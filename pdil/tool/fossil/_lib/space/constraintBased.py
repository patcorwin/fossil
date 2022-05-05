'''
Utilities to manage and use space switching.

..  todo:
    TEST rotate only space!  Might use same group as position only.
    Function to rename enums
'''
from __future__ import print_function, absolute_import

import collections
import logging
import numbers
import operator

from pymel.core import attributeQuery, confirmDialog, createNode, delete, parentConstraint, PyNode, skinPercent, skinCluster


import pdil

from pdil import simpleName

from ... import node

from ..._core import config
from ..._core import find
from .. import visNode

from . import common

try:
    basestring
except NameError:
    basestring = str


log = logging.getLogger(__name__)


globalSettings = pdil.ui.Settings(
    "space switching",
    {
        "autoEuler": False,
        "singleSwitchEuler": False,
    })

SpaceTarget = collections.namedtuple( 'SpaceTarget', 'name target type extra' )


USER_TARGET = 'USER_TARGET'


#------------------------------------------------------------------------------
# Because the main group needs root motion, which needs spaces, and spaces
# have helpers to target the main group, they have to live together here.
def getMainGroup(create=True, fromControl=None):
    '''
    Wraps lib.anim.getMainGroup() so code that simply needs to obtain the group
    can do so while this function actually builds all the needed parts.
    
    fromControl ensures the right mainGroup is found.
    '''

    if fromControl:
        path = fromControl.fullPath().split('|')[1:]
        for i, name in enumerate(path):
            if attributeQuery( config.FOSSIL_MAIN_CONTROL, ex=1, node=name ):
                return PyNode('|' + '|'.join( path[:i + 1] ))

    existing = node.mainGroup(create=False)
    if existing:
        return existing
    
    if create:
        main = node.mainGroup()
        addRootMotion(main)
        return main


def addRootMotion(main=None):
    rootMotion = find.rootMotion(main=main)
    
    if not rootMotion:
        #rootMotion = pdil.getNodes.getRootMotion(create=True, main=main)
        rootMotion = node.rootMotion(main=main)
        pdil.sharedShape.use(rootMotion, visNode.get())
    
    rootMotion.visibility.setKeyable(False)
    add( rootMotion, getMainGroup(), 'main_transOnly', mode=common.Mode.ALT_ROTATE, rotateTarget=common.getTrueWorld())
    add( rootMotion, common.getTrueWorld() ) # Can't use .agnostic.addTrueWorld due to import cycles
    add( rootMotion, getMainGroup(), 'main' )
#------------------------------------------------------------------------------
        

_targetInfoConstraints = []


def getTargetInfo(ctrl, returnProxyTargets=False):
    '''
    Returns a list of targets allowing for reconstruction the spaces.
    
    Additionally, it fills the _targetInfoConstraints for advanced info/usage.
    '''
    
    global _targetInfoConstraints
    _targetInfoConstraints = {}
    
    if not ctrl.hasAttr(common.ENUM_ATTR):
        return []
    
    conditions = ctrl.attr(common.ENUM_ATTR).listConnections( type='condition' )
    
    if conditions:
        for c in conditions:
            mainConstraint = c.outColorR.listConnections()
            if mainConstraint:
                mainConstraint = mainConstraint[0]
                break
    else:
        return []
    
    tempTargets = parentConstraint(mainConstraint, q=True, tl=True )
    plugs = parentConstraint(mainConstraint, q=True, wal=True )
    
    # Map the enum values to targets since the order on the constraint might differ
    targets = {}  # key = index, val=(target, space type)
    proxyTargets = {}
    for condition in conditions:
        plug = condition.outColorR.listConnections(p=True)
        
        constraint = None   # Other tools need access to the constraint of MULTI_*
        #                     and replicating 90% of the logic is dumb
        order = int(condition.secondTerm.get())
        #spaceType = condition.spaceType.get()
        spaceType = condition.spaceTypeName.get()
        extra = None
        if plug:
            plug = plug[0]
            target = tempTargets[plugs.index(plug)]
            proxyTargets[order] = target
            
            target, extra, constraint = common.Mode.getTargets(spaceType, target)
                
            targets[order] = (target, spaceType, extra)
        else:
            targets[order] = (None, spaceType, extra)
            proxyTargets[order] = None
        
        _targetInfoConstraints[order] = constraint
        
    targetAndType = [ t for (i, t) in sorted( targets.items(), key=operator.itemgetter(0))]
    _targetInfoConstraints = [ t for (i, t) in sorted( _targetInfoConstraints.items(), key=operator.itemgetter(0))]
    
    infos = [ SpaceTarget(name, target, type, extra)
                for name, (target, type, extra) in zip( common.getNames(ctrl), targetAndType ) ]
    
    if returnProxyTargets:
        return infos, [target for i, target in sorted(proxyTargets.items())]
    else:
        return infos


