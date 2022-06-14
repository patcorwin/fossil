'''

`_constraintSerialize` returns a dict that is used as **kwargs to rebuild the constriant.
An aimConstraint might produce this:

{
    "wuo": "upTarget",      # <-- constraint specifics live top level
    "wut": "object",
    "#": {                  # <-- extra info, like the target list, live underneath "#"
        "targets": ["target_a",  "target_b"]
    }
}

`_constraintSerialize` has an optional `nodeConv` param to convert PyNodes into something json serializable.
This defaults into `str` to just dump it out as a string

`_constraintDeerialize` has the reverse `nodeDeconv` to convert the input into something, defaulting to doing nothing.

Fossil uses this to turn nodes into a dict, which provides several methods to find a node.

'''

from __future__ import print_function, absolute_import

import copy


from pymel.core import aimConstraint, parentConstraint, pointConstraint, orientConstraint, scaleConstraint
from pymel.core import PyNode, dt
import maya.cmds as cmds


__all__ = [
    'aimSerialize',
    'aimDeserialize',
    'pointSerialize',
    'pointDeserialize',
    'orientSerialize',
    'orientDeserialize',
    'scaleSerialize',
    'scaleDeserialize',
    'parentSerialize',
    'parentDeserialize',
    'fullSerialize',
    'fullDeserialize',
    'getOrientConstrainee',
    'getParentConstrainee',
    'pointConst',
    'orientConst',
]


# Dynamically accessed in `_constraintSerialize` on what flags to query.
AIMCONSTRAINT_FLAGS = ['aim', 'u', 'wut', 'wu', 'wuo', 'o']
POINTCONSTRAINT_FLAGS = []
PARENTCONSTRAINT_FLAGS = []
ORIENTCONSTRAINT_FLAGS = []
SCALECONSTRAINT_FLAGS = []


affectsRotation = {
    'orientConstraint': 'skip',
    'parentConstraint': 'sr',
    'aimConstraint': 'skip',
}

affectsTranslation = {
    'parentConstraint': 'st',
    'pointConstraint': 'skip'
}


def makeJsonSerializable(val, nodeConv=str):
    ''' Converts pymel vectors to lists and PyNodes via `nodeConv` (defaults to `str`)
    '''
    if isinstance(val, dt.Vector):
        return [val[0], val[1], val[2]]
    
    if isinstance(val, PyNode):
        return nodeConv(val)
    
    return val


def _constraintSerialize(constType, obj, nodeConv=str, includeOffset=False):
    ''' Given a str for the constraint type, ex `pointConstraint` and a PyNode, returns
    a json-valid dict that can be used to reconstruct the contstraint.
    
    Args:
        constType: str = 'pointConstraint' or one of the other constraints
        obj: PyNode = The object to inspect
        nodeConv: <function> = Targets (and other objects) get run through this
            to make it serializable
        includeOffset: bool = Force using the offset instead of `maintainOffset`
    
    '''
    cmds_constraint = getattr(cmds, constType)
    pymel_constraint = globals()[constType]
    flags = globals()[constType.upper() + '_FLAGS']
    
    data = {'#': {}}
    
    const = cmds_constraint(str(obj), q=True)

    if not const:
        return None, None

    for flag in flags:
        val = pymel_constraint(const, q=True, **{flag: True})
        data[flag] = makeJsonSerializable(val, nodeConv)

    data['#']['targets'] = [ nodeConv(o) for o in pymel_constraint(const, q=True, tl=True) ]

    if constType in affectsRotation:
        skipRotate = [axis for axis in 'xyz' if not cmds.listConnections( const + '.constraintRotate' + axis.upper() )]
        if skipRotate:
            skipFlag = affectsRotation[constType]
            data[ skipFlag ] = skipRotate
    
    if constType in affectsTranslation:
        skipTranslate = [axis for axis in 'xyz' if not cmds.listConnections( const + '.constraintTranslate' + axis.upper() )]
        if skipTranslate:
            skipFlag = affectsTranslation[constType]
            data[skipFlag] = skipTranslate
    
    if constType == 'scaleConstraint':
        skipScale = [axis for axis in 'xyz' if not cmds.listConnections( const + '.constraintScale' + axis.upper() )]
        if skipScale:
            # Currently there is only one scale affector so just set it directly
            skipFlag = 'skip'
            data[skipFlag] = skipScale
    
    if includeOffset:
        if constType == 'parentConstraint':
            indices = cmds.getAttr( const + '.target', mi=True )
            data['#']['offset'] = [
                [cmds.getAttr(const + '.target[%i].targetOffsetTranslate' % i)[0],
                cmds.getAttr(const + '.target[%i].targetOffsetRotate' % i)[0]]
                for i in indices
            ]
        else:
            data['#']['offset'] = cmds.getAttr(const + '.offset')[0]

    return data, const


def _constraintDeserialize(kwargs, nodeDeconv=lambda n: n):
    ''' Takes the kwargs used for a constraint and converts the targets to nodes (default to leaving as is).
    '''
    #kwargs = copy.deepcopy(data)
    kwargExtraData = kwargs['#']
    del kwargs['#']

    # Always maintain offset.  Might not want to at some point but a value in o/offset implies -mo was used.
    if 'o' in kwargs:
        del kwargs['o']
        kwargs['mo'] = True

    targets = [ nodeDeconv(o) for o in kwargExtraData['targets'] ]

    # In of 2016-2020, unicode keys don't work so use str, which will always work.
    nonUnicodeKwargs = {}
    for k, v in kwargs.items():
        nonUnicodeKwargs[str(k)] = v
    
    return targets, nonUnicodeKwargs


