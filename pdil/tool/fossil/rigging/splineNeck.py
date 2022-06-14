
from collections import OrderedDict

from pymel.core import duplicate, dt, joint, group, hide, ikHandle, move, orientConstraint, parent, parentConstraint, \
    pointConstraint, PyNode, pointOnCurve, skinCluster, spaceLocator, xform

import pdil

from ..cardRigging import MetaControl, Param, ParamInfo
from .._lib2 import controllerShape
from .. import node
from .._lib import space

from . import _util as util


try:
    basestring  # noqa
except Exception:
    basestring = str


def findClosest(obj, targets):
    '''
    Given an object or position, finds which of the given targets it is closest to.
    '''
    if isinstance(obj, (PyNode, basestring)):
        pos = xform(obj, q=True, ws=True, t=True)
    else:
        pos = obj
    
    dists = [((dt.Vector(xform(t, q=1, ws=1, t=1)) - pos).length(), t) for t in targets]
    dists.sort()
    return dists[0][1]


@util.adds('stretch')
@util.defaultspec( {'shape': 'box',    'color': 'blue 0.22', 'size': 10},
            middle={'shape': 'sphere', 'color': 'blue 0.22', 'size': 10},
             start={'shape': 'box',    'color': 'blue 0.22', 'size': 10},)