def clean(ctrl):
    
    #missingTargets = []
    for i, spaceTarget in enumerate(getTargetInfo(ctrl)):
        if not spaceTarget.target:
            #missingTargets.append(spaceTarget)
            res = confirmDialog(m='There is nothing connected to %s' % spaceTarget.name, b=['Delete', 'Ignore'] )
            if res == 'Delete':
                conditions = ctrl.attr(common.ENUM_ATTR).listConnections( type='condition' )
                for condition in conditions:
                    if int(condition.secondTerm.get()) == i and not condition.outColorR.listConnections(p=True):
                        delete(condition)
                        break


def remove(control, spaceNameOrIndex, shuffleRemove=False):
    '''
    Remove the space from the control.  If `shuffleRemove` is `True`, keep the
    same number of enum but make the last one marked for delete.  This means
    you can remove referenced things but it's a 3 step process:
        * shuffleRemove
        * move the anim curves to the appropriate connection in ref'ed files
        * Fully remove the end spaces marked for delete.
    
    Args:
        controls - The control with a space to be removed
        spaceNameOrIndex - String name or the index (in case a name was duplicated on accident)
        shuffleRemove - Retains the same number of spaces, but puts a 'DELETE' space at the end.
            The intention is to preserve the count if referenced, but probably not actually useful.
    
    ..  todo::
        Option to allow specifying the actual space target instead of just the name?
        
    '''

    # Adjust the condition for each one secondTerm to be one earlier
    # Mark or delete the final item
    
    names = common.getNames(control)
    
    if isinstance(spaceNameOrIndex, numbers.Number):
        index = spaceNameOrIndex
    else:
        index = names.index(spaceNameOrIndex)
    
    conditionToDelete = None
    plugToDelete = None
    # Find target and shift all the values above down to closes the gap.
    for condition in control.attr(common.ENUM_ATTR).listConnections( type='condition' ):
        plugs = condition.outColorR.listConnections(p=True)
        if condition.secondTerm.get() == index and plugs: # Verify plugs exist, otherwise it's an orphaned condition
            conditionToDelete = condition
            plugToDelete = plugs[0] if condition.outColorR.listConnections() else None
            break
            
    for condition in control.attr(common.ENUM_ATTR).listConnections( type='condition' ):
        if condition.secondTerm.get() > index:  # Shuffle all terms down
            condition.secondTerm.set( condition.secondTerm.get() - 1 )
    
    del names[index]
        
    if shuffleRemove:
        names.append( 'DELETE' )
        
    # If the last space was removed, remove the switch attr entirely
    if not names:
        control.deleteAttr(common.ENUM_ATTR)
    else:
        common.setNames( control, names )
        
    spaceGrp = pdil.dagObj.zero(control, apply=False)
    const = PyNode(parentConstraint(spaceGrp, q=True))
    
    # Since the targetList order might not match the enum order, find the
    # correct target by matching up the destination weight plug.
    if plugToDelete:
        for target, plug in zip(const.getTargetList(), const.getWeightAliasList()):
            if plug == plugToDelete:
                parentConstraint( target, const, e=True, rm=True)
                
    if conditionToDelete:
        delete(conditionToDelete)


def removeAll(control):
    ''' Removes all the spaces from the control.
    '''
    
    names = common.getNames(control)
    if not names:
        return
    
    spaceGrp = pdil.dagObj.zero(control, apply=False)
    
    delete( parentConstraint(spaceGrp, q=True) )
    
    '''
    for i, condition in enumerate(control.listConnections( type='condition' )):
        delete(condition)
        target = parentConstraint( spaceGrp, q=True, tl=True )[i]
        parentConstraint( target, spaceGrp, e=True, rm=True)
        '''
    
    if control.hasAttr(common.ENUM_ATTR):
        control.deleteAttr(common.ENUM_ATTR)
    else:
        for name in names:
            control.deleteAttr(name)


