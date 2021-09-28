from collections import OrderedDict

from pymel.core import delete, duplicate, dt, group, hide, ikHandle, orientConstraint, \
    parent, pointConstraint, poleVectorConstraint, showHidden, xform

from ....add import simpleName
from .... import core
from .... import nodeApi

from ..cardRigging import MetaControl, ParamInfo
from .. import controllerShape
from .. import space

from . import _util as util
from .. import node
from .. import rig


try:
    basestring  # noqa
except Exception:
    basestring = str

@util.adds('stretch', 'length')
@util.defaultspec( {'shape': 'box',    'size': 10, 'color': 'green 0.22' },  # noqa e231
           pv={'shape': 'sphere', 'size': 5,  'color': 'green 0.22' },
       socket={'shape': 'sphere', 'size': 5,  'color': 'green 0.22', 'visGroup': 'socket' } )
def buildIkChain(start, end, pvLen=None, stretchDefault=1, endOrientType=util.EndOrient.TRUE_ZERO, twists={}, makeBendable=False, name='', groupName='', controlSpec={}):
    '''
    
    :param int pvLen: How far from the center joint to be, defaults to half the length of the chain.
    ..  todo::
        * Have fk build as rotate only if not stretchy
    
    :param dict twists: Indicates how many twists each section has, ex {1: 2} means
        joint[1] has 2 twists, which means a 3 joint arm chain becomes
        shoulder, elbow, twist1, twist2, wrist

    '''
    
    chain = util.getChain( start, end )
    
    # Simplify the names
    controlChain = util.dupChain(start, end)
    for j, orig in zip(controlChain, chain):
        j.rename( util.trimName(orig) + '_proxy' )
    
    mainJointCount = len(chain) - sum( twists.values() )
    
    # Take the linear chain and figure out what are the "main ik", and which
    # are the twist joints.  Also parent the mainArmature as a solo chain for ik application.
    mainArmature = []
    subTwists = {}
    cur = 0
    for i in range(mainJointCount):
        mainArmature.append( controlChain[cur] )
        
        if len(mainArmature) > 1:  # Need to reparent so the 'pivot' joints are independent of the twists
        
            if mainArmature[-1].getParent() != mainArmature[-2]: # ... unless this section has no twists and is already parented.
                mainArmature[-1].setParent(mainArmature[-2])
        
        cur += 1
        if i in twists:
            subTwists[ mainArmature[-1] ] = []
            
            for ti in range(twists[i]):
                subTwists[ mainArmature[-1] ].append( controlChain[cur] )
                controlChain[cur].setParent(w=True)  # This ends up being temporary so the ik is applied properly
                cur += 1

    # actual ik node
    mainIk = ikHandle( sol='ikRPsolver', sj=mainArmature[0], ee=mainArmature[-1] )[0]
    # NOT using Spring because it acts odd.  If the pelvis turns, the poleVectors follow it.
    # Make as RP first so the ik doesn't flip around
    #PyNode('ikSpringSolver').message >> mainIk.ikSolver


    # Build the main ik control
    
    hide(mainIk)
    hide(controlChain)
    
    if not name:
        name = util.trimName(start)
    
    ctrl = controllerShape.build( name + '_Ik', controlSpec['main'], type=controllerShape.ControlType.IK )
    
    container = group( n=name + '_grp' )
    container.setParent( node.mainGroup() )
    
    core.dagObj.moveTo( ctrl, end )
    core.dagObj.zero( ctrl ).setParent( container )

    # Orient the main ik control
    if endOrientType == util.EndOrient.TRUE_ZERO:
        util.trueZeroSetup(end, ctrl)
    elif endOrientType == util.EndOrient.TRUE_ZERO_FOOT:
        util.trueZeroFloorPlane(end, ctrl)
    elif endOrientType == util.EndOrient.JOINT:
        core.dagObj.matchTo(ctrl, end)
        
        ctrl.rx.set( util.shortestAxis(ctrl.rx.get()) )
        ctrl.ry.set( util.shortestAxis(ctrl.ry.get()) )
        ctrl.rz.set( util.shortestAxis(ctrl.rz.get()) )
        
        core.dagObj.zero(ctrl)
    elif endOrientType == util.EndOrient.WORLD:
        # Do nothing, it's built world oriented
        pass
    
    core.dagObj.lockScale(ctrl)
    
    mainIk.setParent( ctrl )
    
    # I think orientTarget is for matching fk to ik
    orientTarget = duplicate( end, po=True )[0]
    orientTarget.setParent(ctrl)
    core.dagObj.lockTrans(core.dagObj.lockRot(core.dagObj.lockScale(orientTarget)))
    orientConstraint( orientTarget, mainArmature[-1] )
    hide(orientTarget)
    
    core.dagObj.lockRot(mainIk)
    core.dagObj.lockTrans(mainIk)
    core.dagObj.lockScale(mainIk)


    attr, jointLenMultiplier, nodes = util.makeStretchyNonSpline(ctrl, mainIk, stretchDefault)
    # &&& Need to do the math for all the
    
    # Make the offset joints and setup all the parenting of twists
    subArmature = []
    rotationOffsetCtrls = []
    bendCtrls = []
    for i, j in enumerate(mainArmature[:-1]):  # [:-1] Since last joint can't logically have twists
        if makeBendable:
            j.drawStyle.set(2)  # Probably should make groups but not drawing bones works for now.
        offset = duplicate(j, po=True)[0]
        offset.setParent(j)
        offset.rename( simpleName(j, '{}_Twist') )
        
        #subArmature.append(offset)  ### OLD
        if True:  ### NEW
            if not makeBendable:
                subArmature.append(offset)
            else:
                if i == 0:
                    subArmature.append(offset)
                else:
                    offsetCtrl = controllerShape.build('Bend%i' % (len(bendCtrls) + 1),
                        {'shape': 'band', 'size': 10, 'color': 'green 0.22', 'align': 'x' })
                    core.dagObj.matchTo(offsetCtrl, offset)
                    offsetCtrl.setParent(offset)
                    showHidden(offsetCtrl, a=True)
                    subArmature.append(offsetCtrl)
                    bendCtrls.append(offsetCtrl)
                
        
        rotationOffsetCtrls.append(offset)  # &&& Deprectated?
        
        attrName = simpleName(j, '{}_Twist')
        ctrl.addAttr( attrName, at='double', k=True )
        ctrl.attr(attrName) >> offset.rx
        
        if i in twists:
            for subTwist in subTwists[j]:
                subTwist.setParent(j)
                #subArmature.append(subTwist) ### NEW comment out
                
                attrName = simpleName(subTwist)
                ctrl.addAttr( attrName, at='double', k=True )
                ctrl.attr(attrName) >> subTwist.rx
                
                if not makeBendable:
                    subArmature.append(subTwist)
                else:
                    if True: ### NEW
                        offsetCtrl = controllerShape.build('Bend%i' % (len(bendCtrls) + 1),
                            {'shape': 'band', 'size': 10, 'color': 'green 0.22', 'align': 'x' })
                        core.dagObj.matchTo(offsetCtrl, subTwist)
                        offsetCtrl.setParent(subTwist)
                        subTwist.drawStyle.set(2)  # Probably should make groups but not drawing bones works fine for now.
                        showHidden(offsetCtrl, a=True)
                        subArmature.append(offsetCtrl)
                        bendCtrls.append(offsetCtrl)
                
                #offset.rename( simpleName(j, '{0}_0ffset') )
                

    #for mainJoint, (startSegment, endSegment) in zip( mainArmature, zip( rotationOffsetCtrls, rotationOffsetCtrls[1:] + [mainArmature[-1]] )):
    #    if mainJoint in subTwists:
    #        twistSetup(subTwists[mainJoint], startSegment, endSegment)
    
    # Since we don't want twists affecting eachother, base them off the mainArmature
    if False:  ### SKipping this new stuff and resurrecting the old twists
        for startSegment, endSegment in zip( mainArmature, mainArmature[1:] ):
            #print( 'HAS SUB TWISTS', startSegment in subTwists )
            if startSegment in subTwists:
                twistSetup(ctrl, subTwists[startSegment], startSegment, endSegment, jointLenMultiplier)
            
            
    '''
    # Build the groups to hold the twist controls
    groups = []
    for i, (j, nextJ) in enumerate(zip(mainArmature[:-1], mainArmature[1:])):
        g = group(em=True)
        parentConstraint(j, g)
        g.rename( core.dagObj.simpleName(g, '{0}_grp') )
        groups.append(g)

        g.setParent(container)
        
        if j in subTwists:
            
            #totalDist = core.dagObj.distanceBetween(j, nextJ)
            
            for subTwist in subTwists[j]:
                
                dist = core.dagObj.distanceBetween(j, subTwist)
                
                #disc = 'disc'()
                disc = controllerShape.build('Twist', {'shape': 'disc', 'align': 'x', 'size': 3})
                disc.setParent(g)
                disc.t.set( 0, 0, 0 )
                disc.r.set( 0, 0, 0 )
                
                core.dagObj.lockAll(disc)
                disc.rx.unlock()
                disc.tx.unlock()
                
                # Manage the lengths of the twist joints and their controls
                mult = core.math.multiply( dist, jointLenMultiplier)
                mult >> disc.tx
                mult >> subTwist.tx
                
                disc.rx >> subTwist.rx
    '''

    constraints = util.constrainAtoB( chain, subArmature + [mainArmature[-1]] )
    
        
    # PoleVector
    if not pvLen or pvLen < 0:
        pvLen = util.chainLength(mainArmature) * 0.5
    out = util.calcOutVector(mainArmature[0], mainArmature[1], mainArmature[-1])
    pvPos = out * pvLen + dt.Vector(xform(mainArmature[1], q=True, ws=True, t=True))
    pvCtrl = controllerShape.build( name + '_pv', controlSpec['pv'], type=controllerShape.ControlType.POLEVECTOR )
    
    core.dagObj.lockScale(core.dagObj.lockRot(pvCtrl))
    xform(pvCtrl, ws=True, t=pvPos)
    controllerShape.connectingLine(pvCtrl, mainArmature[1] )
    poleVectorConstraint( pvCtrl, mainIk )
    core.dagObj.zero(pvCtrl).setParent(container)
    
    # Socket offset control
    socketOffset = controllerShape.build( name + '_socket', controlSpec['socket'], type=controllerShape.ControlType.TRANSLATE )
    socketContainer = util.parentGroup( start )
    socketContainer.setParent( container )
    
    core.dagObj.moveTo( socketOffset, start )
    core.dagObj.zero( socketOffset ).setParent( socketContainer )
    core.dagObj.lockRot( socketOffset )
    core.dagObj.lockScale( socketOffset )
    pointConstraint( socketOffset, mainArmature[0] )
    
    # Reuse the socketOffset container for the controlling chain
    mainArmature[0].setParent( socketContainer )
