from __future__ import absolute_import, division, print_function

from collections import OrderedDict

from pymel.core import delete, dt, group, hide, orientConstraint, parentConstraint, poleVectorConstraint, pointConstraint, PyNode, xform

import pdil

from ..cardRigging import MetaControl, Param
from .. import node
from .._lib import space
from .._lib2 import controllerShape

from . import _util as util
from . import dogFrontLeg


@util.adds('stretch', 'bend', 'length')
@util.defaultspec( {'shape': 'box',    'size': 10, 'color': 'green 0.22' },
              bend={'shape': 'disc', 'size': 5,  'color': 'green 0.22' },
                pv={'shape': 'sphere', 'size': 5,  'color': 'green 0.22' },
            socket={'shape': 'sphere', 'size': 5,  'color': 'green 0.22', 'visGroup': 'socket' } )
def buildDogleg(hipJoint, end, pvLen=None, name='Dogleg', endOrientType=util.EndOrient.TRUE_ZERO_FOOT, groupName='', controlSpec={}):
    '''
    ..  todo::
        * Specify toe joint instead to remove ambiguity in case of twist joints.
        * For some reason, sometimes, twist must be introduced because some flippin
            occurs.  For some reason the poleVector doesn't come in straight on.
            * Need to determine if a 180 twist is needed as the minotaur did.
        * Need to figure out the best way to constrain the last joint to the controller
    '''

    boundChain = util.getChain(hipJoint, end)

    container = group(n=name + '_dogHindleg', em=True, p=node.mainGroup())
    
    # &&& I think I want to turn this into the container for all extra stuff related to a given control
    chainGrp = group( p=container, n=name + "_ikChain", em=True )
    parentConstraint( hipJoint.getParent(), chainGrp, mo=True )
    
    # Make the control to translate/offset the limb's socket.
    socketOffset = controllerShape.build( name + '_socket', controlSpec['socket'], type=controllerShape.ControlType.TRANSLATE )
    pdil.dagObj.lock(socketOffset, 'r s')
    pdil.dagObj.moveTo( socketOffset, hipJoint )
    socketZero = pdil.dagObj.zero(socketOffset)
    socketZero.setParent( chainGrp )
    
    footCtrl = controllerShape.build( name, controlSpec['main'], type=controllerShape.ControlType.IK)
    pdil.dagObj.lock(footCtrl, 's')
    footCtrl.addAttr( 'bend', at='double', k=True )
    pdil.dagObj.moveTo( footCtrl, end )
    
    if endOrientType == util.EndOrient.TRUE_ZERO:
        util.trueZeroSetup(end, footCtrl)
    elif endOrientType == util.EndOrient.TRUE_ZERO_FOOT:
        util.trueZeroFloorPlane(end, footCtrl)
    elif endOrientType == util.EndOrient.JOINT:
        pdil.dagObj.matchTo(footCtrl, end)
        
        footCtrl.rx.set( util.shortestAxis(footCtrl.rx.get()) )
        footCtrl.ry.set( util.shortestAxis(footCtrl.ry.get()) )
        footCtrl.rz.set( util.shortestAxis(footCtrl.rz.get()) )
        
        pdil.dagObj.zero(footCtrl)
    elif endOrientType == util.EndOrient.WORLD:
        # Do nothing, it's built world oriented
        pass
    
    util.createMatcher(footCtrl, end).setParent(container)

    # Make the main ik chain which gives overall compression
    masterChain = util.dupChain(hipJoint, end)
    masterChain[0].rename( pdil.simpleName(hipJoint, '{0}_OverallCompression') )
    
    mainIk = util.ikRP('mainIk', masterChain[0], masterChain[-1])
    PyNode('ikSpringSolver').message >> mainIk.ikSolver
    '''
    mainIk = ikHandle( sol='ikRPsolver', sj=masterChain[0], ee=masterChain[-1] )[0]
    PyNode('ikSpringSolver').message >> mainIk.ikSolver
    
    mainIk.rename('mainIk')
    hide(mainIk)
    '''
    
    springFixup = group(em=True, n='SprinkIkFix')
    springFixup.inheritsTransform.set(False)
    springFixup.inheritsTransform.lock()
    springFixup.setParent( socketOffset )
    pointConstraint( socketOffset, springFixup )
    masterChain[0].setParent( springFixup )
    
    #pointConstraint( socketOffset, hipJoint )
    
    # Create the polevector.  This needs to happen first so things don't flip out later
    out = util.calcOutVector(masterChain[0], masterChain[1], masterChain[-1])
    if not pvLen or pvLen < 0:
        pvLen = util.chainLength(masterChain[1:]) * 0.5
    pvPos = out * pvLen + dt.Vector(xform(boundChain[1], q=True, ws=True, t=True))
    
    pvCtrl = controllerShape.build( name + '_pv', controlSpec['pv'], type=controllerShape.ControlType.POLEVECTOR )
    pdil.dagObj.lock(pvCtrl, 'r s')
    xform(pvCtrl, ws=True, t=pvPos)
    poleVectorConstraint( pvCtrl, mainIk )
    
    # Verify the knees are in the same place
    delta = boundChain[1].getTranslation('world') - masterChain[1].getTranslation('world')
    if delta.length() > 0.1:
        mainIk.twist.set(180)
    
    # Make sub IKs so the chain can be offset
    offsetChain = util.dupChain(hipJoint, end, '{0}_offset')
    hide(offsetChain[0])
    #offsetChain[0].rename( 'OffsetChain' )
    offsetChain[0].setParent(container)
    controllerShape.connectingLine(pvCtrl, offsetChain[1] )
    constraints = util.constrainAtoB( util.getChain(hipJoint, end), offsetChain, mo=False )
    
    pointConstraint( masterChain[0], offsetChain[0] )
    
    ankleIk = util.ikRP( 'hipToAnkle', offsetChain[0], offsetChain[-2] )
    offsetIk = util.ikRP( 'metatarsusIk', offsetChain[-2], offsetChain[-1] )
    
    #ankleIk = ikHandle( sol='ikRPsolver', sj=offsetChain[0], ee=offsetChain[-2])[0]
    #offsetIk = ikHandle( sol='ikRPsolver', sj=offsetChain[-2], ee=offsetChain[-1])[0]
    #offsetIk.rename('metatarsusIk')

    bend = controllerShape.build( name + '_bend', controlSpec['bend'], type=controllerShape.ControlType.ROTATE )
    pdil.dagObj.matchTo(bend, masterChain[-1] )
    
    if end.tx.get() < 0:
        pdil.anim.orientJoint(bend, boundChain[-2], upTarget=boundChain[-3], aim='-y', up='-x')
    else:
        pdil.anim.orientJoint(bend, boundChain[-2], upTarget=boundChain[-3], aim='y', up='x')
    
    bendZero = pdil.dagObj.zero(bend)
    bendZero.setParent(footCtrl)
    pdil.dagObj.lock(bend, 't s')
    orientConstraint( masterChain[-1], bendZero, mo=True)

