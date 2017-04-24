from __future__ import print_function, absolute_import

import copy

from pymel.core import aimConstraint, parentConstraint, pointConstraint, orientConstraint
from pymel.core import PyNode, dt
import maya.cmds as cmds

from .. import add


AIMCONSTRAINT_FLAGS = ['aim', 'u', 'wut', 'wu', 'wuo', 'o']
POINTCONSTRAINT_FLAGS = []
PARENTCONSTRAINT_FLAGS = []
ORIENTCONSTRAINT_FLAGS = []


def makeJsonSerializable(val):
    '''
    Converts pymel vectors to lists and pynodes to dicts (in core.dagObj id format).
    '''
    if isinstance(val, dt.Vector):
        return [val[0], val[1], val[2]]
    
    if isinstance(val, PyNode):
        return add.getIds(val)
    
    return val


def _constraintSerialize(constType, obj):
    cmds_constraint = getattr(cmds, constType)
    pymel_constraint = globals()[constType]
    flags = globals()[constType.upper() + '_FLAGS']
    
    data = {'#': {}}
    
    const = cmds_constraint(str(obj), q=True)

    if not const:
        return None

    for flag in flags:
        val = pymel_constraint(const, q=True, **{flag: True})
        data[flag] = makeJsonSerializable(val)

    data['#']['targets'] = [ add.getIds(o) for o in pymel_constraint(const, q=True, tl=True) ]

    return data


def _constraintDeserialize(obj, kwargs):
    #kwargs = copy.deepcopy(data)
    kwargExtraData = kwargs['#']
    del kwargs['#']

    # Always maintain offset
    if 'o' in kwargs:
        del kwargs['o']
        kwargs['mo'] = True

    targets = [ add.findFromIds(o) for o in kwargExtraData['targets'] ]

    # As of 2016, unicode keys don't work.  So stupid.
    nonUnicode = {}
    for k, v in kwargs.items():
        nonUnicode[str(k)] = v

    #aimConstraint(targets, obj, **nonUnicode )
    return targets, nonUnicode


def aimSerialize(obj):
    return _constraintSerialize('aimConstraint', obj)
    
    
def aimDeserialize(obj, data):
    # If the world up object is absent, remove it entirely.
    kwargs = copy.deepcopy(data)
    if not kwargs['wuo']:
        del kwargs['wuo']
    else:
        kwargs['wuo'] = add.findFromIds(kwargs['wuo'])
    
    targets, reformattedKwargs = _constraintDeserialize(obj, kwargs)
    aimConstraint(targets, obj, mo=True, **reformattedKwargs)
    
    
def pointSerialize(obj):
    return _constraintSerialize('pointConstraint', obj)
    

def pointDeserialize(obj, data):
    kwargs = copy.deepcopy(data)
    targets, reformattedKwargs = _constraintDeserialize(obj, kwargs)
    pointConstraint(targets, obj, mo=True, **reformattedKwargs)
    
    
def orientSerialize(obj):
    return _constraintSerialize('orientConstraint', obj)
    
    
def orientDeserialize(obj, data):
    kwargs = copy.deepcopy(data)
    targets, reformattedKwargs = _constraintDeserialize(obj, kwargs)
    orientConstraint(targets, obj, mo=True, **reformattedKwargs)
    
    
def parentSerialize(obj):
    return _constraintSerialize('parentConstraint', obj)
    
    
def parentDeserialize(obj, data):
    kwargs = copy.deepcopy(data)
    targets, reformattedKwargs = _constraintDeserialize(obj, kwargs)
    parentConstraint(targets, obj, mo=True, **reformattedKwargs)
    
    
def getOrientConstrainee(target):
    '''
    Given a target used in an orientConstraint, find the object that is orient
    constrained to it.
    '''
    try:
        #target.parentMatrix[0].listConnections( type='orientConstraint', d=True )[0].constraintRotateZ.listConnections()[0]

        constraints = target.parentMatrix[0].listConnections( type='orientConstraint', d=True )

        if not constraints:
            return None
        elif len(constraints) == 1:
            return constraints[0].constraintRotateZ.listConnections()[0]
        else:
            raise Exception( '{0} is the target of multiple constraints, too many results'.format( target ) )
    except Exception:
        return None
        
        
def getParentConstrainee(target):
    '''
    Given a target used in an orientConstraint, find the object that is orient
    constrained to it.
    '''
    try:
        #target.parentMatrix[0].listConnections( type='orientConstraint', d=True )[0].constraintRotateZ.listConnections()[0]

        constraints = target.parentMatrix[0].listConnections( type='parentConstraint', d=True )

        if not constraints:
            return None
        elif len(constraints) == 1:
            return constraints[0].constraintRotateZ.listConnections()[0]
        else:
            raise Exception( '{0} is the target of multiple constraints, too many results'.format( target ) )
    except Exception:
        return None
        
        
def pointConst(*args, **kwargs):
    # pointConstraint wrapper that returns the controlling plug
    return pointConstraint(*args, **kwargs).getWeightAliasList()[-1]


def orientConst(*args, **kwargs):
    # orientConstraint wrapper that returns the controlling plug
    return orientConstraint(*args, **kwargs).getWeightAliasList()[-1]