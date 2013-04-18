import inspect
import json
import os

from django.core.urlresolvers import reverse
from django.dispatch import receiver
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.utils.datastructures import MultiValueDictKeyError
from django.views.decorators.csrf import csrf_exempt

from django.conf import settings

from djeventstream.signals import event_received

from registry import event_handlers, request_handlers
from util import default_optional_kwargs

import auth
import util
from util import optional_parameter_call

import logging

log=logging.getLogger(__name__)

@auth.auth
def index(request):
    return HttpResponseRedirect("static/index.html")

@auth.auth
def event_properties(request):
    ''' Adds a view to advertise defined event properties '''
    from registry import event_property_registry
    items = []
    for key in event_property_registry.keys():
        items.append("<di>{name}</di><dd>{doc}</dd>".format(**event_property_registry[key]))
    return HttpResponse("<dl>"+"\n".join(items)+"</dl>")

# We don't want to have two ways to get at this data
# @auth.auth
# def handle_probe(request, cls=None, name = None):
#     ''' Handles probes for what types of modules are available, and
#     what they do. Shown as, effectively, a big directory tree to the
#     caller.
#     '''
#     error_message = "{0} not found in {1}."
#     if cls == None:
#         l = ['view','query']
#     elif name == None:
#         if cls in request_handlers:
#             l = request_handlers[cls].keys()
#         else:
#             raise Http404(error_message.format(cls,request_handlers))
#     else:
#         if cls in request_handlers and name in request_handlers[cls]:
#             l = [request_handlers[cls][name]['doc']]
#         else:
#             raise Http404(error_message.format(cls+'/'+name,request_handlers))
#     if request.GET.get("f", "") == "html":
#         if not name:
#             l = ["<li><a href={a}?f=html>{b}</a></li>".format(a=(cls or "probe")+"/"+i, b=i) for i in l]
#         else:
#             l = ["<p>".join(l)]
#         return HttpResponse("".join(l), mimetype='text/html')
#     return HttpResponse("\n".join(l), mimetype='text/text')

def schema_helper():
    endpoints = []
    for cls in request_handlers:
        for name in request_handlers[cls]:
            rh = request_handlers[cls][name]
            endpoints.append({'category' : rh['category'], 'class': cls, 'name' : name, 'doc' : rh['doc']})
    return endpoints

@auth.auth
def schema(request):
    ''' Returns all available views and queries as a JSON
    object. 
    '''
    endpoints = schema_helper()
    if request.GET.get("f", "") == "html":
        return HttpResponse("\n".join(sorted(["<dt><p><b>{class}/{name}</b> <i>{category}</i></dt><dd>{doc}</dd>".format(**rh) for rh in endpoints])))
    return HttpResponse(json.dumps(endpoints))
    

def handle_request(cls, name, **kwargs):
    ''' Generic code from handle_view and handle_query '''
    args = dict()
    categories = request_handlers[cls]
    if name in categories: 
        handler_dict = categories[name]
    else:
        raise Http404(name+"  is not a valid function")
    handler = handler_dict['function']
    if 'args' in handler_dict:
        arglist = handler_dict['arglist']
    else:
        arglist = inspect.getargspec(handler).args

    return optional_parameter_call(handler, default_optional_kwargs, kwargs, arglist)

@auth.auth
def handle_view(request, name, **kwargs):
    ''' Handles generic view. 
        Category is where this should be place (per student, per problem, etc.)
        Name is specific 
    '''
    kwargs.update(request.POST.items())
    kwargs.update(request.GET.items())
    return HttpResponse(handle_request('view', name, **kwargs))

@auth.auth
def handle_query(request, name, **kwargs):
    ''' Handles generic view. 
        Category is where this should be place (per student, per problem, etc.)
        Name is specific 
    '''
    kwargs.update(request.POST.items())
    kwargs.update(request.GET.items())
    request_data = handle_request('query', name, **kwargs)
    try:
        request_data = json.dumps(request_data)
    except:
        pass

    try:
        return HttpResponse(request_data)
    except:
        return request_data

@receiver(event_received)
def handle_event(sender, **kwargs):
    ''' Receives either an event or a list of events, as sent by
    djeventstream (either from a Python logging HTTPHandler or
    SNSHandler. 

    Forwards it along to the event handlers defined in the modules. 

    This is not a view, but it is the moral equivalent. 
    '''
    # Handle strings, lists, and dictionaries
    msg = kwargs['msg']
    if isinstance(msg,str) or isinstance(msg,unicode):
        msg = json.loads(msg)

    # If we get a batch of events, we need to load them. 
    if isinstance(msg,list):
        for i in xrange(0,len(msg)):
            try:
                msg[i] = json.loads(msg[i])
            except:
                pass

    # Single event should still be passed as a list for API 
    # compatibility between patched and unbatched. 
    if not isinstance(msg, list):
        msg = [msg]
    
    from registry import StreamingEvent
    msg = map(StreamingEvent, msg)

    for e in event_handlers:
        event_func = e['function']
        batch = e['batch']
        if not batch: ## Message was a list of events, but handler cannot batch events
            for event in msg:
                try:
                    optional_parameter_call(event_func, default_optional_kwargs, {'events':[event]})
                except:
                    handle_event_exception(e['function'])
        else: ## Message was a list of events, and handler can batch events
            try:
                optional_parameter_call(event_func, default_optional_kwargs, {'events':msg})
            except:
                handle_event_exception(e['function'])

    return HttpResponse( "Success" )

def handle_event_exception(function):
    log.exception("Handler {0} failed".format(function))