##    offsetControl = group(em=True, n='OffsetBend')
##    offsetContainer = group(offsetControl, n='OffsetSpace')
##    offsetContainer.setParent(footCtrl)
        
    # Setup the offsetContainer so it is properly aligned to bend on z
##    offsetContainer.setParent( masterChain[-1] )
##    offsetContainer.t.set(0, 0, 0)
    #temp = aimConstraint( pvCtrl, offsetContainer, aim=[1, 0, 0], wut='object', wuo=hipJoint, u=[0, 1, 0])
    #delete( temp )
    
    '''
    NEED TO CHANGE THE ORIENTATION
    
    Must perfectly align with ankle segment so the offset ikhandle can translate
    according to how much things are scaled
    
    '''
##    lib.anim.orientJoint(offsetContainer, boundChain[-2], upTarget=boundChain[-3], aim='y', up='x')
    #mimic old way lib.anim.orientJoint(offsetContainer, pvCtrl, upTarget=hipJoint, aim='x', up='y')
    #lib.anim.orientJoint(offsetContainer, pvCtrl, upTarget=hipJoint, aim='x', up='y')
    
    
##    offsetControl.t.set(0, 0, 0)
##    offsetControl.t.lock()
##    offsetControl.r.set(0, 0, 0)
##    footCtrl.bend >> offsetControl.rz
    
    '''
    This is really dumb.
    Sometimes maya will rotate everything by 180 but I'm not sure how to
    calculate the proper offset, which normally results in one axis being off
    by 360, so account for that too.
    '''
    temp = orientConstraint( footCtrl, offsetChain[-1], mo=True)
    
    if not pdil.math.isClose( offsetChain[-1].r.get(), [0, 0, 0] ):

        badVals = offsetChain[-1].r.get()
        delete(temp)
        offsetChain[-1].r.set( -badVals )
        temp = orientConstraint( footCtrl, offsetChain[-1], mo=True)

        for a in 'xyz':
            val = offsetChain[-1].attr('r' + a).get()
            if abs(val - 360) < 0.00001:
                attr = temp.attr( 'offset' + a.upper() )
                attr.set( attr.get() - 360 )
                
            elif abs(val + 360) < 0.00001:
                attr = temp.attr( 'offset' + a.upper() )
                attr.set( attr.get() + 360 )
    # Hopefully the end of dumbness


    
    ankleIk.setParent( bend )
    
    # Adjust the offset ikHandle according to how long the final bone is.


    masterChain[-1].tx >> ankleIk.ty
