from __future__ import absolute_import, division, print_function

import numbers
import operator

from pymel.core import createNode, delete, listConnections, parentConstraint, PyNode
import pdil


from ..._core import find
from . import constraintBased as traditional
from . import common


BIDIRECTIONAL_ID = 'bidirectional'


def add(control, target, spaceName='', modeName=common.Mode.ROTATE_TRANSLATE, enum=True, rotateTarget=None):
    ''' Add a space to the given control.
    
    Args:
        control: Add the space to it
        target: What to target
        modeName: String name for what type of space
        enum: DEPRECATED unused
        rotateTarget: Now a catch-all for lots of additional data depending on the mode
    '''

    # Early outs
    if not target:
        print( "No target specified")
        return False
    
    for targetInfo in getTargetInfoBD(control):
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
        spaceContainer = common.getGroup(modeName, main=find.mainGroup(fromControl=control) ) if modeName != 'USER' else None

        # -----------------------
        # ACTUAL SPACE ADDED HERE
        # Call the appropriate sub function to build the particulars of the space
        trueTarget, spaceName = common.Mode.build(modeName, target, spaceName, spaceContainer, rotateTarget, control, space)
        # -----------------------

        if not spaceName:
            spaceName = pdil.simpleName(target)
        existingNames = common.getNames(control) + [spaceName]
        if not control.hasAttr( common.ENUM_ATTR):
            control.addAttr( common.ENUM_ATTR, at='enum', enumName='FAKE', k=True )
        common.setNames(control, existingNames)


        choice = getChoiceNode(control)
        if not choice:
            choice = makeChoiceNode()
            decomp = createNode('decomposeMatrix')
            choice.output >> decomp.inputMatrix
            control.space >> choice.selector
        else:
            decomp = choice.output.listConnections()[0]

        offsetMatrix = addTarget(choice, trueTarget, control, space, choice.input.numElements())
        offsetMatrix.addAttr( common.SPACE_TYPE_NAME, dt='string' )
        offsetMatrix.attr( common.SPACE_TYPE_NAME ).set( modeName )

        if len(existingNames) == 1: # At this stage, this means this is the first space so decomp needs hookup.
            decomp.outputTranslate >> space.t
            decomp.outputRotate >> space.r
            
    return True


def makeChoiceNode():
    node = createNode('choice')
    
    node.addAttr('fossilData', dt='string')
    node.fossilData.set(BIDIRECTIONAL_ID)
    
    return node


def addTarget(choice, target, ctrl, zero, i):
    ''' Helper function that appends and entry to the given choice node.
    '''
    offsetMatrix = createNode('fourByFourMatrix')
    
    # If I want a transform relative to another I multiply by the inverse world of the other
    delta = ctrl.worldMatrix[0].get() * target.worldInverseMatrix[0].get()
    
    set4x4Matrix(offsetMatrix, delta)
    
    mult = createNode('multMatrix')
    
    offsetMatrix.output >> mult.matrixIn[0]
    target.worldMatrix[0] >> mult.matrixIn[1]
    zero.parentInverseMatrix[0] >> mult.matrixIn[2]
    
    mult.matrixSum >> choice.input[i]

    return offsetMatrix


def set4x4Matrix(node, values):
    _matrixPlugs = ['in%i%i' % (r, c) for r in range(4) for c in range(4)] # Make 4x4 inputs: in00 .. in33
    for name, val in zip(_matrixPlugs, [col for row in values for col in row]):
        node.attr(name).set(val)


