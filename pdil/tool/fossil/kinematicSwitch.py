from __future__ import print_function, absolute_import

from functools import partial
import logging
import math

from pymel.core import dt, delete, keyframe, PyNode, xform, currentTime, setKeyframe, warning, setAttr, refresh, orientConstraint, listConnections, group

from ... import core

from ...nodeApi import fossilNodes

from . import controllerShape
from . import rig


switch_logger = logging.getLogger('IK_FK_Switch')


def _getSwitchPlug(obj):  # WTF IS THIS??
    '''
    Given the object a bind joint is constrained to, return the switching plug.
    '''

    bone = core.constraints.getOrientConstrainee(obj)
    constraint = orientConstraint( bone, q=True )
    
    plugs = orientConstraint(constraint, q=True, wal=True)
    targets = orientConstraint(constraint, q=True, tl=True)
    
    for plug, target in zip(plugs, targets):
        if target == obj:
            switchPlug = plug.listConnections(s=True, d=False, p=True)
            return switchPlug


def getChainFromIk(ikHandle):
    '''
    Given an ikHandle, return a chain of the joints affected by it.
    '''
    start = ikHandle.startJoint.listConnections()[0]
    endEffector = ikHandle.endEffector.listConnections()[0]
    end = endEffector.tx.listConnections()[0]

    chain = rig.getChain(start, end)
    return chain


def getConstraineeChain(chain):
    '''
    If the given chain has another rotate constrained to it, return it
    '''
    boundJoints = []
    for j in chain:
        temp = core.constraints.getOrientConstrainee(j)
        if temp:
            boundJoints.append(temp)
        else:
            break

    return boundJoints


def angleBetween( a, mid, c ):
    # Give 3 points, return the angle and axis between the vectors
    aPos = dt.Vector(xform(a, q=True, ws=True, t=True))
    midPos = dt.Vector(xform(mid, q=True, ws=True, t=True))
    cPos = dt.Vector(xform(c, q=True, ws=True, t=True))

    aLine = midPos - aPos
    bLine = midPos - cPos

    aLine.normalize()
    bLine.normalize()

    axis = aLine.cross(bLine)

    if axis.length() > 0.01:
        return math.degrees(math.acos(aLine.dot(bLine))), axis
    else:
        return 0, axis


def ikFkRange(control, start=None, end=None):
    action = activateIk if control.fossilCtrlType.get() in ['ik'] else activateFk

    otherObj = control.getOtherMotionType()
    
    drivePlug = controllerShape.getSwitcherPlug(control)
    if drivePlug:
        driver = lambda: setAttr(drivePlug, 1)  # noqa E731
    else:
        if control.fossilCtrlType.get() in ['ik']:
            switch = _getSwitchPlug(otherObj)[0].node()
            plug = switch.input1D.listConnections(p=True)[0]
            driver = lambda: plug.set(1)  # noqa E731
        else:
            switch = _getSwitchPlug(control)[0].node()
            plug = switch.input1D.listConnections(p=True)[0]
            driver = lambda: plug.set(1)  # noqa E731

    controls = [ ctrl for name, ctrl in otherObj.subControl.items() ] + [otherObj]
    times = set()
    
    for c in controls:
        times.update( keyframe(c, q=True, tc=True) )
    
    finalRange = []
    for t in sorted(times):
        if start is not None and t < start:
            continue
        if end is not None and t > end:
            continue
            
        finalRange.append(t)
        
    targetControls = [ctrl for name, ctrl in control.subControl.items()] + [control]
    
    with core.ui.NoUpdate():
        for t in finalRange:
            currentTime(t)
            driver()
            action(control)
            refresh()
            setKeyframe(targetControls, shape=False)
            
            if drivePlug:
                setKeyframe( drivePlug )