def applyOffset(const, data):
    offset = data.get('#', {}).get('offset', None)
    if offset:
        const.offset.set( offset )


def aimSerialize(obj, nodeConv=str, includeOffset=False):
    return _constraintSerialize('aimConstraint', obj, nodeConv=nodeConv, includeOffset=includeOffset)[0]
    
    
def aimDeserialize(obj, data, nodeDeconv=lambda n: n, includeOffset=False):
    # If the world up object is absent, remove it entirely.
    kwargs = copy.deepcopy(data)
    if not kwargs['wuo']:
        del kwargs['wuo']
    else:
        kwargs['wuo'] = nodeDeconv(kwargs['wuo'])
    
    targets, reformattedKwargs = _constraintDeserialize(kwargs, nodeDeconv)
    if 'mo' in reformattedKwargs:
        del reformattedKwargs['mo']
    #print('TARGETS:', targets)
    #print('OBJ:', obj)
    #print('KWARGS', reformattedKwargs)
    const = aimConstraint(targets, obj, mo=True, **reformattedKwargs)
    
    if includeOffset:
        applyOffset(const, data)
    
    
def pointSerialize(obj, nodeConv=str, includeOffset=False):
    return _constraintSerialize('pointConstraint', obj, nodeConv=nodeConv, includeOffset=includeOffset)[0]
    

def pointDeserialize(obj, data, nodeDeconv=lambda n: n, includeOffset=False):
    kwargs = copy.deepcopy(data)
    targets, reformattedKwargs = _constraintDeserialize(kwargs, nodeDeconv)
    if 'mo' in reformattedKwargs:
        del reformattedKwargs['mo']
    const = pointConstraint(targets, obj, mo=True, **reformattedKwargs)
    
    if includeOffset:
        applyOffset(const, data)
    
    
def orientSerialize(obj, nodeConv=str, includeOffset=False):
    return _constraintSerialize('orientConstraint', obj, nodeConv=nodeConv, includeOffset=includeOffset)[0]
    
    
def orientDeserialize(obj, data, nodeDeconv=lambda n: n, includeOffset=False):
    kwargs = copy.deepcopy(data)
    targets, reformattedKwargs = _constraintDeserialize(kwargs, nodeDeconv)
    if 'mo' in reformattedKwargs:
        del reformattedKwargs['mo']
    const = orientConstraint(targets, obj, mo=True, **reformattedKwargs)
    if includeOffset:
        applyOffset(const, data)
    
    
def scaleSerialize(obj, nodeConv=str, includeOffset=False):
    return _constraintSerialize('scaleConstraint', obj, nodeConv=nodeConv, includeOffset=includeOffset)[0]
    
    
def scaleDeserialize(obj, data, nodeDeconv=lambda n: n, includeOffset=False):
    kwargs = copy.deepcopy(data)
    targets, reformattedKwargs = _constraintDeserialize(kwargs, nodeDeconv)
    if 'mo' in reformattedKwargs:
        del reformattedKwargs['mo']
    const = scaleConstraint(targets, obj, mo=True, **reformattedKwargs)
    if includeOffset:
        applyOffset(const, data)
    
    
def parentSerialize(obj, nodeConv=str, includeOffset=False):
    return _constraintSerialize('parentConstraint', obj, nodeConv=nodeConv, includeOffset=includeOffset)[0]
    
    
def parentDeserialize(obj, data, nodeDeconv=lambda n: n, includeOffset=False):
    kwargs = copy.deepcopy(data)
    targets, reformattedKwargs = _constraintDeserialize(kwargs, nodeDeconv)
    if 'mo' in reformattedKwargs:
        del reformattedKwargs['mo']
    
    const = parentConstraint(targets, obj, mo=True, **reformattedKwargs)
    
    if includeOffset:
        
        # The assumption is that the targets line up with the offsets, which
        # might not be strictly true, but I'll address it if it comes up.
        offsets = data.get('#', {}).get('offset', [])
        if offsets:
            targetIndices = const.target.getArrayIndices()
            
            for target_i, offset in zip(targetIndices, offsets):
                const.target[target_i].targetOffsetTranslate.set( offset[0] )
                const.target[target_i].targetOffsetRotate.set( offset[1] )
    
    
def fullSerialize(obj, nodeConv=str, includeOffset=False):
    '''
    Try serializing all constraint, returning a dictionary of which ones apply.
    '''
    constraints = {}
    for func in [ aimSerialize, pointSerialize, orientSerialize, parentSerialize, scaleSerialize ]:
        result = func(obj, nodeConv, includeOffset)
        if result:
            constraints[func.__name__.replace('Serialize', '')] = result
    return constraints
    
    
def fullDeserialize(obj, alldata, nodeDeconv=lambda n: n, includeOffset=False):
    alldata = copy.deepcopy(alldata)
    for ctype, data in alldata.items():
        if 'mo' in data:
            del data['mo']
        globals()[ ctype + 'Deserialize' ](obj, data, nodeDeconv, includeOffset)
    
    
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
    ''' pointConstraint wrapper that returns the controlling plug '''
    return pointConstraint(*args, **kwargs).getWeightAliasList()[-1]


def orientConst(*args, **kwargs):
    ''' orientConstraint wrapper that returns the controlling plug '''
    return orientConstraint(*args, **kwargs).getWeightAliasList()[-1]