def _convertToBD(targets, obj):

    choice = makeChoiceNode()
    decomp = createNode('decomposeMatrix')
    
    choice.output >> decomp.inputMatrix
    
    zero = pdil.dagObj.zero(obj, False, False)
    
    offsets = []
    
    for i, target in enumerate(targets):
        offsets.append( addTarget(choice, target, obj, zero, i) )
        """
        offsetMatrix = createNode('fourByFourMatrix')
        offsets.append(offsetMatrix)
        
        # If I want a transform relative to another I multiply by the inverse world of the other
        delta = obj.worldMatrix[0].get() * target.worldInverseMatrix[0].get()
        
        set4x4Matrix(offsetMatrix, delta)
        #for name, val in zip(_matrixPlugs, [col for row in delta for col in row]):
        #    offsetMatrix.attr(name).set(val)
        
        mult = createNode('multMatrix')
        
        offsetMatrix.output >> mult.matrixIn[0]
        target.worldMatrix[0] >> mult.matrixIn[1]
        zero.parentInverseMatrix[0] >> mult.matrixIn[2]
        
        mult.matrixSum >> choice.input[i]
        """
    
    decomp.outputTranslate >> zero.t
    decomp.outputRotate >> zero.r
    
    return offsets, choice
    
    
def convertToBidirectional(ctrl):
    
    zero = pdil.dagObj.zero(ctrl, False, False)
    
    const = PyNode(parentConstraint( zero, q=True ))
    
    infos, proxyTargets = traditional.getTargetInfo(ctrl, returnProxyTargets=True)
    
    delete(const)
    
    offsets, choice = _convertToBD(proxyTargets, ctrl)
    
    if not ctrl.hasAttr('space'):
        ctrl.addAttr( 'space', at='enum', enumName=':'.join( t.name() for t in proxyTargets ), k=True )
    
    ctrl.space >> choice.selector
    
    for offset, info in zip(offsets, infos):
        offset.addAttr( common.SPACE_TYPE_NAME, dt='string' )
        offset.attr( common.SPACE_TYPE_NAME ).set( info.type )
        

def getChoiceNode(ctrl):
    ''' Returns the choice node that manages the bidirectional constraint.
    '''
    if not ctrl.hasAttr(common.ENUM_ATTR):
        return None
    
    choiceNode = [node for node in ctrl.attr(common.ENUM_ATTR).listConnections( type='choice', s=False, d=True )
                    if node.hasAttr('fossilData') and node.fossilData.get() == BIDIRECTIONAL_ID]
    
    return choiceNode[0] if choiceNode else None


def getTargetInfoBD(ctrl, intSpaceType=False):
    ''' Returns a list of targets allowing for reconstruction the spaces.
    
    Additionally, it fills the _targetInfoConstraints for advanced info/usage.
    
    ..todo: Explain _targetInfoConstraints better, I think it's only for rivet
    space editing weights on the specific constraints?  Does this return the proxy's
    constraints?
    
    '''
    
    global _targetInfoConstraints
    _targetInfoConstraints = {}
            
    choiceNode = getChoiceNode(ctrl)
    
    if not choiceNode:
        return []
    
    targets = [None] * choiceNode.input.numElements() # Unlike regular version, order cannot be out of sync so prepopulate
    for order, option in enumerate(choiceNode.input):
        
        multiplyNode = option.listConnections(s=True, d=False)[0]
        
        offsetMatrix = multiplyNode.matrixIn[0].listConnections()[0]
        proxyTarget = multiplyNode.matrixIn[1].listConnections()

        spaceType = offsetMatrix.spaceTypeName.get()
        
        constraint = None
        extra = None
        if proxyTarget:
            proxyTarget = proxyTarget[0]
            
            target, extra, constraint = common.Mode.getTargets( getattr(common.Mode, spaceType), proxyTarget)

            targets[order] = (target, spaceType, extra)
        else:
            targets[order] = (None, spaceType, extra)
        
        _targetInfoConstraints[order] = constraint
        

    _targetInfoConstraints = [ t for (i, t) in sorted( _targetInfoConstraints.items(), key=operator.itemgetter(0))]
    
    """
    if intSpaceType:
        return [ traditional.SpaceTarget(name, target, getattr(common.Mode, spaceType), extra)
                 for name, (target, spaceType, extra) in zip( traditional.getNames(ctrl), targets ) ]
    else:
        """
    return [ traditional.SpaceTarget(name, target, spaceType, extra)
             for name, (target, spaceType, extra) in zip( common.getNames(ctrl), targets ) ]


