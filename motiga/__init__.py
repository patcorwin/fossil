from __future__ import print_function, absolute_import

import inspect


def deprecatedStub(funcOrClass, error=False):
    '''
    Wrap calls to functions that have been moved.  `error=True` is for when you
    think you have updated all usage to the new location but can still have the
    breadcrumb.
    '''
    if inspect.isclass(funcOrClass):
    
        class newThing(funcOrClass):
            def __init__(self, *args, **kwargs):
                #print('You have called a class from a deprecated module, update to the new location')
                if error:
                    raise DeprecationWarning(str(funcOrClass) + ' is being called from an old location')
                funcOrClass.__init__(self, *args, **kwargs)
    
    else:
        def newThing(*args, **kwargs):
            #print('You have called a function from a deprecated module, update to the new location')
            if error:
                raise DeprecationWarning(str(funcOrClass) + ' is being called from an old location')
            return funcOrClass(*args, **kwargs)
    
    return newThing