def buildSplineNeck(start, end, name='', matchEndOrient=False, endOrient=util.EndOrient.TRUE_ZERO, curve=None, duplicateCurve=True, groupName='', controlSpec={} ):
    '''
    Makes a spline with a middle control point constrained between the endpoints.
    
    ..  todo::
        * Might want to make the end the main control to treat it more consistently
            with other IK, where the main is the end of the chain.
    '''
    if not name:
        name = pdil.simpleName(start)
        
    container = group(em=True, p=node.mainGroup(), n=name + "_controls")
    container.inheritsTransform.set(False)
    container.inheritsTransform.lock()
    
    controlChain = util.dupChain(start, end)
    controlChain[0].setParent(container)
    
    # If the chain is mirrored, we need to reorient to point down x so the
    # spline doesn't mess up when the main control rotates
    if controlChain[1].tx.get() < 0:
        # Despite aggresive zeroing of the source, the dup can still end up slightly
        # off zero so force it.
        for jnt in controlChain:
            jnt.r.set(0, 0, 0)
        joint( controlChain[0], e=True, oj='xyz', secondaryAxisOrient='yup', zso=True, ch=1)
        joint(controlChain[-1], e=True, oj='none')
    
    # Since the spline might shift the joints, make joints at the original pos
    # to constrain to.  This lets us make controls agnostically since we don't.
    # need to maintain offset
    offsetChain = util.dupChain(start, end, '{0}_offset')

    if curve:
        if duplicateCurve:
            crv = duplicate(curve)[0]
        else:
            crv = curve
        mainIk, _effector = ikHandle( sol='ikSplineSolver',
            sj=controlChain[0],  # noqa e128
            ee=controlChain[-1],
            ccv=False,
            pcv=False)
        crv.getShape().worldSpace[0] >> mainIk.inCurve

    else:
        mainIk, _effector, crv = ikHandle( sol='ikSplineSolver',
            sj=controlChain[0],  # noqa e128
            ee=controlChain[-1],
            ns=1)
        
    constraints = util.constrainAtoB( util.getChain(start, end)[:-1], offsetChain[:-1], mo=False)
    
    hide(mainIk, crv, controlChain[0])
    parent( mainIk, crv, container )
    
    startJnt = duplicate( start, po=True )[0]
    startJnt.setParent(w=True)
    endJnt = duplicate( end, po=True )[0]
    endJnt.setParent(w=True)
    
    midCtrl = controllerShape.build( name + "_Mid", controlSpec['middle'], controllerShape.ControlType.SPLINE )
    pdil.dagObj.lock(midCtrl, 's')
    midPoint = pointOnCurve( crv, pr=0.5, p=True, top=True )
    midChain = findClosest(midPoint, util.getChain(start, end))
    pdil.dagObj.matchTo(midCtrl, midChain)
    midZero = pdil.dagObj.zero(midCtrl)
    midZero.t.set( midPoint )
    
    midJoint = joint(None)
    midJoint.setParent(midCtrl)
    midJoint.t.set(0, 0, 0)
    midJoint.r.set(0, 0, 0)
    midZero.setParent( container )
    
    # Setup mid controller spaces
    pointSpace = spaceLocator()
    pointSpace.rename('midPoint_{0}'.format(start))
    pointSpace.setParent(container)
    pdil.dagObj.moveTo(pointSpace, midCtrl)
    pointConstraint( startJnt, endJnt, pointSpace, mo=True )
    hide(pointSpace)
    space.add( midCtrl, pointSpace, spaceName='midPoint')
    
    childSpace = spaceLocator()
    childSpace.rename('midChild_{0}'.format(start))
    childSpace.setParent(container)
    pdil.dagObj.matchTo(childSpace, midCtrl)
    parentConst = parentConstraint( startJnt, endJnt, childSpace, mo=True )
    parentConst.interpType.set( 2 ) # Set to `shortest`, which hopefully should always prevent flipping
    hide(childSpace)
    space.add( midCtrl, childSpace, spaceName='midChild')
    
    pntRotSpace = spaceLocator()
    pntRotSpace.rename('midPntRot_{0}'.format(start))
    pntRotSpace.setParent(container)
    pdil.dagObj.matchTo(pntRotSpace, midCtrl)
    pointConstraint( startJnt, endJnt, pntRotSpace, mo=True )
    orientConst = orientConstraint( startJnt, endJnt, pntRotSpace, mo=True )
    orientConst.interpType.set( 2 ) # Set to `shortest`, which hopefully should always prevent flipping
    hide(pntRotSpace)
    space.add( midCtrl, pntRotSpace, spaceName='midPointRot')
    
    aimer = util.midAimer(startJnt, endJnt, midCtrl)
    aimer.setParent(container)
    hide(aimer)
    space.add( midCtrl, aimer, spaceName='mid_aim')
    
    # Build Start and end controllers
    
    skinCluster(startJnt, endJnt, midJoint, crv, tsb=True)
    
    startCtrl = controllerShape.build( name + '_Start', controlSpec['start'], controllerShape.ControlType.SPLINE )
    pdil.dagObj.lock(startCtrl, 's')
    pdil.dagObj.matchTo( startCtrl, startJnt )
    startSpace = pdil.dagObj.zero(startCtrl)
    startSpace.setParent(container)
    
    endCtrl = controllerShape.build( name + '_End', controlSpec['main'], controllerShape.ControlType.SPLINE )
    util.registerRigNode(endCtrl, pointSpace, 'midPoint')
    util.registerRigNode(endCtrl, childSpace, 'midChild')
    util.registerRigNode(endCtrl, pntRotSpace, 'midPointRot')
    util.registerRigNode(endCtrl, aimer, 'mid_aim')
    pdil.dagObj.lock(endCtrl, 's')
    
    #pdil.dagObj.moveTo( endCtrl, end )
    #pdil.dagObj.zero( endCtrl ).setParent( container )
    
    """
    ORIGINAL matchEndOrient code
    if not matchEndOrient:
        pdil.dagObj.matchTo( endCtrl, endJnt )
    else:
        print( 'JUST MOVING' )
        pdil.dagObj.moveTo( endCtrl, endJnt )
    
    pdil.dagObj.zero(endCtrl).setParent(container)
    
    if matchEndOrient:
        rot = determineClosestWorldOrient(end)
        endCtrl.r.set( rot )
        storeTrueZero(endCtrl, rot)
    """
    
    # Begin new endOrient enum code (replacing matchEndOrient)
    # matchEndOrient=False == TRUE_ZERO
    # matchEndOrient=True  == JOINT
    if endOrient == util.EndOrient.WORLD:
        pdil.dagObj.moveTo( endCtrl, endJnt )
        
    elif endOrient == util.EndOrient.JOINT:
        pdil.dagObj.matchTo( endCtrl, endJnt )
        
    elif endOrient == util.EndOrient.TRUE_ZERO:
        pdil.dagObj.moveTo( endCtrl, endJnt )
    
    pdil.dagObj.zero(endCtrl).setParent(container)
    
    if endOrient == util.EndOrient.TRUE_ZERO:
        rot = util.determineClosestWorldOrient(end)
        endCtrl.r.set( rot )
        util.storeTrueZero(endCtrl, rot)
    
    # End new endOrient enum code
    
    util.makeStretchySpline( endCtrl, mainIk )
    
    # Constraint to endJnt, which has the same orientation as end instead of endCtrl
    endJnt.setParent( endCtrl )
    endConstraints = util.constrainAtoB( [end], [endJnt] )
    
    util.driveConstraints( constraints, endConstraints )
    hide( startJnt, endJnt, midJoint )
    
    space.addMain(endCtrl)
    space.add( endCtrl, start.getParent(), 'parent' )
    space.add( endCtrl, startCtrl, 'start' )
    
    space.add( startCtrl, start.getParent(), 'parent' )
    
    startJnt.setParent( startCtrl )
    
    orientConstraint( endCtrl, controlChain[-1], mo=True )
    
