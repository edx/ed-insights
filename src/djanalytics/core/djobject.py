''' This is a generic interface to djanalytics. It presents views,
etc. as Python objects. 

This is prototype-grade code. 

It will remain ugly into production, however. I'm not sure if there is
a good way to make this clean, but the ugliness here will save a lot
of ugliness for the API caller.
'''

import requests
import urllib
import json
import decorator

schema = None

def find_in_schema(cls = None, name = None):
    ''' Search for a given class/name combo in schema. Return all
    matching objects. Either can be passed alone. 
    ''' 
    items = []
    for item in schema: 
        if cls and item['class'] != cls: 
            continue
        if name and item['name'] != name: 
            continue
        items.append(item)
    return items

def http_rpc_helper(baseurl, view_or_query, function, headers = {}):
    ''' Make an RPC call to a remote djanalytics instance
    '''
    if baseurl: 
        baseembedurl = baseurl+view_or_query+"/"

    def rpc_call(**kwargs):
        url = urllib.basejoin(baseembedurl, function)
        if kwargs:
            url = url+"?"+urllib.urlencode(kwargs)
        response = requests.get(url, headers = headers)
        if response.status_code == 200:
            return response.content
        if response.status_code == 404:
            raise AttributeError(function)
        error = "Error calling {func} {status}".format(func=function, status=response.status_code)
        raise Exception(error)
    return rpc_call

def local_call_helper(view_or_query, function):
    ''' Make a call (functionally identical to RPC) to the local djanalytics instance
    '''
    import djanalytics.core.views
    def rpc_call(**kwargs):
        return djanalytics.core.views.handle_request(view_or_query, function, **kwargs)
    return rpc_call

class embed():
    def __init__(self, view_or_query, baseurl = None, headers = {}):
        self._baseurl = baseurl
        self._view_or_query = view_or_query
        self._headers = headers
        self._refresh_schema()

    def _refresh_schema(self):
        global schema
        if not schema:
            if self._baseurl:
                url = self._baseurl+"schema"
                schema = json.loads(requests.get(url).content)
            else: 
                import djanalytics.core.views
                schema = djanalytics.core.views.schema_helper()

    def __getattr__(self, attr):
        ## Disallow internal. This is necessary both for analytics,
        ## and for Python. Otherwise, we have all sorts of __setattr__
        ## and similar overwritten
        if attr[0] == '_':
            return

        # Return a caller to the function
        if self._baseurl:
            helper = http_rpc_helper(self._baseurl, self._view_or_query, attr)
        else:
            helper = local_call_helper(self._view_or_query, attr)
            
        # Modified the function to have the proper function spec. 
        # The internals of decorator.FunctionMaker make me sick. 
        try: 
            rpcspec = find_in_schema(cls = self._view_or_query, name = attr)[0]
        except IndexError: 
            raise AttributeError(function)
        category = rpcspec['category']

        def_params = category.replace('+',',') # Is this still needed? 
        if def_params:
            call_params = ",".join(["{p}={p}".format(p=p) for p in category.split('+')])
        else:
            call_params = ""
        funcspec = "{name}({params})".format(name='rpc_'+attr, 
                                             params=def_params)
        callspec = "return helper({params})".format(params=call_params)
        return decorator.FunctionMaker.create(funcspec, 
                                              callspec, 
                                              {'helper':helper}, 
                                              doc = rpcspec['doc'])

    def __dir__(self):
        ''' Allow tab completion on function names in ipython, and
        other sorts of introspection.  '''
        self._refresh_schema()
        return [i["name"] for i in find_in_schema(cls = self._view_or_query)]

    def __repr__(self):
        ''' Pretty representation of the object. '''
        return self._view_or_query+" object host: ["+self._baseurl+"]"
                                
class djobject():
    def __init__(self, baseurl = None, headers = {}):
        self.view = embed('view', baseurl = baseurl, headers = headers)
        self.query = embed('query', baseurl = baseurl, headers = headers)

if __name__ == "__main__":
    djo = djobject(baseurl = "http://127.0.0.1:8000/")
    print djo.query.djt_event_count()
    print djo.query.djt_user_event_count(user = "bob")
    print djo.query.__dir__()
