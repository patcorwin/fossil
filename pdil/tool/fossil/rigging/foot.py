'''
TODO:

This should hook into the ik/fk of the leg, and doesn't unbuild properly, you have to delete the leg too.

'''
from __future__ import absolute_import, division, print_function

import collections

from functools import partial

from pymel.core import group, hide, ikHandle, joint, move, rotate, select, xform, upAxis

from .... import core
from .... import lib
from .... import nodeApi

from .. import controllerShape


from ..cardRigging import MetaControl, OutputControls, colorParity
from .. import log
from .. import space

from . import _util as util


MAYA_UP = upAxis(q=True, ax=True)


@util.adds('tiptoe', 'heelRaise', 'toeTap', 'ballPivot')
@util.defaultspec(     {'shape': 'disc',      'size': 15, 'color': 'blue 0.22', 'align': MAYA_UP},
            toeControl={'shape': 'sphere',    'size': 10, 'color': 'blue 0.22'},
             ballPivot={'shape': 'band',      'size': 10, 'color': 'green 0.22', 'align': MAYA_UP},
                toeTap={'shape': 'cuff',      'size': 10, 'color': 'green 0.22'},
             heelRaise={'shape': 'cuff',      'size': 10, 'color': 'red 0.22', 'align': MAYA_UP},
                )
def buildFoot(ballJnt, toePos, heelPos, legControl, side, controlSpec={}):
    if not side:
        side = ''
    
    # The foot container
    container = group(n='FancyFoot_{}'.format(side.title()), em=True, p=lib.getNodes.mainGroup())
    
    # Fake joints for IK/FK switching tech
    ankle = joint(None, n='FakeAnkle')
    ball = joint(n='FakeBall')
    toe = joint(n='FakeToe')
    hide(ankle)
    
    # IK gathering
    ballIk, effector = ikHandle(solver='ikSCsolver', sj=ankle, ee=ball)
    toeIk, effector = ikHandle(solver='ikSCsolver', sj=ball, ee=toe)
    hide(ballIk, toeIk)
    
    # Place the "Fake" joints
    core.dagObj.moveTo(ankle, legControl)
    core.dagObj.moveTo(ball, ballJnt)
    core.dagObj.moveTo(toe, toePos)
    
    #Foot Control
    footCtrl = controllerShape.build( "Foot_" + side + "_ctrl", controlSpec['main'], type=controllerShape.ControlType.TRANSLATE )
    core.dagObj.moveTo(footCtrl, heelPos)
    footCtrl.setParent(container)
    core.dagObj.zero(footCtrl)
    footCtrl = nodeApi.RigController.convert(footCtrl)
    footCtrl.container = container
        
    # Toe Control
    toeCtrl = controllerShape.build( "Toe_" + side + "_ctrl", controlSpec['toeControl'], type=controllerShape.ControlType.TRANSLATE )
    core.dagObj.matchTo(toeCtrl, toe)
    #toeCtrl.setRotation( legControl.getRotation(space='world'), space='world' )
    toeCtrl.setParent(footCtrl)
    ankle.setParent(toeCtrl)
    core.dagObj.zero(toeCtrl)
    footCtrl.subControl['toe'] = toeCtrl
    
    # Ball Control
    ballCtrl = controllerShape.build( "Ball_" + side + "_ctrl", controlSpec['ballPivot'], type=controllerShape.ControlType.TRANSLATE )
    core.dagObj.moveTo(ballCtrl, ballJnt)
    ballIk.setParent(ballCtrl)
    ballCtrl.setParent(toeCtrl)
    core.dagObj.zero(ballCtrl)
    footCtrl.subControl['ball'] = ballCtrl
    
    # Toe Tap Control
    toeTapCtrl = controllerShape.build( "ToeTap_" + side + "_ctrl", controlSpec['toeTap'], type=controllerShape.ControlType.ROTATE )
    core.dagObj.moveTo(toeTapCtrl, ballJnt)
    toeIk.setParent(toeTapCtrl)
    toeTapCtrl.setParent(ballCtrl)
    core.dagObj.zero(toeTapCtrl)
    footCtrl.subControl['toeTap'] = toeTapCtrl
    
    # Heel Raise Control
    heelRaiseCtrl = controllerShape.build( "HeelRaise_" + side + "_ctrl", controlSpec['heelRaise'], type=controllerShape.ControlType.ROTATE )
    core.dagObj.moveTo(heelRaiseCtrl, ballJnt)
    footCtrl.subControl['heel'] = heelRaiseCtrl
    
    # Put the heelRaiseCtrl shape at the heel, not at it's pivot
    delta = core.dagObj.getPos(footCtrl) - core.dagObj.getPos(heelRaiseCtrl)
    for shape in core.shape.getShapes(heelRaiseCtrl):
        rotate(shape.cv[:], [180, 0, 0], os=True)
        move(shape.cv[:], delta, r=True)
    
    
    select(d=True)
    space.add(legControl, heelRaiseCtrl)
    heelRaiseCtrl.setParent(ballCtrl)
    core.dagObj.zero(heelRaiseCtrl)
    
    # Set the leg control Pivot to the heel
    xform(legControl, ws=True, rp=heelPos)
    
    # Drive the align groups for common motions to keep down on clutter
    util.drive(footCtrl, 'tiptoe', toeCtrl.getParent().rx, dv=0, minVal=0)
    util.drive(footCtrl, 'heelRaise', heelRaiseCtrl.getParent().rx, dv=0, maxVal=0, flipped=True)
    util.drive(footCtrl, 'toeTap', toeTapCtrl.getParent().rx, dv=0, minVal=0, flipped=True)
    util.drive(footCtrl, 'ballPivot', ballCtrl.getParent().attr('r' + MAYA_UP), dv=0)
    
    
    constraints = util.constrainAtoB( [ballJnt], [ball], mo=True )
    
    return footCtrl, constraints
    
    