def add(control, target, spaceName='', mode=common.Mode.ROTATE_TRANSLATE, enum=True, rotateTarget=None):
    '''
    Concerns::
        Does rotate only handle being applied repeatedly without issues?
    
    ..  todo:
        * Had to change Rotate only, does translate only need the same?
            * Are certain settings for certain controls nonsense?
                * PV can be position only
                * Weapons can be rotate only
        * Possibly make a custom switch node to replace all the conditions?
        * Add test to confirm that junk names are discarded
        * Validate the name will be unique
        * When adding a space, there probably should be a more robust way to
            check for the index to add, not just using the length of existing targets.
    '''

    # Early outs
    if not target:
        print( "No target specified")
        return False
    
    modeName = mode
    
    for targetInfo in getTargetInfo(control):
        if targetInfo.type == modeName and targetInfo.target == target:
            print( "Target already exists", modeName, target)
            return False
    
    if spaceName in common.getNames(control):
        return False
    # End early outs

    rotateLocked = False
    translateLocked = False
    # If the control can't translate, make sure the mode is rotate-only.
    if control.tx.isLocked() and control.ty.isLocked() and control.tz.isLocked():
        if modeName != 'MULTI_ORIENT':
            modeName = 'ROTATE'
        translateLocked = True

    if control.rx.isLocked() and control.ry.isLocked() and control.rz.isLocked():
        rotateLocked = True
    
    with pdil.dagObj.TemporaryUnlock(control, trans=not translateLocked, rot=not rotateLocked):
        space = pdil.dagObj.zero(control, apply=False)
        
        # &&& Hack to not make two user groups, unsure which direction is the best.
        # The class probably should make the object but I can't remember if that causes some side effect.
        spaceContainer = common.getGroup(modeName, main=getMainGroup(fromControl=control) ) if modeName != 'USER' else None

        # -----------------------
        # ACTUAL SPACE ADDED HERE
        # Call the appropriate sub function to build the particulars of the space
        trueTarget, spaceName = common.Mode.build(modeName, target, spaceName, spaceContainer, rotateTarget, control, space)
        # -----------------------

        if not spaceName:
            spaceName = simpleName(target)

        existingTargets = parentConstraint( space, q=True, tl=True)

        constraint = parentConstraint( trueTarget, space, mo=True )
        constraintAttr = constraint.getWeightAliasList()[-1]
        
        if enum:
            existingNames = common.getNames(control) + [spaceName]
            if not control.hasAttr(common.ENUM_ATTR):
                control.addAttr( common.ENUM_ATTR, at='enum', enumName='FAKE', k=True )

            common.setNames(control, existingNames)

            switch = createNode('condition')
            switch.rename( 's_%i_to_%s' % (len(existingTargets), spaceName) )
            switch.secondTerm.set( len(existingTargets) )
            switch.colorIfTrue.set(1, 1, 1)
            switch.colorIfFalse.set(0, 0, 0)
            #switch.addAttr( 'spaceType', at='long', dv=mode )
            switch.addAttr( common.SPACE_TYPE_NAME, dt='string' )
            switch.spaceTypeName.set( modeName )
            
            control.attr( common.ENUM_ATTR ) >> switch.firstTerm
            switch.outColorR >> constraintAttr
            
        else:
            # &&& 2021-11-23 Does this make sense to have at all?  I think userspaces does this if needed.
            # Add float attr (but alias it to nice name?)
            #raise Exception('This is not implemented yet')
            name = '%s_%s_%s' % (common.ENUM_ATTR, spaceName, modeName)
            control.addAttr( name, at='float', min=0.0, max=1.0, k=True)
            
            control.attr(name) >> constraintAttr

    return True