#    hide( mainArmature[0] )
    
    ''' Currently unable to get this to update, maybe order of operations needs to be enforced?
    # Add switch to reverse the direction of the bend
    reverseAngle = controlChain[1].jointOrient.get()[1] * -1.1
    ctrl.addAttr( 'reverse', at='short', min=0, max=1, dv=0, k=True )
    preferredAngle = core.math.condition( ctrl.reverse, '=', 0, 0, reverseAngle )
    twist = core.math.condition( ctrl.reverse, '=', 0, 0, -180)
    preferredAngle >> controlChain[1].preferredAngleY
    twist >> mainIk.twist
    core.math.condition( mainIk.twist, '!=', 0, 0, 1 ) >> mainIk.twistType # Force updating??
    '''
    
    if True: # &&& LOCKABLE
        endToMidDist, g1 = core.dagObj.measure(ctrl, pvCtrl, 'end_to_mid')
        startToMidDist, g2 = core.dagObj.measure(socketOffset, pvCtrl, 'start_to_mid')
        parent(endToMidDist, g1, startToMidDist, g2, container)
        
        #ctrl.addAttr( 'lockPV', at='double', min=0.0, dv=0.0, max=1.0, k=True )
        
        #switcher.input[0].set(1)
        
        #print('--'* 20)
        #print(mainArmature)

        for jnt, dist in zip(mainArmature[1:], [startToMidDist, endToMidDist]):
            axis = util.identifyAxis(jnt)
            lockSwitch = jnt.attr('t' + axis).listConnections(s=True, d=False)[0]
            if jnt.attr('t' + axis).get() < 0:
                core.math.multiply( dist.distance, -1) >> lockSwitch.input[1]
            else:
                dist.distance >> lockSwitch.input[1]
            
            util.drive(ctrl, 'lockPV', lockSwitch.attributesBlender, 0, 1)
            
        """
        axis = identifyAxis(mainArmature[-1])
        lockSwitchA = mainArmature[-1].attr('t' + axis).listConnections(s=True, d=False)[0]
        if mainArmature[-1].attr('t' + axis).get() < 0:
            core.math.multiply( endToMidDist.distance, -1) >> lockSwitchA.input[1]
        else:
            endToMidDist.distance, -1 >> lockSwitchA.input[1]
        
        lockSwitchB = mainArmature[-2].attr('t' + axis).listConnections(s=True, d=False)[0]
        startToMidDist.distance >> lockSwitchB.input[1]
        #print(lockSwitchA, lockSwitchB, '-'* 20)
        drive(ctrl, 'lockPV', lockSwitchA.attributesBlender, 0, 1)
        drive(ctrl, 'lockPV', lockSwitchB.attributesBlender, 0, 1)
        """
    
    # Register all the parts of the control for easy identification at other times.
    ctrl = nodeApi.RigController.convert(ctrl)
    ctrl.container = container
    
    ctrl.subControl['socket'] = socketOffset
    for i, bend in enumerate(bendCtrls):
        ctrl.subControl['bend%i' % i] = bend
    ctrl.subControl['pv'] = pvCtrl
    # Add default spaces
    space.addMain( pvCtrl )
    #space.add( pvCtrl, ctrl, spaceName=shortName(ctrl, '{0}_posOnly') )
    #space.add( pvCtrl, ctrl, spaceName=shortName(ctrl, '{0}_posOnly'), mode=space.TRANSLATE)
    space.add( pvCtrl, ctrl )
    space.add( pvCtrl, ctrl, mode=space.Mode.TRANSLATE)
    
    return ctrl, constraints
    
    