def activateFk( fkControl ):
    ctrls = [ (int(name), ctrl) for name, ctrl in fkControl.subControl.items() ]
    ctrls = sorted(ctrls)
    ctrls = [ ctrl for name, ctrl in ctrls ]
    ctrls.insert( 0, fkControl )
        
    for ctrl in ctrls:
        target = core.constraints.getOrientConstrainee( ctrl )

        trans = xform( target, q=True, ws=True, t=True)
        rot = xform( target, q=True, ws=True, ro=True)
        
        xform( ctrl, ws=True, t=trans)
        xform( ctrl, ws=True, ro=rot)

    switchPlug = _getSwitchPlug(fkControl)
    
    if switchPlug:
        switchPlug[0].node().listConnections(p=1, s=True, d=0)[0].set(0)


def ikFkSwitch(obj, start, end):
    '''
    Ik/Fk switch
    
    Takes any controller type (ik or fk) and switches to the other.
    '''
    
    obj = PyNode(obj)
    
    if isinstance(obj, fossilNodes.RigController):
        mainCtrl = obj
    else:
        mainCtrl = obj.message.listConnections(type=fossilNodes.RigController)[0]
        
    otherCtrl = mainCtrl.getOtherMotionType()
        
    # If we are changing to fk...
    if otherCtrl.fossilCtrlType.get() in ['translate', 'rotate']:
        
        if start == end and start is not None:  # Might want ikFkRange to handle this distinction
            activateFk(otherCtrl)
        else:
            ikFkRange(otherCtrl, start, end)
    
    # If we are changing to ik
    else:
        activateIk( otherCtrl, start, end )


def multiSwitch(objs, start, end):
    for obj in objs:
        ikFkSwitch(obj, start, end)


