from __future__ import print_function, absolute_import, division

import numbers

from maya.cmds import currentUnit

from . import alt # noqa
from . import path # noqa

__all__ = ['alt', 'path', 'shortName', 'simpleName', 'meters', 'cm']


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


"""
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
"""
        
_conversion = {
    'mm': .001, # millimeter
    'cm': .01, # centimeter
    'm': 1.0, # meter
    'km': 10, # kilometer
    'in': 0.0254, # inch
    'ft': 0.3048, # foot
    'yd': 0.9144, # yard
    'mi': 1609.34, # mile
}


def meters(val):
    ratio = _conversion[currentUnit(q=True, l=True)]
    if isinstance(val, numbers.Number):
        return (val / ratio)
    else:
        return [v / ratio for v in val]
        
        
def cm(val):
    ratio = _conversion[currentUnit(q=True, l=True)] * 100.0
    if isinstance(val, numbers.Number):
        return val / ratio
    else:
        return [v / ratio for v in val]