class IkChain(MetaControl):
    ''' Basic 3 joint ik chain. '''
    #ik_ = 'pdil.tool.fossil.rig.ikChain2'
    ik_ = __name__ + '.' + buildIkChain.__name__
    
    ikInput = OrderedDict( [
        ('name', ParamInfo( 'Name', 'Name', ParamInfo.STR, '')),
        ('pvLen', ParamInfo('PV Length', 'How far the pole vector should be from the chain', ParamInfo.FLOAT, default=0) ),
        ('stretchDefault', ParamInfo('Stretch Default', 'Default value for stretch (set when you `zero`)', ParamInfo.FLOAT, default=1, min=0, max=1)),
        ('endOrientType', ParamInfo('Control Orient', 'How to orient the last control', ParamInfo.ENUM, enum=util.EndOrient.asChoices(), default=util.EndOrient.TRUE_ZERO)),
        ('makeBendable', ParamInfo('Make Bendy', 'Adds fine detail controls to adjust each joint individually', ParamInfo.BOOL, default=False) ),
    ] )
    
    ikArgs = {}
    fkArgs = {'translatable': True}
    
    @classmethod
    def readIkKwargs(cls, card, isMirroredSide, sideAlteration):
        kwargs = super(IkChain, cls).readIkKwargs(card, isMirroredSide, sideAlteration)
        '''
        try:
            kwargs['twists'] = json.loads( kwargs['twists'] )
        except Exception:
            kwargs['twists'] = {}
        
        print( 'Parsed into ' + str(type(kwargs['twists'])) + ' ' + str(kwargs['twists']) )
        '''
        
        # Determine the twist joints
        twists = {}

        primaryIndex = -1
        dividerCount = 0
        for j in card.joints:
            if j.info.get('twist'):
                dividerCount += 1
            else:
                if dividerCount:
                    twists[primaryIndex] = dividerCount
                  
                primaryIndex += 1
                dividerCount = 0
        
        kwargs['twists'] = twists
                
        return kwargs
        

