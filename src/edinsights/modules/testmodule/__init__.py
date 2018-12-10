''' Basic module containing events, views, and queries for the test suite. 

'''

modules_to_import = []

from edinsights.core.decorators import query, event_handler, view, event_property

@view()
def djt_hello_template():
    ''' Example of how to use mako templates in a view '''
    from edinsights.core.render import render
    return render("hello.html", {})

@query()
def djt_event_count(mongodb):
    ''' Number of hits to event_handler since clear_database
    '''
    collection = mongodb['event_count']
    t = list(collection.find())
    if len(t):
        return t[0]['event_count']
    return 0

@query()
def djt_user_event_count(mongodb, user):
    ''' Number of hits by a specific user to event_handler since
    clear_database
    '''
    collection = mongodb['user_event_count']
    t = list(collection.find({'user':user}))
    if len(t):
        return t[0]['event_count']
    return 0

@query()
def djt_clear_database(mongodb):
    ''' Clear event counts
    '''
    collection = mongodb['event_count']
    collection.remove({})
    collection = mongodb['user_event_count']
    collection.remove({})
    return "Database clear"

@event_handler()
def djt_event_count_event(mongodb, events):
    ''' Count events per user and per system. Used as test case for
    per-user and global queries. '''
    for evt in events:
        if 'user' in evt:
            collection = mongodb['user_event_count']
            user = evt['user']
            t = list(collection.find({'user' : user}))
            if len(t): 
                collection.update({'user' : user}, {'$inc':{'event_count':1}})
            else:
                collection.insert({'event_count' : 1, 'user' : user})
        collection = mongodb['event_count']
        t = list(collection.find())
        if len(t): 
            collection.update({}, {'$inc':{'event_count':1}})
        else:
            collection.insert({'event_count' : 1})
    return 0

@event_handler()
def djt_python_fs_forgets(fs, events):
    ''' Test case for checking whether the file system properly forgets. 
    To write a file: 

    { 'fs_forgets_contents' : True, 
      'filename' : "foo.txt",
      'contents' : "hello world!"}

    To set or change expiry on a file: 
    { 'fs_forgets_expiry' : -5, 
      'filename' : "foo.txt"}

    The two may be combined into one operation. 
    '''
    def djt_checkfile(filename, contents):
        if not fs.exists(filename):
            return False
        if fs.open(filename).read == contents:
            return True
        raise Exception("File contents do not match")
    for evt in events:
        if 'fs_forgets_contents' in evt:
            f=fs.open(evt['filename'], 'w')
            f.write(evt['fs_forgets_contents'])
            f.close()
        if 'fs_forgets_expiry' in evt:
            try: 
                fs.expire(evt['filename'], evt['fs_forgets_expiry'])
            except:
                print "Failed"
                import traceback
                traceback.print_exc()
    return 0

@event_handler()
def djt_python_fs_event(fs, events):
    ''' Handles events which will create and delete files in the
    filesystem. 
    '''
    for evt in events:
        if 'event' in evt and evt['event'] == 'pyfstest':
            if 'create' in evt:
                f=fs.open(evt['create'], 'w')
                f.write(evt['contents'])
                f.close()
            if 'delete' in evt and fs.exists(evt['delete']): 
                fs.remove(evt['delete'])

@query()
def djt_readfile(fs, filename):
    ''' Return the contents of a file in the fs. 
    '''
    if fs.exists(filename): 
        f=fs.open(filename)
        return f.read()
    return "File not found"

@query()
def djt_cache_get(cache, key):
    ''' Used in test case for cache '''
    result = cache.get(key)
    return result

@event_handler()
def djt_cache_set(cache, events):
    ''' Used in test case for cache '''
    for evt in events:
        if 'event' in evt and evt['event'] == 'cachetest':
            cache.set(evt['key'], evt['value'], evt['timeout'])

@event_property(name="djt_agent")
def djt_agent(event):
    ''' Returns the user that generated the event. The terminology of
    'agent' is borrowed from the Tincan agent/verb/object model. '''
    if "user" in event:
        return event["user"]
    elif "username" in event:
        return event["username"]
    else:
        return None

@event_handler()
def djt_event_property_check(cache, events):
    ''' Used in test case for event handler '''
    for evt in events:
        if "event_property_check" in evt:
            cache.set("last_seen_user", evt.djt_agent, 30)

@query()
def djt_fake_user_count():
    ''' Used as test case for query objects '''
    return 2

@view()
def djt_fake_user_count(query):
    ''' Test of an abstraction used to call queries, abstracting away
    the network, as well as optional parameters like fs, db, etc. 
    '''
    return "<html>Users: {uc}</html>".format(uc = query.djt_fake_user_count())

@query(name=['djt_three_name', 'edx_djt_three_name', 'edx.djt_three_name'])
def djt_three_name():
    return "I have three names"

@query(name = 'djt_check_three_name')
def check_three_name(query):
    if query.djt_three_name() != "I have three names":
        raise Exception("oops")
    if query.edx_djt_three_name() != "I have three names":
        raise Exception("oops")
    return "Works"
