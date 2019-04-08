from __future__ import print_function, absolute_import

import copy

try:
    from typing import Any, Dict, List, Tuple, Union # noqa
except ImportError:
    pass

from pymel.core import aimConstraint, parentConstraint, pointConstraint, orientConstraint
from pymel.core import PyNode, dt
import maya.cmds as cmds

from .. import add

# Dynamically accessed in `_constraintSerialize` on what flags to query.
AIMCONSTRAINT_FLAGS = ['aim', 'u', 'wut', 'wu', 'wuo', 'o']
POINTCONSTRAINT_FLAGS = [] # type: List[str]
PARENTCONSTRAINT_FLAGS = [] # type: List[str]
ORIENTCONSTRAINT_FLAGS = [] # type: List[str]


def makeJsonSerializable(val): # type: (Union[PyNode, dt.Vector]) -> Union[Dict, List]
    '''
    Converts pymel vectors to lists and pynodes to dicts (in core.dagObj id format).
    '''
    if isinstance(val, dt.Vector):
        return [val[0], val[1], val[2]]
    
    if isinstance(val, PyNode):
        return add.getIds(val)
    
    return val


def _constraintSerialize(constType, obj): # type: (str, PyNode) -> Dict[str, Dict]
    '''
    Given a str for the constraint type, ex `pointConstraint` and a PyNode, returns
    a json-valid dict that can be used to reconstruct the contstraint.
    '''
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


def _constraintDeserialize(obj, kwargs): # type: (PyNode, Dict) -> Tuple[List[PyNode], Dict]
    '''
    Helper, return a <list of targets> and **kwargs for use in reconstructing a constraint, from `_constraintSerialize`.
    '''
    #kwargs = copy.deepcopy(data)
    kwargExtraData = kwargs['#']
    del kwargs['#']

    # Always maintain offset.  Might not want to at some point but a value in o/offset implies -mo was used.
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


def aimSerialize(obj): # type: (PyNode) -> Dict
    return _constraintSerialize('aimConstraint', obj)
    
    
def aimDeserialize(obj, data): # type: (PyNode, Dict) -> None
    # If the world up object is absent, remove it entirely.
    kwargs = copy.deepcopy(data)
    if not kwargs['wuo']:
        del kwargs['wuo']
    else:
        kwargs['wuo'] = add.findFromIds(kwargs['wuo'])
    
    targets, reformattedKwargs = _constraintDeserialize(obj, kwargs)
    if 'mo' in reformattedKwargs:
        del reformattedKwargs['mo']
    aimConstraint(targets, obj, mo=True, **reformattedKwargs)
    
    
def pointSerialize(obj): # type: (PyNode) -> Dict
    return _constraintSerialize('pointConstraint', obj)
    

def pointDeserialize(obj, data): # type: (PyNode, Dict) -> None
    kwargs = copy.deepcopy(data)
    targets, reformattedKwargs = _constraintDeserialize(obj, kwargs)
    if 'mo' in reformattedKwargs:
        del reformattedKwargs['mo']
    pointConstraint(targets, obj, mo=True, **reformattedKwargs)
    
    
def orientSerialize(obj): # type: (PyNode) -> Dict
    return _constraintSerialize('orientConstraint', obj)
    
    
def orientDeserialize(obj, data): # type: (PyNode, Dict) -> None
    kwargs = copy.deepcopy(data)
    targets, reformattedKwargs = _constraintDeserialize(obj, kwargs)
    if 'mo' in reformattedKwargs:
        del reformattedKwargs['mo']
    orientConstraint(targets, obj, mo=True, **reformattedKwargs)
    
    
def parentSerialize(obj): # type: (PyNode) -> Dict
    return _constraintSerialize('parentConstraint', obj)
    
    
def parentDeserialize(obj, data):  # type: (PyNode, Dict) -> None
    kwargs = copy.deepcopy(data)
    targets, reformattedKwargs = _constraintDeserialize(obj, kwargs)
    if 'mo' in reformattedKwargs:
        del reformattedKwargs['mo']
    parentConstraint(targets, obj, mo=True, **reformattedKwargs)
    
    
def fullSerialize(obj):
    '''
    Try serializing all constraint, returning a dictionary of which ones apply.
    '''
    constraints = {}
    for func in [ aimSerialize, pointSerialize, orientSerialize, parentSerialize ]:
        result = func(obj)
        if result:
            constraints[func.__name__.replace('Serialize', '')] = result
    return constraints
    
    
def fullDeserialize(obj, alldata):
    alldata = copy.deepcopy(alldata)
    for ctype, data in alldata.items():
        if 'mo' in data:
            del data['mo']
        globals()[ ctype + 'Deserialize' ](obj, data)
    
    
def getOrientConstrainee(target): # type: (PyNode) -> PyNode
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
        
        
def getParentConstrainee(target): # type: (PyNode) -> PyNode
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
        
        
def pointConst(*args, **kwargs): # type: (*Any, **Any) -> PyNode
    ''' pointConstraint wrapper that returns the controlling plug '''
    return pointConstraint(*args, **kwargs).getWeightAliasList()[-1]


def orientConst(*args, **kwargs):
    ''' orientConstraint wrapper that returns the controlling plug '''
    return orientConstraint(*args, **kwargs).getWeightAliasList()[-1]