'''
reload(pdil.tool.fossil.rigging.dogFrontLeg)
c = PyNode('asdf_card')
c.removeRig()
c.removeBones()
pdil.tool.fossil.card.buildBones([c])
pdil.tool.fossil.card.buildRig([c])
c.outputCenter.fk.IkSwitch.set(1)
c.outputCenter.ik.display.set(0)
pointConstraint('asdf02', 'locator5', mo=0)
pointConstraint('asdf04', 'locator4', mo=0)
'''


from __future__ import absolute_import, division, print_function

from collections import OrderedDict
import math

from pymel.core import createNode, delete, dt, expression, group, hide, ikHandle, orientConstraint, parentConstraint, poleVectorConstraint, pointConstraint, PyNode, xform

import pdil

from ..cardRigging import MetaControl, Param
from .._lib2 import controllerShape
from .. import node
from .._lib import space

from . import _util as util


@util.adds('stretch', 'length')
@util.defaultspec( {'shape': 'box',    'size': 10, 'color': 'green 0.22' },
              bend={'shape': 'disc',    'size': 10, 'color': 'green 0.22' },
                pv={'shape': 'sphere', 'size': 5,  'color': 'green 0.22' },
            socket={'shape': 'sphere', 'size': 5,  'color': 'green 0.22', 'visGroup': 'socket' } )