class SpaceType(object):
    # Pretty sure this is trash

    #EXTERNAL = -1           # Here for taking advantage of the get group code.

    #ROTATE_TRANSLATE = 0    # Acts just like a child of the target
    SINGLE_PARENT = 'single_parent'

    MULTI_PARENT = 'multi_parent'
    # DUAL_PARENT = 5         # ParentConstraint to two objs
    # MULTI_PARENT = 7        # The base of a "rivet"
    # ALT_ROTATE = 3          # Acts as a child of the target positionally but is rotationally follows the second target
    #   Adjust weights so 1st parent is p=1, o=0 and second is p=0 o=1
    # MULTI_ORIENT = 8        # Only has an orient constraint
    #   target 0 is parent obj, p=1,o=0 and the remainder are p=0,o>0
    # ROTATE = 2              # Only follows rotation, not translation.  Probably only ever for rotate only controls
    #   identical to multi orient but a single target


    # Not actualy needed, I think. SINGLE_FOLLOW = 'single_follow'
    #DUAL_FOLLOW = 6         # A point and orient to two objs (aka position is alway linearly interpreted between points regardless of target rotation)
    MULTI_FOLLOW = 'multi_follow'
    # TRANSLATE = 1           # If the target translates, it follows but not if the target rotates
    #   p=1, o=0
    
    # REMOVE
    #POINT_ORIENT = 4        # Does a point and orient, which is only relevant if doing non-enum attr
    
    # Get rid of this since the new multis have weighting powers and `user` allows for other nonesense
    # FREEFORM = 10           # Allows several targets in different configurations, I do what I want!
    USER = 'user'               # User constrains this object as needed


def swap(ctrl, spaceAIndex, spaceBIndex):
    ''' Swap the spaces on `ctrl` by index
    
    ..  todo::
        Possibly rename the condition to reflect the new number.
    '''
    
    if not ctrl.hasAttr(common.ENUM_ATTR):
        return
        
    names = common.getNames(ctrl)
    
    if len(names) <= max(spaceAIndex, spaceBIndex):
        return
        
    temp = names[spaceAIndex]
    names[spaceAIndex] = names[spaceBIndex]
    names[spaceBIndex] = temp
    
    common.setNames( ctrl, names )
        
    conditions = ctrl.attr(common.ENUM_ATTR).listConnections( type='condition' )
    
    for condition in conditions:
        if condition.secondTerm.get() == spaceAIndex:
            condition.secondTerm.set(spaceBIndex)
            
        elif condition.secondTerm.get() == spaceBIndex:
            condition.secondTerm.set(spaceAIndex)


def rivetSpace(ctrl, vert, name=''):
    skin = pdil.weights.findRelatedSkinCluster(vert.node())
    
    if not skin:
        return
    
    vals = skinPercent(skin, vert, q=True, v=True )
    jnts = skinCluster(skin, q=True, inf=True)

    targets = []
    weights = []

    for v, j in zip(vals, jnts):
        if v:
            targets.append(j)
            weights.append(v)
    
    add( ctrl, targets, spaceName=name, mode=common.Mode.MULTI_PARENT, enum=True, rotateTarget=weights)
    

def fixUnhookedSpaces(ctrl):
    '''
    Preliminary tool to deal with messed up spaces.
    
    Right now ONLY deals if there is a space name and destination unhookedup.
    FILL IN OTHERS WITH ERROR IN NAME???
    '''
    
    names = common.getNames(ctrl)
    space = pdil.dagObj.zero(ctrl, apply=False)
    constraint = PyNode(parentConstraint(space, q=True))
    targetPlugs = constraint.getWeightAliasList()
    
    if len(names) != len(targetPlugs):
        print( 'There are', len(names), 'but', len(targetPlugs), ', you will need to figure out what is right!')
    
    noDriver = {}
    for i, plug in enumerate(targetPlugs):
        cons = plug.listConnections(s=True, d=False)
        if not cons:
            noDriver[i] = plug
            
    #
    connected = {}
    unconnected = []
    conditions = ctrl.attr(common.ENUM_ATTR).listConnections( type='condition' )
    
    for c in conditions:
        con = c.outColorR.listConnections()
        if con:
            order = c.secondTerm.get()
            connected[order] = con[0]
        else:
            unconnected.append(c)
    
    missingIndex = range(len(targetPlugs))
    for i in connected:
        missingIndex.remove(i)
    
    if len(noDriver) == 1 and len(unconnected) == 1:
        print( noDriver, unconnected )
        print( connected.keys() )
        print( missingIndex )
        
        print( 'Autofixing!', noDriver.values()[0], 'is "%s"' % names[missingIndex[0]] )
        unconnected[0].secondTerm.set(missingIndex[0])
        #print( noDriver.values()[0] )
        unconnected[0].outColorR >> noDriver.values()[0]
    
    if not noDriver and not unconnected:
        print( 'All good!' )
    else:
        print( 'This had some errors' )
        
    'FILL IN OTHERS WITH ERROR IN NAME???'