#    ctrls = addControlsToCurve('Blah', crv)

#    startCtrl.setParent( ctrls[0] )
#    endCtrl.setParent( ctrls[3] )
    
#    parentConstraint( ctrls[0], midCtrl, ctrls[1], mo=True )
#    parentConstraint( ctrls[3], midCtrl, ctrls[2], mo=True )
    
    #hide( ctrls[1:3] )
    
    
    # Setup matchers for easy ik switching later
    endMatch = util.createMatcher(endCtrl, end)
    endMatch.setParent(container)
    
    startMatch = util.createMatcher(startCtrl, start)
    startMatch.setParent(container)
    
    distances = {}
    jointChain = util.getChain(start, end)
        
    for j in jointChain:
        distances[ pdil.dagObj.distanceBetween(j, midCtrl) ] = j
    
    for dist, j in sorted(distances.items()):
        # Make a matcher here
        midMatch = util.createMatcher(midCtrl, j)
        midMatch.setParent(container)
        break
    
    # Setup the endControl as the leader
    
    endCtrl = pdil.nodeApi.RigController.convert(endCtrl)
    endCtrl.container = container
    endCtrl.subControl['start'] = startCtrl
    endCtrl.subControl['mid'] = midCtrl

    # Since the chain might have reversed, use the control chain for the twist axes.
    util.advancedTwist(controlChain[0], controlChain[1], startCtrl, endCtrl, mainIk)
    # Since adding the advanced twist can slightly alter things (sometimes),
    # put the offset joints in as the last step
    for ctrl, offset in zip(controlChain, offsetChain):
        offset.setParent(ctrl)
    
    return endCtrl, constraints


class SplineNeck(MetaControl):
    ''' Spline controller with a center control to provide arcing. '''
    ik_ = 'pdil.tool.fossil.rigging.splineNeck.buildSplineNeck'
    ikInput = OrderedDict( [
        ('name', Param('', 'Name', 'Name')),
        ('matchEndOrient', Param(False, 'DEP-Match Orient', 'Ik Control will match the orientation of the joint last joint')),
        ('endOrient', Param(util.EndOrient.JOINT, 'Control Orient', 'How to orient the last control')),
        ('curve', ParamInfo('NODE_0', 'Curve', 'A nurbs curve to use for spline')),
    ] )

    fkArgs = {'translatable': True}

    @classmethod
    def readIkKwargs(cls, card, isMirroredSide, sideAlteration=lambda **kwargs: kwargs, kinematicType='ik'):
        '''
        Overriden to handle if a custom curve was given, which then needs to be duplicated, mirrored and
        fed directly into the splineTwist.
        '''

        kwargs = cls.readKwargs(card, isMirroredSide, sideAlteration, kinematicType='ik')
        if isMirroredSide:
            if 'curve' in kwargs:
                crv = kwargs['curve']
                crv = duplicate(crv)[0]
                kwargs['curve'] = crv
                move( crv.sp, [0, 0, 0], a=True )
                move( crv.rp, [0, 0, 0], a=True )
                crv.sx.set(-1)
                
                kwargs['duplicateCurve'] = False
                
        return kwargs
        
    
class activator(object):
    
    @staticmethod
    def prep(endControl):
        return {
            'end': util.getMatcher(endControl),
            'mid': util.getMatcher(endControl.subControl['mid']),
            'start': util.getMatcher(endControl.subControl['start']),
        }

    
    @staticmethod
    def harvest(data):
        return {
            'end': util.worldInfo( data['end'] ),
            'mid': util.worldInfo( data['mid'] ),
            'start': util.worldInfo( data['start'] ),
        }
        
    
    @staticmethod
    def apply(data, values, endControl):
        util.applyWorldInfo( endControl.subControl['start'], values['start'] ) # Can be space of end so must come first
        util.applyWorldInfo( endControl, values['end'] )
        util.applyWorldInfo( endControl.subControl['mid'], values['mid'] )