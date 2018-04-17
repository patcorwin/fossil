from __future__ import print_function, absolute_import

from pymel.core import ls, PyNode

from . import alt # noqa
from . import path # noqa


def shortName(obj):
    '''
    Returns the name without ANY hierarchy, thus might not be unique. Ex:
        
        shortName( PyNode('someObj|eat:food') ) => 'eat:food'
        shortName( PyNode('someOtherObj|eat:food') ) => 'eat:food'
    '''
    return obj.name().rsplit('|')[-1]


def simpleName(obj, format='{0}'):
    '''
    Strip the given PyNode of namespaces and hierarchy and optionally format it.
    
    Ex, simpleName(PyNode('|blah:face')) => 'face'
        simpleName(PyNode('ignore:junk|foot')) => 'foot'
        simpleName(PyNode('ignore:junk|beans'), 'cool_{0}_yo') => 'cool_beans_yo'
    '''
    name = obj.name().split(':')[-1].split('|')[-1]
    
    return format.format( name )
    
    
def cardPath(obj):
    '''
    If the object implements cardPath() (rig/anim related), return it, otherwise an empty string.
    '''
    try:
        return obj.cardPath()
    except AttributeError:
        return ''
        

def getIds(obj):
    '''
    Returns a dict of all the various ways to find the given object.
    '''
    
    ids = {
        'short': shortName(obj),
        'long': obj.longName(),
    }
    
    path_ = cardPath(obj)
    
    if path_:
        ids['cardPath'] = path_
    
    return ids
    

def findFromIds(ids):
    '''
    Given the dict from `getIds()`, returns an object if possible.
    '''
    
    if len(ls(ids['short'], r=True)) == 1:
        return PyNode(ids['short'])
        
    if len(ls(ids['long'], r=True)) == 1:
        return PyNode(ids['long'])
        
        
def meters(*args):
    '''
    The input is meters and the return value is what maya is currently set to.
    
    ..  todo:: Make not hardcoded for cm.
    
    Also, is this really needed?
    '''
    unit = 100
    scalar = 0.5 * unit
    
    if len(args) > 1:
        return [ scalar * val for val in args  ]
    else:
        return scalar * args[0]