class activator(object):
    
    @staticmethod
    def prep(ikControl):
        ik = ikControl.listRelatives(type='ikHandle')
        assert ik, "Could not determine ik handle for {0}".format( ikControl )
        ik = ik[0]
        try:
            ikEndJoint = ik.endEffector.listConnections()[0].tx.listConnections()[0]
        except Exception:
            raise Exception( 'End joint of ikHandle {0} could not be determined, unable to active_ikChain()'.format(ik) )
            
        # Figure out what is constrained to the ik and match to it
        endJnt = core.constraints.getOrientConstrainee( ikEndJoint )

        
        midJnt = endJnt.getParent()
        while rig.getBPJoint(midJnt).info.get('twist'):
            midJnt = midJnt.getParent()
        
        startJnt = midJnt.getParent()
        while rig.getBPJoint(startJnt).info.get('twist'):
            startJnt = startJnt.getParent()

        
        return {
            'base': startJnt,
            'mid': midJnt,
            'end': endJnt,
            'ikEndJoint': ikEndJoint,
        }
        
    @staticmethod
    def harvest(data):
        return {
            'base': util.worldInfo( data['base'] ),
            'mid': util.worldInfo( data['mid'] ),
            'end': util.worldInfo( data['end'] ),
            'armLength': util.chainLength( [data['base'], data['mid'], data['end']] ),
        }
        
    @staticmethod
    def apply(data, values, ikControl):

        #_matchIkToChain( ikControl, ikEndJoint, ikControl.subControl['pv'], ikControl.subControl['socket'], endJnt)
        #_matchIkToChain(ikCtrl, ikJnt, pv, socket, chainEndTarget)
        
        # Draw a line from the start to end using the lengths to calc the elbow's projected midpoint
        startPos = dt.Vector(values['base'][0])
        midPos = dt.Vector(values['mid'][0])
        endPos = dt.Vector(values['end'][0])
        
        toEndDir = endPos - startPos
        a = ( midPos - startPos ).length()
        b = ( endPos - midPos ).length()
        midPoint = startPos + (toEndDir * (a / (a + b)))
        
        # The pv direction is from the above projected midpoint to the elbow
        pvDir = midPos - midPoint
        pvDir.normalize()
        
        armLength = values['armLength']
        newPvPos = midPos + pvDir * armLength
        
        xform( ikControl.subControl['socket'], ws=True, t=startPos )
        xform( ikControl, ws=True, t=endPos )
        #xform( ikControl.subControl['pv'], ws=True, t=newPvPos )

        # Not sure how to do the math but this works to properly align the ik
        tempAligner = group(em=True)
        tempAligner.t.set( endPos )
        tempAligner.r.set( xform(ikControl, q=True, ws=True, ro=True) )
        tempAligner.setParent( data['ikEndJoint'] )
        tempAligner.r.lock()
        tempAligner.setParent( data['end'] )
        
        xform( ikControl, ws=True, ro=core.dagObj.getRot(tempAligner) )
        delete( tempAligner )

        # In case the PV is spaced to the controller, put it back
        xform( ikControl.subControl['pv'], ws=True, t=newPvPos )