def swap(ctrl, spaceAIndex, spaceBIndex):
    ''' Swap the spaces on `ctrl` by index
    '''
    
    if not ctrl.hasAttr(common.ENUM_ATTR):
        return
    names = common.getNames(ctrl)
    choice = getChoiceNode(ctrl)
    if len(names) <= max(spaceAIndex, spaceBIndex) or not choice:
        return
        
    # Do the name swap
    temp = names[spaceAIndex]
    names[spaceAIndex] = names[spaceBIndex]
    names[spaceBIndex] = temp
    common.setNames( ctrl, names )
    
    # Swap choice node inputs
    inputA = choice.input[spaceAIndex].listConnections()[0]
    inputB = choice.input[spaceBIndex].listConnections()[0]
    inputA.matrixSum >> choice.input[spaceBIndex]
    inputB.matrixSum >> choice.input[spaceAIndex]


def remove(ctrl, spaceNameOrIndex, shuffleRemove=False):
    ''' Remove the space from the control
    
    Use `shuffleRemove=True` to add 'DELETE' as an enum and update animation
    connections in referenced files before shorting the enum list.
    
    Args:
        ctrl: The control with a space to be removed
        spaceNameOrIndex: String name or the index (in case a name was duplicated on accident)
        shuffleRemove: Retains the same number of spaces, but puts a 'DELETE' space at the end.
            The intention is to preserve the count if referenced, but probably not actually useful.
    '''
    names = common.getNames(ctrl)
    
    zero = pdil.dagObj.zero(ctrl, False, False)
    trans = zero.t.get()
    rot = zero.r.get()
    
    if isinstance(spaceNameOrIndex, numbers.Number):
        index = spaceNameOrIndex
    else:
        index = names.index(spaceNameOrIndex)
        
    choice = getChoiceNode(ctrl)
    
    removedMultMatrix = choice.input[index].listConnections()
    offsets = listConnections(removedMultMatrix, d=False, s=True, type='fourByFourMatrix')
    
    # Shuffle the choice.input's to put the empty one last to disconnect
    for i in range(index, choice.input.numElements() - 1 ):
        multMatrix = choice.input[i + 1].listConnections()[0]
        multMatrix.matrixSum >> choice.input[i]
    
    last = choice.input.getArrayIndices()
    if last:
        choice.input[last[-1]].disconnect()

    delete( removedMultMatrix, offsets ) # Delete the input matrix nodes AFTER connections shuffle in case last was removed
    
    # Update the name enum
    del names[index]
        
    if shuffleRemove:
        names.append( 'DELETE' )
        
    if not names:
        # If the last space was removed, remove the switch attr entirely
        ctrl.deleteAttr(common.ENUM_ATTR)
        delete(choice)
        
        zero.t.set(trans) # Removing in normal use appears fine, but in tests,
        zero.r.set(rot)   # the transform zeros so restore it just in case
    else:
        common.setNames( ctrl, names )


def removeAll(ctrl):
    choiceNode = getChoiceNode(ctrl)

    if not choiceNode:
        return
    
    zero = pdil.dagObj.zero(ctrl, False, False)
    trans = zero.t.get()
    rot = zero.r.get()
    
    multMatrix = choiceNode.listConnections(type='multMatrix')
    offsets = listConnections(multMatrix, d=False, s=True, type='fourByFourMatrix')
    delete(choiceNode, multMatrix, offsets)
                 
    ctrl.deleteAttr(common.ENUM_ATTR)

    zero.t.set(trans) # Removing in normal use appears fine, but in tests,
    zero.r.set(rot)   # the transform zeros so restore it just in case