class ActivateIkDispatch(object):
    '''
    Ik matching is complex enough to be grouped but not so large yet to merit
    its own module.
    '''

    def __call__(self, ikController, start=None, end=None, key=True):
        '''
        Manages determining the main control and appropriate type of switching.
        
        
        If start and end are None, it means all keys.  If they are the same
        values, it means a single frame.
        '''
        ikControl = rig.getMainController(ikController)
        
        # Determine what type of switching to employ.
        card = ikControl.card
        
        if card.rigCommand == 'DogHindleg':
            switchCmd = partial(self.activate_dogleg, ikControl)

        elif card.rigCommand in ['SplineChest', 'SplineChestV2']:
            switchCmd = partial(self.active_splineChest, ikControl)

        elif card.rigCommand == 'SplineNeck':
            switchCmd = partial(self.active_splineNeck, ikControl)

        else:
            switchCmd = partial(self.active_ikChain, ikControl)
        
        print( 'Switch called on', ikController, switchCmd.func )
        
        # Get the plug that controls the kinematic mode.
        switcherPlug = controllerShape.getSwitcherPlug(ikControl)
            
        # Gather the times
        if start is not None and end is not None and start == end:
            finalRange = [start]
        else:
            key = True # If we are range switching, we have to key everything.
            
            fkMain = ikControl.getOtherMotionType()
            fkControls = [ ctrl for name, ctrl in fkMain.subControl.items() ] + [fkMain]
            times = set(keyframe(switcherPlug, q=True))
    
            for c in fkControls:
                times.update( keyframe(c, q=True, tc=True) )
                
            finalRange = []
            for t in sorted(times):
                if start is not None and t < start:
                    continue
                if end is not None and t > end:
                    continue
                    
                finalRange.append(t)
            
            if finalRange:  # &&& it is possible this should be one scope up.
                # Put keys at all frames that will be switched if not already there.
                if not keyframe(switcherPlug, q=True):
                    setKeyframe(switcherPlug, t=finalRange[0])
                    
                for t in finalRange:
                    setKeyframe( switcherPlug, t=t, insert=True )
                
        # Finally, actually switch to ik.
        ikControls = [ctrl for name, ctrl in ikControl.subControl.items()] + [ikControl, switcherPlug]
                
        with core.ui.NoUpdate():
            cur = currentTime(q=True)
            
            for t in finalRange:
                currentTime(t)
                switchCmd()
                setAttr(switcherPlug, 1)
                if key:
                    setKeyframe(ikControls, shape=False)
                    
            currentTime(cur)
    
    @classmethod
    def active_splineNeck(cls, endControl):
                
        cls.alignToMatcher(endControl)
        cls.alignToMatcher( endControl.subControl['mid'] )
        cls.alignToMatcher( endControl.subControl['start'] )
        
        # Reference for if matching needs to use relevant joints
        #joints = card.getRealJoints( side=endControl.getSide() )
        #skeletonTool.util.moveTo(endControl, joints[-1])
        #skeletonTool.util.moveTo(endControl.subControl['start'], joints[-1])

    @classmethod
    def active_ikChain(cls, ikControl):
        '''
        Move the Ik control to where the bind joints are and switch to IK mode
        Work on ik arms and legs
        '''

        ik = ikControl.listRelatives(type='ikHandle')
        assert ik, "Could not determine ik handle for {0}".format( ikControl )
        ik = ik[0]
        try:
            ikEndJoint = ik.endEffector.listConnections()[0].tx.listConnections()[0]
        except Exception:
            raise Exception( 'End joint of ikHandle {0} could not be determined, unable to active_ikChain()'.format(ik) )
            
        # Figure out what is constrained to the ik and match to it
        endJnt = core.constraints.getOrientConstrainee( ikEndJoint )
            
        cls._matchIkToChain( ikControl, ikEndJoint, ikControl.subControl['pv'], ikControl.subControl['socket'], endJnt)

    @classmethod
    def active_splineChest(cls, chestCtrl):
        '''
        ..  todo::
            Implement even number of stomach joints
        '''
        cls.alignToMatcher(chestCtrl)

        midJnt = chestCtrl.subControl['mid'].listRelatives(type='joint')[0]

        skin = listConnections(midJnt, type='skinCluster')
        curveShape = skin[0].outputGeometry[0].listConnections(p=True)[0].node()
        ikHandle = curveShape.worldSpace.listConnections( type='ikHandle' )[0]

        chain = getChainFromIk(ikHandle)

        boundJoints = getConstraineeChain(chain)

        if len(boundJoints) % 2 == 1:
            switch_logger.debug('Mid point ODD moved, # bound = {}'.format(len(boundJoints)))
            i = int(len(boundJoints) / 2) + 1
            xform( chestCtrl.subControl['mid'], ws=True, t=xform(boundJoints[i], q=True, ws=True, t=True) )
        else:
            i = int(len(boundJoints) / 2)
            xform( chestCtrl.subControl['mid'], ws=True, t=xform(boundJoints[i], q=True, ws=True, t=True) )
            switch_logger.debug('Mid point EVEN moved, # bound = {}'.format(len(boundJoints)))

    @classmethod
    def activate_dogleg(cls, ctrl):

        # Get the last ik chunk but expand it to include the rest of the limb joints
        for ik in ctrl.listRelatives(type='ikHandle'):
            if not ik.name().count( 'mainIk' ):
                break
        else:
            raise Exception('Unable to determin IK handle on {0} to match'.format(ctrl))

        chain = getChainFromIk(ik)
        chain.insert( 0, chain[0].getParent() )
        chain.insert( 0, chain[0].getParent() )
        bound = getConstraineeChain(chain)
        
        # Move the main control to the end point
        #xform(ctrl, ws=True, t=xform(bound[-1], q=True, ws=True, t=True) )
        cls.alignToMatcher(ctrl)

        # Place the pole vector away
        out = rig.calcOutVector(bound[0], bound[1], bound[-2])
        length = abs(sum( [b.tx.get() for b in bound[1:]] ))
        out *= length

        pvPos = xform( bound[1], q=True, ws=True, t=True ) + out
        xform( ctrl.subControl['pv'], ws=True, t=pvPos )

        # Figure out the bend, (via trial and error at the moment)
        def setBend():
            angle, axis = angleBetween( bound[-2], bound[-1], chain[-2] )
            current = ctrl.bend.get()

            ''' This is an attempt to look at the axis to determine what direction to bend
            if abs(axis[0]) > abs(axis[1]) and abs(axis[0]) > abs(axis[2]):
                signAxis = axis[0]
            elif abs(axis[1]) > abs(axis[0]) and abs(axis[1]) > abs(axis[2]):
                signAxis = axis[1]
            elif abs(axis[2]) > abs(axis[0]) and abs(axis[2]) > abs(axis[1]):
                signAxis = axis[2]
            '''

            d = core.dagObj.distanceBetween(bound[-2], chain[-2])
            ctrl.bend.set( current + angle )
            if core.dagObj.distanceBetween(bound[-2], chain[-2]) > d:
                ctrl.bend.set( current - angle )

        setBend()

        # Try to correct for errors a few times because the initial bend might
        # prevent the foot from being placed all the way at the end.
        # Can't try forever in case the FK is off plane.
        '''
        The *right* way to do this.  Get the angle between

        cross the 2 vectors for the out vector
        cross the out vector with the original vector for the "right angle" vector
        Now dot that with the 2nd vector (and possibly get angle?) if it's less than 90 rotate one direction

        '''
        if core.dagObj.distanceBetween(bound[-2], chain[-2]) > 0.1:
            setBend()
            if core.dagObj.distanceBetween(bound[-2], chain[-2]) > 0.1:
                setBend()
                if core.dagObj.distanceBetween(bound[-2], chain[-2]) > 0.1:
                    setBend()

    @staticmethod
    def alignToMatcher(ctrl):
        try:
            matcher = ctrl.matcher.listConnections()[0]
            xform( ctrl, ws=True, t=xform(matcher, q=True, ws=True, t=True) )
            xform( ctrl, ws=True, ro=xform(matcher, q=True, ws=True, ro=True) )
        except Exception:
            warning('{0} does not have a matcher setup'.format(ctrl))

    @staticmethod
    def _matchIkToChain(ikCtrl, ikJnt, pv, socket, chainEndTarget):
        '''
        Designed for 3 joint ik.
        
        :param ikCtrl: Ik controller
        :param ikJnt: The joint the ik controller is manipulating
        :param pv: Pole vector control
        :param socket: The socket controller of the ik chain
        :param Joint chainEndTarget: The joint at the end of the chain we want to match.


        ..  todo::
            Update to use a percentage of the length of the palm to offset the polevector length, probably .5 the length of the arm
        '''

        midJnt = chainEndTarget.getParent()
        while rig.getBPJoint(midJnt).info.get('twist'):
            midJnt = midJnt.getParent()
        
        startJnt = midJnt.getParent()
        while rig.getBPJoint(startJnt).info.get('twist'):
            startJnt = startJnt.getParent()

        switch_logger.debug( 'ikCtrl={}\nikJnt={}\nmidJnt={}\nstartJnt={}\nchainEndTarget={}'.format(ikCtrl, ikJnt, midJnt, startJnt, chainEndTarget) )

        # Draw a line from the start to end using the lengths to calc the elbow's projected midpoint
        startPos = core.dagObj.getPos( startJnt )
        midPos = core.dagObj.getPos( midJnt )
        endPos = core.dagObj.getPos( chainEndTarget )
        
        toEndDir = endPos - startPos
        a = ( midPos - startPos ).length()
        b = ( endPos - midPos ).length()
        midPoint = startPos + (toEndDir * (a / (a + b)))
        
        # The pv direction is from the above projected midpoint to the elbow
        pvDir = midPos - midPoint
        pvDir.normalize()
        
        armLength = rig.chainLength([startJnt, midJnt, chainEndTarget])
        newPvPos = midPos + pvDir * armLength
        
        xform( socket, ws=True, t=startPos )
        xform( ikCtrl, ws=True, t=endPos )
        xform( pv, ws=True, t=newPvPos )

        # Not sure how to do the math but this works to properly align the ik
        tempAligner = group(em=True)
        tempAligner.t.set( core.dagObj.getPos(ikCtrl) )
        tempAligner.r.set( core.dagObj.getRot(ikCtrl) )
        tempAligner.setParent( ikJnt )
        tempAligner.r.lock()
        tempAligner.setParent( chainEndTarget )
        
        xform( ikCtrl, ws=True, ro=core.dagObj.getRot(tempAligner) )
        delete( tempAligner )
    
        # In case the PV is spaced to the controller, put it back
        xform( pv, ws=True, t=newPvPos )
        
        
activateIk = ActivateIkDispatch()