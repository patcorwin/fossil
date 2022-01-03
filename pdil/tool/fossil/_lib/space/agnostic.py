'''
These functions provide a single interface to the version specific implementations.
'''

from __future__ import absolute_import, division, print_function

from pymel.core import group, warning

import pdil

from ..._core import find

from . import bidirectional
from . import common
from . import constraintBased


def add(ctrl, target, spaceName='', mode=common.Mode.ROTATE_TRANSLATE, enum=True, rotateTarget=None):
    
    if common.isBidirectional(ctrl):
        return bidirectional.add(ctrl, target, spaceName=spaceName, mode=mode, rotateTarget=rotateTarget)
    else:
        return constraintBased.add(ctrl, target, spaceName=spaceName, mode=mode, rotateTarget=rotateTarget)


def remove(ctrl, spaceNameOrIndex, shuffleRemove=False):
    
    if common.isBidirectional(ctrl):
        return bidirectional.remove(ctrl, spaceNameOrIndex, shuffleRemove=shuffleRemove)
    else:
        return constraintBased.remove(ctrl, spaceNameOrIndex, shuffleRemove=shuffleRemove)


def removeAll(ctrl):
    
    if common.isBidirectional(ctrl):
        return bidirectional.removeAll(ctrl)
    else:
        return constraintBased.removeAll(ctrl)


def swap(ctrl, spaceAIndex, spaceBIndex):
    if common.isBidirectional(ctrl):
        return bidirectional.swap(ctrl, spaceAIndex, spaceBIndex)
    else:
        return constraintBased.swap(ctrl, spaceAIndex, spaceBIndex)


def getTargetInfo(ctrl):
    if not ctrl.hasAttr(common.ENUM_ATTR):
        return []
        
    return bidirectional.getTargetInfoBD(ctrl) if common.isBidirectional(ctrl) else constraintBased.getTargetInfo(ctrl)
    
    
def reorder(ctrl, newOrder):
    '''
    Make sure the spaces on `ctrl` are in the `newOrder`, ex `reorder( handCtrl, ['World', 'Root', 'Chest', 'Shoulder'])`.
    '''
    names = common.getNames(ctrl)
    if names == newOrder:
        return
    
    assert len(names) == len(newOrder), 'Cannot reorder spaces on {}, new order has a different number of spaces'.format(ctrl)
    
    assert set(names).issubset(newOrder), 'Cannot reorder spaces on {}, new order has different names'.format(ctrl)
    
    swapFunction = bidirectional.swap if common.isBidirectional(ctrl) else constraintBased.swap
    
    for targetIndex in range( len(names) - 1 ): # Skip the last item since ordering the second-to-last guarantees it.
        if names[targetIndex] != newOrder[targetIndex]:
            subIndex = names.index( newOrder[targetIndex] )
            swapFunction(ctrl, targetIndex, subIndex)
            
            
def addParent(control, **kwargs):
    '''
    Convenience function to add a space of the parent of the joint that the
    given control is controlling.
    '''
    
    bindBone = pdil.constraints.getOrientConstrainee(control)
    parent = bindBone.getParent()
    
    _applyDefaults( kwargs, mode=common.Mode.ROTATE_TRANSLATE, spaceName='parent' )
    
    add( control, parent, **kwargs )


def addWorldToTranslateable(control, **kwargs):
    '''
    Convenience function to split pos/target to parent and world to easily add 'world'
    to translating fk controls.
    '''
    
    bindBone = pdil.constraints.getOrientConstrainee(control)
    parent = bindBone.getParent()
    
    add(control, parent, 'main', mode=common.Mode.ALT_ROTATE, rotateTarget=find.mainGroup(fromControl=control))


def addMain(control, *args, **kwargs):
    '''
    Convenience func for adding root space, has same args as `add()`
    '''
    add( control, find.mainGroup(fromControl=control), 'main', *args, **kwargs )


def addTrueWorld(control, *args, **kwargs): # &&& TODO: rename to addWorld
    '''
    Convenience func for adding world space, has same args as `add()`
    '''
    add( control, common.getTrueWorld(), 'world', *args, **kwargs )


def addUserDriven(control, spaceName):
    targetName = pdil.simpleName(control) + '_' + spaceName
    userGroup = common.getGroup(common.Mode.USER)
    
    if targetName in userGroup.listRelatives(type='transform'):
        warning('This space/target already exists')
        return
    
    trueTarget = group(em=True, name=targetName)
    trueTarget.setParent( userGroup )
    pdil.dagObj.matchTo(trueTarget, control)
    pdil.dagObj.align(trueTarget, make=True)
    
    add(control, trueTarget, spaceName, mode=common.Mode.USER)
    
    return trueTarget


def _applyDefaults(kwargs, **defaults):
    '''
    Helper for convenience space adding attrs to process inputs and only apply
    values if the user didn't specify anything.  For example, addParent() adds
    a space called 'parent' by default but the user can specify something else.
    '''
    for k, v in defaults.items():
        if k not in kwargs:
            kwargs[k] = v