#    if masterChain[-1].tx.get() > 0:
#        masterChain[-1].tx >> ankleIk.ty
#    else:
#        pdil.math.multiply(masterChain[-1].tx, -1.0) >> ankleIk.ty
    
    ankleIk.tx.lock()
    ankleIk.tz.lock()
    
    #ankleIk.t.lock()
    
    
    
    
    
    mainIk.setParent( footCtrl )
    offsetIk.setParent( footCtrl )
    
    pdil.dagObj.zero(footCtrl).setParent( container )
    
    hide(masterChain[0] )
    poleVectorConstraint( pvCtrl, ankleIk )
    poleVectorConstraint( pvCtrl, offsetIk )
    
    # Adding the pv constraint might require a counter rotation of the offsetIk
    counterTwist = offsetChain[-2].rx.get() * (1.0 if offsetChain[-2].tx.get() < 0 else -1.0)
    offsetIk.twist.set( counterTwist )
    
    pdil.dagObj.zero(pvCtrl).setParent( container )
    
    # Make stretchy ik, but the secondary chain needs the stretch hooked up too.
    util.makeStretchyNonSpline(footCtrl, mainIk)
        
    for src, dest in zip( masterChain[1:], offsetChain[1:] ):
        src.tx >> dest.tx
    
    footCtrl = pdil.nodeApi.RigController.convert(footCtrl)
    footCtrl.container = container
    footCtrl.subControl['socket'] = socketOffset
    footCtrl.subControl['pv'] = pvCtrl
    footCtrl.subControl['bend'] = bend
    
    # Add default spaces
    space.addMain( pvCtrl )
    space.add( pvCtrl, footCtrl )
    space.add( pvCtrl, footCtrl, mode=space.Mode.TRANSLATE)
    if hipJoint.getParent():
        space.add( pvCtrl, hipJoint.getParent())
    
        space.addMain( footCtrl )
        space.add( footCtrl, hipJoint.getParent() )
    
    return footCtrl, constraints


class DogHindleg(MetaControl):
    ''' 4 joint dog hindleg. '''
    ik_ = 'pdil.tool.fossil.rigging.dogHindLeg.buildDogleg'

    fkArgs = {'translatable': True}

    ikInput = OrderedDict( [
        ('name', Param('Leg', 'Name', 'Name')),
        ('pvLen', Param(0.0, 'PV Length', 'How far the pole vector should be from the chain') ),
        ('endOrientType', Param(util.EndOrient.TRUE_ZERO_FOOT, 'Control Orient', 'How to orient the last control')),
    ] )
                    
                    
class activator(dogFrontLeg.activator):

    # Getting the IK handle is the only difference, everything else is the same

    @staticmethod
    def getIkHandle(ctrl):
        for ik in ctrl.listRelatives(type='ikHandle'):
            if not ik.name().count( 'mainIk' ):
                return ik
        else:
            raise Exception('Unable to determine IK handle on {0} to match'.format(ctrl))
