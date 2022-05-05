'''
TODO:

This should hook into the ik/fk of the leg, and doesn't unbuild properly, you have to delete the leg too.

'''
from __future__ import absolute_import, division, print_function

#import collections

from collections import OrderedDict
from functools import partial

try:
    from enum import Enum
except ImportError:
    from pdil.vendor.enum import Enum

from pymel.core import createNode, group, hide, ikHandle, joint, move, rotate, xform, upAxis, duplicate

import pdil

from ..cardRigging import MetaControl, OutputControls, colorParity, Param
from .._core import config
from .._lib import space
from .._lib2 import controllerShape
from .. import enums
from .. import log
from .. import node

from . import _util as util


class FootHierarchy(Enum):
    BALL_TOE_HEEL = 'Ball Toe Heel'
    BALL_HEEL_TOE = 'Ball Heel Toe'
    
    TOE_HEEL_BALL = 'Toe Heel Ball'
    TOE_BALL_HEEL = 'Toe Ball Heel'
    
    HEEL_BALL_TOE = 'Heel Ball Toe'
    HEEL_TOE_BALL = 'Heel Toe Ball'


MAYA_UP = upAxis(q=True, ax=True)


@util.adds('tiptoe', 'heelRaise', 'toeTap', 'ballPivot')
@util.defaultspec(     {'shape': 'disc',      'size': 15, 'color': 'blue 0.22', 'align': MAYA_UP},
            toeControl={'shape': 'sphere',    'size': 10, 'color': 'blue 0.22'},
             ballPivot={'shape': 'band',      'size': 10, 'color': 'green 0.22', 'align': MAYA_UP},
                toeTap={'shape': 'cuff',      'size': 10, 'color': 'green 0.22'},
             heelRaise={'shape': 'cuff',      'size': 10, 'color': 'red 0.22', 'align': MAYA_UP},
                )