def buildDogFrontLeg(hipJoint, end, aim='x', upVector=dt.Vector(1, 0, 0), pvLen=None, name='Dogleg', endOrientType=util.EndOrient.TRUE_ZERO_FOOT, groupName='', controlSpec={}):
    boundChain = util.getChain(hipJoint, end)

    container = group(n=name + '_dogFrontleg', em=True, p=node.mainGroup())
    
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
    masterChain = util.dupChain(hipJoint, end, '{0}_compress')
    masterChain[-1].setParent( masterChain[-3] )
    pdil.anim.orientJoint(masterChain[-3], masterChain[-1], aim=aim, upVector=upVector)
    delete( masterChain[-2] )
    del masterChain[-2]

    refChain = util.dupChain(hipJoint, end, '{0}_ref')
    hide(refChain[0])
    refChain[0].setParent( socketOffset )
    refIk = util.ikRP('refIk', refChain[0], refChain[-1])
    refIk.setParent( footCtrl )
    pdil.dagObj.lock(refIk)

    mainIk = ikHandle( sol='ikRPsolver', sj=masterChain[0], ee=masterChain[-1] )[0]
    PyNode('ikSpringSolver').message >> mainIk.ikSolver
    
    mainIk.rename('mainIk')
    hide(mainIk)
    
    masterChain[0].setParent( socketOffset )
    
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
    offsetChain = util.dupChain(hipJoint, end)
    hide(offsetChain[0])
    offsetChain[0].rename( 'OffsetChain' )
    offsetChain[0].setParent(container)
    controllerShape.connectingLine(pvCtrl, offsetChain[1] )
    constraints = util.constrainAtoB( util.getChain(hipJoint, end), offsetChain, mo=False )
    
    pointConstraint( masterChain[0], offsetChain[0] )
    ankleIk = util.ikRP('ankle', offsetChain[0], offsetChain[-2])
    offsetIk = util.ikRP( 'metatarsusIk', offsetChain[-2], offsetChain[-1])
    
    bend = controllerShape.build( name + '_bend', controlSpec['bend'], type=controllerShape.ControlType.ROTATE )
    offsetContainer = group(em=True, n='OffsetSpace')
    offsetContainer.setParent( footCtrl )
    pdil.dagObj.moveTo(offsetContainer, end)
    
    if end.tx.get() < 0:
        pdil.anim.orientJoint(offsetContainer, boundChain[-2], upTarget=boundChain[-3], aim='-y', up='-x')
    else:
        pdil.anim.orientJoint(offsetContainer, boundChain[-2], upTarget=boundChain[-3], aim='y', up='x')

    bend.setParent(offsetContainer)
    bend.t.set(0, 0, 0)
    bend.r.set(0, 0, 0)

    pdil.dagObj.zero(bend)
    pdil.dagObj.lock( bend, 't s' )

    parentConstraint( masterChain[-1], offsetContainer, mo=True )
    
    
    ''' NOTE - This is from dog hind leg.  I need to find a repro to test.
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
    
    mainIk.setParent( footCtrl )
    offsetIk.setParent( footCtrl )
    
    pdil.dagObj.zero(footCtrl).setParent( container )
    
    hide(masterChain[0])
    poleVectorConstraint( pvCtrl, ankleIk )
    poleVectorConstraint( pvCtrl, offsetIk )
    
    # Adding the pv constraint might require a counter rotation of the offsetIk
    counterTwist = offsetChain[-2].rx.get() * (1.0 if offsetChain[-2].tx.get() < 0 else -1.0)
    offsetIk.twist.set( counterTwist )
    
    pdil.dagObj.zero(pvCtrl).setParent( container )
    
    # Make stretchy ik, but the secondary chain needs the stretch hooked up too
    strechPlug, _, nodes = util.makeStretchyNonSpline(footCtrl, refIk)

    for src, dest in zip( refChain[1:], offsetChain[1:] ):
        src.tx >> dest.tx
    
    refChain[1].tx >> masterChain[1].tx
    # Law of cosines to determine the master chain's 'forearm' bone length
    formula = '{jnt} = sqrt( pow({sideA}, 2) + pow({sideB}, 2) - 2 * {sideA} * {sideB} * cos({angle})  );'\
        .format(
            jnt=masterChain[-1].tx,
            sideA=refChain[-1].tx,
            sideB=refChain[-2].tx,
            angle=math.radians(util.angleBetween(*refChain[-3:])[0])
        )
    expression( s=formula )

    ankleIk.setParent( bend )

    # Finish setting up the bend control to be lerpable from user controlled to fully straight
    bendAnchor = group(em=True, n='bendAnchor')
    pdil.dagObj.matchTo(bendAnchor, ankleIk)
    
    bendAnchor.setParent( bend )
    refChain[3].tx >> bendAnchor.ty
    
    autoStraighten = pointConstraint( [bendAnchor, refChain[-2]], ankleIk )
    dynamicW, straightW = autoStraighten.getWeightAliasList()

    
    #? = begin straightening value
    #remap 0,0 --> ?,0 -> 1, 1
    straighten = .95
    remap = createNode('remapValue')
    remap.value[2].value_Position.set(straighten)
    remap.value[2].value_FloatValue.set(0)
    remap.value[2].value_Interp.set(1)
    
    pdil.math.divide( nodes['distToController'], nodes['computedTotalScaled'] ) >> remap.inputValue

    dynamicW.set(1)
    straightW.set(0)
    remap.outValue >> straightW
    pdil.math.opposite( remap.outValue ) >> dynamicW
    util.drive(footCtrl, 'straighten', remap.value[2].value_Position, 0, 1, dv=straighten)
    footCtrl.straighten.set(straighten)
    #-

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


class DogFrontLeg(MetaControl):
    ''' 4 joint dog front leg.

    Acts like a 3 joint ik, with the end two joints
    moving as a single bone but bendable via controller.
    '''
    
    '''
    `Seg Leg #` is -10 to 10
        -10 = Zero length
          0 = Original length
         10 = 2x original length
    Length is -10 to 10
        -10 = Half length
          0 = Original length
         10 = 2x length

    '''
    ik_ = 'pdil.tool.fossil.rigging.dogFrontLeg.buildDogFrontLeg'

    fkArgs = {'translatable': True}

    ikInput = OrderedDict( [
        ('name', Param('Leg', 'Name', 'Name')),
        ('pvLen', Param(0.0, 'PV Length', 'How far the pole vector should be from the chain') ),
        ('endOrientType', Param(util.EndOrient.TRUE_ZERO_FOOT, 'Control Orient', 'How to orient the last control')),
    ] )
    

class activator(object):

    @staticmethod
    def getIkHandle(ctrl):
        for ik in ctrl.listRelatives(type='ikHandle'):
            if ik.name().count( 'metatarsusIk' ):
                return ik
        else:
            raise Exception('Unable to determine IK handle on {0} to match'.format(ctrl))

    @classmethod
    def prep(cls, ctrl):
        ik = cls.getIkHandle(ctrl)
        
        chain = util.getChainFromIk(ik)
        
        chain.insert(0, chain[0].getParent() )
        chain.insert(0, chain[0].getParent() )

        bound = util.getConstraineeChain(chain)

        return {
            'matcher': util.getMatcher(ctrl),
            'hip': bound[0],
            'knee': bound[1],
            'ankle': bound[2],
            'ball': bound[3],
        }
        
    @staticmethod
    def harvest(objects):
        return {
            'matcher': util.worldInfo( objects['matcher']),
            'hip': util.worldInfo( objects['hip']),
            'knee': util.worldInfo( objects['knee']),
            'ankle': util.worldInfo( objects['ankle']),
            'ball': util.worldInfo( objects['ball']),
            'length': abs(sum( [b.tx.get() for b in (objects['knee'], objects['ankle'], objects['ball'])] )),
            'ankleMatrix': xform( objects['ankle'], q=True, ws=True, m=True),
        }
    

    WORLD_INFO = ['matcher', 'hip', 'knee', 'ankle', 'ball']

    @classmethod
    def split(cls, values):
        ''' Turns all the `worldInfo` into separate dictionaries. '''
        pos, rot = {}, {}
        for key in cls.WORLD_INFO:
            pos[key] = dt.Vector( values[key][0] )
            rot[key] = values[key][1]
        return pos, rot

    @classmethod
    def apply(cls, objects, values, ctrl):
        pos, rot = cls.split(values)
        out = util.calcOutVector(pos['hip'], pos['knee'], pos['ankle'])
        out *= values['length']

        pvPos = values['knee'][0] + out
        
        util.applyWorldInfo(ctrl, values['matcher'])

        xform( ctrl.subControl['pv'], ws=True, t=pvPos )
        
        # Aim Y at ball
        matrix = values['ankleMatrix']
        bendNormal = dt.Vector(matrix[4:7]) * -1.0

        ybasis = (pos['ankle'] - pos['ball']).normal()
        xbasis = ybasis.cross( bendNormal )
        zbasis = xbasis.cross( ybasis )

        if objects['ball'].tx.get() < 0:
            ybasis *= -1
            xbasis *= -1

        r = pdil.math.eulerFromMatrix( [xbasis, ybasis, zbasis], degrees=True )
        xform( ctrl.subControl['bend'], ws=True, ro=r )
