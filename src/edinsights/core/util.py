from importlib import import_module
import inspect

from pymongo import MongoClient

from django.conf import settings
from django.core.cache import cache

from edinsights.modulefs import modulefs

connection = MongoClient() # TODO: Parameter setting for Mongos over the network

def import_view_modules():
    '''
    Step through the modules specified in INSTALLED_ANALYTICS_MODULES
    in settings.py, and import each of them. This must run on startup
    to make sure all of the event_handler decorators are called.
    '''
    top_level_modules = settings.INSTALLED_ANALYTICS_MODULES
    module_names = []
    for module in top_level_modules:
        mod = import_module(module)
        submodules = []
        try: 
            submodules = mod.modules_to_import # I'd like to deprecate this syntax
        except AttributeError: 
            pass
        for sub_module in submodules:
            submod_name = "{0}.{1}".format(module,sub_module)
            module_names.append(submod_name)
    modules = map(import_module, module_names)
    return modules

def namespace(f):
    ''' Return the namespace of a function f. 
    If passed a string, assumes it is already a namespace. '''
    if not isinstance(f,str) and not isinstance(f,unicode):
        module = f.__module__
    else:
        module = f
    return str(module).replace(".","_")

def get_mongo(f):
    ''' Given a function in a module, return the Mongo DB associated
    with that function. 
    '''
    return connection[namespace(f)]

def get_filesystem(f):
    ''' Given a function in a module, return the Pyfilesystem for that
    function. Right now, this is on disk, but it has to move to
    Mongo gridfs or S3 or similar (both of which are supported by 
    pyfs).
    '''
    return modulefs.get_filesystem(namespace(f))

class CacheHelper:
    def __init__(self, name, cache):
        self.name = name
        self.cache = cache

    def set(self, key, value, time):
        return self.cache.set(self.name+"/"+key, value, time)

    def get(self, key):
        return self.cache.get(self.name+"/"+key)

def get_cache(f):
    ''' Given a function, return a cache for that function. This is
    helpful for things like daily activity, where we don't want to hit
    Mongo for every event. Cache is not guaranteed. It is likely to be
    per-thread or per-process. '''
    return CacheHelper(namespace(f), cache)

def get_view(f):
    ''' Returns an object which provides an abstraction to other
    queries. This allows us to split the analytics across multiple
    systems transparently, as well as add/remove things like cache,
    filesystem, etc.
    '''
    from djobject import djobject, get_embed
    from django.conf import settings
    embed_config = None
    try:
        embed_config = settings.DJOBJECT_CONFIG
    except AttributeError:
        pass

    return get_embed('view', config = embed_config)

def get_query(f):
    ''' Returns an object which provides an abstraction to views. This
    allows us to split the analytics across multiple systems
    transparently, as well as add/remove things like cache,
    filesystem, etc.
    '''
    from djobject import djobject, get_embed
    from django.conf import settings
    embed_config = None
    try:
        embed_config = settings.DJOBJECT_CONFIG
    except AttributeError:
        pass

    return get_embed('query', config = embed_config)

default_optional_kwargs = {'fs' : get_filesystem,
                           'mongodb' : get_mongo,
                           'cache' : get_cache,
#                           'analytics' : get_djobject,
                           'view' : get_view,
                           'query' : get_query}

def optional_parameter_call(function, passed_kwargs, arglist = None):
    ''' Calls a function with parameters: 
    passed_kwargs are input parameters the function must take. 
    Format: Dictionary mapping keywords to arguments. 

    optional_kwargs are optional input parameters. 
    Format: Dictionary mapping keywords to functions which generate those parameters. 

    arglist is an optional list of arguments to pass to the function. 
    '''
    if not arglist: 
        arglist = inspect.getargspec(function).args
    
    args = {}

    #The params keyword should be able to handle any passed arguments that are not explicitly asked for
    #by the function.
    #This will set the "params" field in args to a dictionary of the fields that do not appear in arglist.
    #The params field will be overriden in the loop further down if the user explicitly specifies it.
    additional_argument_variable = "params"
    if additional_argument_variable in arglist:
        params = {k:passed_kwargs[k] for k in passed_kwargs if k not in arglist}
        if additional_argument_variable not in passed_kwargs and additional_argument_variable not in optional_kwargs:
            arglist = [a for a in arglist if a!=additional_argument_variable]
        args[additional_argument_variable] = params

    for arg in arglist:
        # This order is important for security. We don't want users
        # being able to pass in 'fs' or 'db' and having that take
        # precedence.

        global default_optional_kwargs
        if arg in default_optional_kwargs:
            args[arg] = default_optional_kwargs[arg](function)
            #ignore default arguments in memoize when building cache key
            args[arg].memoize_ignore = True
        elif arg in passed_kwargs: 
            args[arg] = passed_kwargs[arg]
        else: 
            raise TypeError("Missing argument needed for handler ", arg)

    return function(**args)