def buildFoot(ballJnt, toePos, ballPos, heelPos, legControl, side, hierarchy, controlSpec={}):
    if not side:
        side = ''
    
    # The foot container
    container = group(n='FancyFoot_{}'.format(side), em=True, p=node.mainGroup())
    
    # Fake joints for IK/FK switching tech
    ankle = joint(None, n='FakeAnkle')
    ball = joint(n='FakeBall')
    toe = joint(n='FakeToe')
    hide(ankle)
    
    # Place the "Fake" joints
    pdil.dagObj.moveTo(ankle, legControl)
    pdil.dagObj.moveTo(ball, ballJnt)# ballPos)
    pdil.dagObj.moveTo(toe, toePos)
    
    # IK gathering
    ballIk, effector = ikHandle(solver='ikSCsolver', sj=ankle, ee=ball)
    toeIk, effector = ikHandle(solver='ikSCsolver', sj=ball, ee=toe)
    hide(ballIk, toeIk)
    
    # Heel Control
    footCtrl = controllerShape.build( "Heel" + side + "_ctrl", controlSpec['main'], type=controllerShape.ControlType.TRANSLATE )
    pdil.dagObj.moveTo(footCtrl, heelPos)
    footCtrl = pdil.nodeApi.RigController.convert(footCtrl)
    footCtrl.container = container
    
    # HeelTilt (for Roll automation)
    heelRoll = group(em=True, n='heel' + side + '_tweak')
    pdil.dagObj.moveTo(heelRoll, heelPos)
    heelRoll.setParent(footCtrl)
    
    # Toe Control
    toeCtrl = controllerShape.build( 'Toe' + side + '_ctrl', controlSpec['toeControl'], type=controllerShape.ControlType.TRANSLATE )
    pdil.dagObj.matchTo(toeCtrl, toe)
    footCtrl.subControl['toe'] = toeCtrl
    
    # Ball Control
    ballCtrl = controllerShape.build( 'Ball' + side + '_ctrl', controlSpec['ballPivot'], type=controllerShape.ControlType.TRANSLATE )
    pdil.dagObj.moveTo(ballCtrl, ballPos)
    footCtrl.subControl['ball'] = ballCtrl
    
    # Toe Tap Control
    toeTapCtrl = controllerShape.build( 'ToeTap' + side + '_tweak', controlSpec['toeTap'], type=controllerShape.ControlType.ROTATE )
    pdil.dagObj.moveTo(toeTapCtrl, ballJnt)
    toeIk.setParent(toeTapCtrl)
    footCtrl.subControl['toeTap'] = toeTapCtrl
    
    # Heel Raise Control
    heelRaiseCtrl = controllerShape.build( 'HeelRaise' + side + '_tweak', controlSpec['heelRaise'], type=controllerShape.ControlType.ROTATE )
    pdil.dagObj.moveTo(heelRaiseCtrl, ballPos)
    footCtrl.subControl['heel'] = heelRaiseCtrl
    
    # Put the heelRaiseCtrl shape at the heel, not at it's pivot
    delta = pdil.dagObj.getPos(footCtrl) - pdil.dagObj.getPos(heelRaiseCtrl)
    for shape in pdil.shape.getNurbsShapes(heelRaiseCtrl):
        rotate(shape.cv[:], [180, 0, 0], os=True)
        move(shape.cv[:], delta, r=True)
        
    # Cheesily decode the value instead of a large if/else chain
    controlOrder = hierarchy.value.lower().split(' ')
    
    # Since the heel has multiple parts, the first item is the top control in that
    # sub section, and the second is the last
    controls = {
        'container': [container, container],
        'heel': [footCtrl, heelRoll],
        'toe': [toeCtrl, toeCtrl],
        'ball': [ballCtrl, ballCtrl],
    }
    
    for child, parent in zip(controlOrder, ['container'] + controlOrder[:2] ):
        parent = controls[parent][1]
        child = controls[child][0]
        child.setParent( parent )
        pdil.dagObj.zero(child)
    
    lastCtrl = controls[ controlOrder[-1] ][1]
    
    ankle.setParent( lastCtrl )
    
    toeTapCtrl.setParent(lastCtrl)
    pdil.dagObj.zero(toeTapCtrl)
    
    ballIk.setParent(lastCtrl)
    
    # Add spaces the the parent ik control
    footSpace = 'foot'
    # &&& This needs to be more robust, look at the idspec instead in case it's renamed or the hierarchy changes
    if footSpace in space.getNames(legControl):
        space.remove(legControl, footSpace)
    
    # If there aren't any spaces, also add a main as well as the foot space
    if not space.getNames(legControl):
        space.addMain(legControl)
    
    space.add(legControl, heelRaiseCtrl, footSpace)
    heelRaiseCtrl.setParent(lastCtrl)
    pdil.dagObj.zero(heelRaiseCtrl)
    
    # Setup foot roll attrs
    leadCtrl = controls[ controlOrder[0] ][0]
    
    # Drive the align groups for common motions to keep down on clutter
    #util.drive(footCtrl, 'tiptoe', toeCtrl.getParent().rx, dv=0, minVal=0)
    #util.drive(footCtrl, 'heelRaise', heelRaiseCtrl.getParent().rx, dv=0, maxVal=0, flipped=True)
    '''util.drive(footCtrl, 'toeTap', toeTapCtrl.getParent().rx, dv=0, minVal=-30, flipped=True)'''
    '''util.drive(footCtrl, 'ballPivot', ballCtrl.getParent().attr('r' + MAYA_UP), dv=0)'''
    
    rollMin = -2
    rollMax = 10
    
    zero = -rollMin / float(rollMax - rollMin)
    mid = ((rollMax / 2) - rollMin) / float(rollMax - rollMin)
    
    leadCtrl.addAttr('roll', at='double', min=rollMin, max=rollMax, k=True)
    leadCtrl.addAttr('heelBack', at='double', dv=-25, k=True)
    leadCtrl.addAttr('heelLift', at='double', dv=45, k=True)
    leadCtrl.addAttr('toeLift', at='double', dv=60, k=True)
    
    
    heelBackRemap = createNode('remapValue', n='heelBack')
    heelBackRemap.value[0].value_FloatValue.set(1)
    heelBackRemap.value[1].value_Position.set( zero )
    heelBackRemap.value[1].value_FloatValue.set(0)
    
    heelBackRemap.inputMin.set(-2)
    heelBackRemap.inputMax.set(10)
    heelBackRemap.outputMin.set(0)
    leadCtrl.heelBack >> heelBackRemap.outputMax
    
    
    heelLiftRemap = createNode('remapValue', n='heelLift')
    heelLiftRemap.value[0].value_Position.set( zero )
    heelLiftRemap.value[0].value_FloatValue.set(0)
    
    heelLiftRemap.value[1].value_Position.set( mid )
    heelLiftRemap.value[1].value_FloatValue.set(1)
    
    heelLiftRemap.value[2].value_Position.set(1)
    heelLiftRemap.value[2].value_FloatValue.set(0)
    
    heelLiftRemap.inputMin.set(-2)
    heelLiftRemap.inputMax.set(10)
    heelLiftRemap.outputMin.set(0)
    leadCtrl.heelLift >> heelLiftRemap.outputMax
    
    
    tipToeRemap = createNode('remapValue', n='tipToe')
    tipToeRemap.value[0].value_Position.set( mid )
    tipToeRemap.value[0].value_FloatValue.set(0)
    
    tipToeRemap.value[1].value_Position.set( 1 )
    tipToeRemap.value[1].value_FloatValue.set(1)
    
    tipToeRemap.inputMin.set(-2)
    tipToeRemap.inputMax.set(10)
    tipToeRemap.outputMin.set(0)
    leadCtrl.toeLift >> tipToeRemap.outputMax
    
    
    heelBackRemap.outValue >> heelRoll.rx
    heelLiftRemap.outValue >> heelRaiseCtrl.getParent().rx
    tipToeRemap.outValue >> toeCtrl.getParent().rx
    
    leadCtrl.roll >> heelBackRemap.inputValue
    leadCtrl.roll >> heelLiftRemap.inputValue
    leadCtrl.roll >> tipToeRemap.inputValue
    
    # Finally, make the actual object that will drive the bind joint
    ballOffset = joint(ball, n='ballOffset')
    pdil.dagObj.matchTo(ballOffset, ballJnt)
    pdil.dagObj.lock( ballOffset )
    
    #-
    midCtrl = controls[ controlOrder[1] ][0]
    
    pdil.dagObj.lock( leadCtrl, 's' )
    pdil.dagObj.lock( midCtrl, 't s' )
    pdil.dagObj.lock( lastCtrl, 't s' )
    
    pdil.dagObj.lock( toeTapCtrl, 't s' )
    pdil.dagObj.lock( heelRaiseCtrl, 't s' )
    
    constraints = util.constrainAtoB( [ballJnt], [ballOffset], mo=True )
    
    return footCtrl, constraints
    
    