class Foot(MetaControl):
    
    ik_ = 'pdil.tool.fossil.rigging.foot.buildFoot'
    
    @classmethod
    def build(cls, card):
        '''
        '''
        
        #assert len(card.joints) > 2
        
        toe = card.joints[1]
        heel = card.joints[2]
        
        previousJoint = card.joints[0].parent
        assert previousJoint.card.rigCommand in ('Leg', 'IkChain')
        
        legCard = previousJoint.card
        print('prev card', legCard, previousJoint, legCard.outputLeft.ik, legCard.outputRight.ik)
        
        side = card.findSuffix()
        
        #if not util.canMirror( card.start() ) or card.isAsymmetric():
        if not side or card.isAsymmetric():
            legControl = legCard.outputCenter.ik
            suffix = card.findSuffix()
            if suffix:
                ctrls = cls._buildSide(card, card.joints[0].real, xform(toe, q=True, ws=True, t=True), xform(heel, q=True, ws=True, t=True), legControl, False, suffix)
            else:
                ctrls = cls._buildSide(card, card.joints[0].real, xform(toe, q=True, ws=True, t=True), xform(heel, q=True, ws=True, t=True), legControl, False)

            card.outputCenter.ik = ctrls.ik
            
        else:
            toePos = xform(toe, q=True, t=True, ws=True)
            heelPos = xform(heel, q=True, t=True, ws=True)
            
            leftLegControl = legCard.outputLeft.ik
            ctrls = cls._buildSide(card, card.joints[0].real, toePos, heelPos, leftLegControl, True, 'L')
            card.outputLeft.ik = ctrls.ik


            rightLegControl = legCard.outputRight.ik
            toePos[0] *= -1
            heelPos[0] *= -1
            ctrls = cls._buildSide(card, card.joints[0].realMirror, toePos, heelPos, rightLegControl, False, 'R')
            card.outputRight.ik = ctrls.ik
        
        
        
        #pivotPoint = xform(card.joints[-1], q=True, ws=True, t=True)
        #joints = [j.real for j in card.joints[:-1]]
    
        #ikControlSpec = cls.controlOverrides(card, 'ik')
        
    
    @classmethod
    def _buildSide( cls, card, ballJoint, toePos, heelPos, legControl, isMirroredSide, side=None, buildFk=False ):
        
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
            
            kwargs = collections.defaultdict(dict)
            kwargs.update( cls.fkArgs )
            kwargs['controlSpec'].update( cls.fkControllerOptions )
            kwargs.update( sideAlteration(**fkControlSpec) )
            
            fkCtrl, fkConstraints = cls.fk( ballJoint, ballJoint, groupName=fkGroupName, **kwargs )
            
            # Ik is coming, disable fk so ik can lay cleanly on top.  Technically it shouldn't matter but sometimes it does.
            for const in fkConstraints:
                const.set(0)
        
        ikControlSpec = cls.controlOverrides(card, 'ik')
        
        kwargs = cls.readIkKwargs(card, isMirroredSide, sideAlteration)
        kwargs.update( cls.ikArgs )
        kwargs['controlSpec'].update( cls.ikControllerOptions )
        kwargs.update( sideAlteration(**ikControlSpec) )
        
        #fkCtrl, fkConstraints = rig.fkChain(ballJoint, ballJoint, translatable=True)
        print('ik args', ballJoint, toePos, heelPos, legControl, side)
        ikCtrl, ikConstraints = cls.ik( ballJoint, toePos, heelPos, legControl, side, **kwargs )
        
        switchPlug = None
        if cls.ik and cls.fk and buildFk:
            switchPlug = controllerShape.ikFkSwitch( 'FootFKSwitch', ikCtrl, ikConstraints, fkCtrl, fkConstraints )
        
        #switchPlug = controller.ikFkSwitch( ballJoint.name(), ikCtrl, ikConstraints, fkCtrl, fkConstraints )
        
        return OutputControls(fkCtrl, ikCtrl)