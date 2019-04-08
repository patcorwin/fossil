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
        

def jointPath(obj):
    '''
    If this joint is connected to blueprint joint, return the cardPath, otherwise an emtpy string.
    
    &&& This needs to return a sensible string, be used in getIds, and consumed by the relevant functions.
    '''
    for connection in obj.message.listConnections(p=True):
        if type(connection.node()).__name__ == 'BPJoint': # Test via string name to prevent import cycles
            if connection.attrName() == 'realJoint':
                node = connection.node()
                return 'real:' + node.card.name() + '.' + str(node.card.joints.index(node)) + '|' + node.name()
            elif connection.attrName() == 'realJointMirror':
                return 'mirror:' + node.card.name() + '.' + str(node.card.joints.index(node)) + '|' + node.name()
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
    
    jpath = jointPath(obj)
    if jpath:
        ids['BPJ'] = jpath
    
    return ids
    

def findFromIds(ids):
    '''
    Given the dict from `getIds()`, returns an object if possible.
    
    ..todo:: Process card path and joint paths, (as defined in `getIds`)
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