class Foot(MetaControl):
    '''
    Adds fancy rolls and pivots. Requires 4 joints:
        * Toe - For toe tapping
        The next 3 are helper joints and should on the floor vertically.
        * Toe Tip - The very front of the foot
        * Ball pivot
        * Heel - The very back of the foot
    '''
    
    ik_ = 'pdil.tool.fossil.rigging.foot.buildFoot'
    
    ikInput = OrderedDict( [
        ( 'hierarchy', Param(FootHierarchy.BALL_HEEL_TOE, 'Hierarchy', 'The order that the controls carry each other'), ),
    ] )
    
    @classmethod
    def validate(cls, card):
        if len(card.joints) > 3:
            return ['You need 4 joints, the toe, a helper representing the toe tip, helpr for ball pivot point, and a helper representing the back of the heel.']
        return None
    
    @classmethod
    def build(cls, card, buildFk=True):
        '''
        '''
        
        #assert cls.validate(card) is None
        
        toePivotHelper = card.joints[-3]
        ballPivotHelper = card.joints[-2]
        heelPivotHelper = card.joints[-1]

        toePos = xform(toePivotHelper, q=True, ws=True, t=True)
        ballPos = xform(ballPivotHelper, q=True, ws=True, t=True)
        heelPos = xform(heelPivotHelper, q=True, ws=True, t=True)
        
        previousJoint = card.joints[0].parent
        # Right now it's so much easier with the foot built off another structure.
        assert previousJoint.card.rigData.get( enums.RigData.rigCmd ) in ('DogFrontLeg', 'DogHindleg', 'IkChain'), 'Parent cardd needs to be IkChain'
        
        legCard = previousJoint.card
        #print('prev card', legCard, previousJoint, legCard.outputLeft.ik, legCard.outputRight.ik)
        
        side = card.findSuffix()
        
        #if not util.canMirror( card.start() ) or card.isAsymmetric():
        if not side or card.isAsymmetric():
            legControl = legCard.outputCenter.ik
            suffix = card.findSuffix()
            
            if suffix:
                ctrls = cls._buildSide(card, card.start().real, card.end().real, toePos, ballPos, heelPos, legControl, False, suffix, buildFk=buildFk)
            else:
                ctrls = cls._buildSide(card, card.start().real, card.end().real, toePos, ballPos, heelPos, legControl, False, buildFk=buildFk)

            card.outputCenter.ik = ctrls.ik
            card.outputCenter.fk = ctrls.fk
            
        else:
            legControl = legCard.getSide(side).ik
            #suffix = config.controlSideSuffix(side)
            ctrls = cls._buildSide(card, card.start().real, card.end().real, toePos, ballPos, heelPos, legControl, False, side, buildFk=buildFk)
            card.getSide(side).ik = ctrls.ik
            card.getSide(side).fk = ctrls.fk

            otherSide = config.otherSideCode(side)
            #otherSuffix = config.controlSideSuffix(otherSide)
            otherLegControl = legCard.getSide(otherSide).ik
            toePos[0] *= -1
            ballPos[0] *= -1
            heelPos[0] *= -1
            ctrls = cls._buildSide(card, card.start().realMirror, card.end().realMirror, toePos, ballPos, heelPos, otherLegControl, True, otherSide, buildFk=buildFk)
            card.getSide(otherSide).ik = ctrls.ik
            card.getSide(otherSide).fk = ctrls.fk
        
        
        #pivotPoint = xform(card.joints[-1], q=True, ws=True, t=True)
        #joints = [j.real for j in card.joints[:-1]]
    
        #ikControlSpec = cls.controlOverrides(card, 'ik')
        
    
    @classmethod
    def _buildSide( cls, card, ballJoint, end, toePos, ballPos, heelPos, legControl, isMirroredSide, side=None, buildFk=True ):
        
        log.Rotation.check([ballJoint], True)
        if side == 'left':
            sideAlteration = partial( colorParity, 'L' )
        elif side == 'right':
            sideAlteration = partial( colorParity, 'R' )
        else:
            sideAlteration = lambda **kwargs: kwargs  # noqa
        
        fkCtrl = None
        
        if buildFk:
            fkControlSpec = cls.controlOverrides(card, 'fk')
            fkGroupName = card.getGroupName( **fkControlSpec )
            
            #kwargs = collections.defaultdict(dict)
            kwargs = cls.readFkKwargs(card, isMirroredSide, sideAlteration)
            kwargs.update( cls.fkArgs )
            kwargs['controlSpec'].update( cls.fkControllerOptions )
            kwargs.update( sideAlteration(**fkControlSpec) )
            
            names = card.nameList(excludeSide=True)
            if side:
                names = [n + config.controlSideSuffix(side) for n in names]
            kwargs['names'] = names
            
            fkCtrl, fkConstraints = cls.fk( ballJoint, end, groupName=fkGroupName, **kwargs )
            
            # Ik is coming, disable fk so ik can lay cleanly on top.  Technically it shouldn't matter but sometimes it does.
            for const in fkConstraints:
                const.set(0)
        
        
        # Don't want to flip orientation of IK controls
        if side == 'left':
            ikSideAlteration = partial( colorParity, 'L', conditionalflipAlign=False )
        elif side == 'right':
            ikSideAlteration = partial( colorParity, 'R', conditionalflipAlign=False )
        else:
            ikSideAlteration = lambda **kwargs: kwargs  # noqa
        
        ikControlSpec = cls.controlOverrides(card, 'ik')
        
        kwargs = cls.readIkKwargs(card, isMirroredSide, ikSideAlteration)
        kwargs.update( cls.ikArgs )
        kwargs['controlSpec'].update( cls.ikControllerOptions )
        kwargs.update( ikSideAlteration(**ikControlSpec) )
        
        #fkCtrl, fkConstraints = rig.fkChain(ballJoint, ballJoint, translatable=True)
        #print('ik args', ballJoint, toePos, ballPos, heelPos, legControl, side)
        suffix = config.controlSideSuffix(side)
        ikCtrl, ikConstraints = cls.ik( ballJoint, toePos, ballPos, heelPos, legControl, suffix, **kwargs )
        
        if cls.ik and cls.fk and buildFk:
            controllerShape.addIkFkSwitch( ikCtrl.name(), ikCtrl, ikConstraints, fkCtrl, fkConstraints )
        
        #switchPlug = controller.addIkFkSwitch( ballJoint.name(), ikCtrl, ikConstraints, fkCtrl, fkConstraints )
        
        return OutputControls(fkCtrl, ikCtrl)