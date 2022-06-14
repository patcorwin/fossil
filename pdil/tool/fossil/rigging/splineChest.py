from __future__ import absolute_import, division, print_function

from collections import OrderedDict
import math

from pymel.core import duplicate, dt, group, hide, joint, ikHandle, listConnections, makeIdentity, move, orientConstraint, parent, parentConstraint, PyNode, skinCluster, xform

import pdil

from .._lib2 import controllerShape

from ..cardRigging import MetaControl, ParamInfo

from .. import node
from .. import rig
from .._core import find
from .._lib import space
from .._lib import visNode

from . import _util as util

@util.adds('stretch')
@util.defaultspec( {'shape': 'box',    'color': 'orange 0.22', 'size': 10 },
            middle={'shape': 'sphere', 'color': 'green  0.22', 'size': 7  },
            offset={'shape': 'pin',    'color': 'orange  0.22', 'size': 3 },
               end={'shape': 'box',    'color': 'orange 0.22', 'size': 10 }, )
def buildSplineChest(start, end, name='Chest', indexOfRibCage=-1, useTrueZero=True, groupName='', controlSpec={}):
    '''
    Makes a spline from the start to the `indexOfRibCage` joint, and
    TODO
        - the remaining joints get fk controllers (so you can make the spine and neck all one card, I guess)
    '''
    srcChain = util.getChain( start, end )
    
    chain = util.dupChain( start, end, '{0}_spline' )
    
    chestBase = chain[indexOfRibCage]
    chestIndex = chain.index(chestBase)
    
    if chestIndex % 2 == 0:
        # Due to `division`, have to cast to int
        midPos = xform(chain[int(chestIndex / 2)], q=True, ws=True, t=True)
        midRot = xform(chain[int(chestIndex / 2)], q=True, ws=True, ro=True)

    else:
        tempIndex = int( math.floor(chestIndex / 2) )
        low = chain[ tempIndex ]
        high = chain[ tempIndex + 1 ]

        midPos = dt.Vector( xform(low, q=True, ws=True, t=True) )
        midPos += dt.Vector( xform(high, q=True, ws=True, t=True) )
        midPos = dt.Vector(midPos) * .5
        '''&&&
        To be safe, find the closest axis on the second obj
        Get average z basis, forward
        then average y basis, up
        calc x, side
        recalc y, up
        This is the world matrix of the average rotation'''
        midRot = xform(low, q=True, ws=True, ro=True)
        #raise Exception('Need to implement even number of stomach joints')

        
    container = group(em=True, p=node.mainGroup(), n=name + "_controls")
    container.inheritsTransform.set(False)
    container.inheritsTransform.lock()
    chain[0].setParent(container)
    
    mainIk, _effector, crv = ikHandle( sol='ikSplineSolver',
        sj=chain[0],
        ee=chestBase,
        ns=3,
        simplifyCurve=False)
    
    crvShape = crv.getShape()
    crvShape.overrideEnabled.set(True)
    crvShape.overrideDisplayType.set(2)
    
    parent( mainIk, crv, container )
        
    # -- Base --  # I don't think there is any benefit to controlling this, but it might just be my weighting.
    base = joint(None, n='Base')
    pdil.dagObj.moveTo(base, chain[0])
    base.setParent( container )
    parentConstraint( start.getParent(), base, mo=True)
    hide(base)
        
    # -- Chest control --
    chestCtrl = controllerShape.build( name + '_main', controlSpec['main'], controllerShape.ControlType.SPLINE )
    chestCtrl.setParent(container)
    util.makeStretchySpline( chestCtrl, mainIk )
    chestCtrl.stretch.set(1)
    chestCtrl.stretch.lock()
    chestCtrl.stretch.setKeyable(False)
    pdil.dagObj.lock(chestCtrl, 's')

    # Put pivot point at the bottom
    chestCtrl.ty.set( chestCtrl.boundingBox()[1][1] )
    
    pdil.sharedShape.remove(chestCtrl, visNode.VIS_NODE_TYPE)
    chestCtrl.setPivots( [0, 0, 0], worldSpace=True )
    makeIdentity( chestCtrl, a=True, t=True )
    pdil.sharedShape.use(chestCtrl, visNode.get())
    
    move( chestCtrl, xform(chestBase, q=True, ws=True, t=True), rpr=True )
    pdil.dagObj.zero(chestCtrl)
    
    if useTrueZero:
        rot = util.determineClosestWorldOrient(chestBase)
        
        util.storeTrueZero(chestCtrl, rot)
        pdil.dagObj.rezero( chestCtrl )  # Not sure why this is needed but otherwise the translate isn't zeroed
        chestCtrl.r.set( rot )
    
    chest = joint(None, n='Chest')
    chest.setParent( chestCtrl )
    pdil.dagObj.moveTo(chest, chestBase)
    pdil.dagObj.lock(chest)
    hide(chest)

    chestMatcher = util.createMatcher(chestCtrl, srcChain[chestIndex])
    chestMatcher.setParent(container)
    
    # Chest spaces need to happen after it's done being manipulated into place
    space.add( chestCtrl, start.getParent(), 'local' )
    space.add( chestCtrl, start.getParent(), 'local_posOnly', mode=space.Mode.TRANSLATE )
    space.addMain( chestCtrl )  # Not sure this space is useful...
    space.addTrueWorld( chestCtrl )
    space.add( chestCtrl, start.getParent(), 'worldRotate', mode=space.Mode.ALT_ROTATE, rotateTarget=find.mainGroup())
    
    # -- Chest Offset -- &&& Currently hard coded to make a single offset joint
    chestOffsetCtrl = None
    if chestIndex < (len(chain) - 1):
        chestOffsetCtrl = controllerShape.build( name + '_bend', controlSpec['offset'], controllerShape.ControlType.SPLINE )
        chestOffsetCtrl.setParent(chestCtrl)
        pdil.dagObj.matchTo( chestOffsetCtrl, chain[-1])
        #move(chestOffsetCtrl, [0, 0.7, 3], r=True)
        pdil.dagObj.zero(chestOffsetCtrl)
        pdil.dagObj.lock(chestOffsetCtrl, 's')
        parentConstraint(chestOffsetCtrl, chain[-1], mo=True)
    
    # -- Mid --
    midCtrl = controllerShape.build( name + '_mid', controlSpec['middle'], controllerShape.ControlType.SPLINE )
    #pdil.dagObj.matchTo( midCtrl, midPoint )
    xform( midCtrl, ws=True, t=midPos )


    pdil.dagObj.lock(midCtrl, 's')
    midCtrl.setParent( container )
    
    mid = joint(None, n='Mid')
    #pdil.dagObj.moveTo( mid, midPoint )
    xform( mid, ws=True, t=midPos )
    mid.setParent( midCtrl )
    pdil.dagObj.lock(mid)
    hide(mid)
    
    # Mid control's rotation aims at the chest
    pdil.dagObj.zero(midCtrl)
    
    aimer = util.midAimer(base, chestCtrl, midCtrl)
    aimer.setParent(container)
    hide(aimer)
    util.registerRigNode(chestCtrl, aimer, 'midAimer')
    
    space.add(midCtrl, aimer, spaceName='default')
    userDriven = space.addUserDriven(midCtrl, 'extreme')  # Best name I got, extreme poses!
    parentConstraint( base, chestCtrl, userDriven, mo=True, skipRotate=('x', 'y', 'z'))
    orientConstraint( base, chestCtrl, userDriven, mo=True)
    util.registerRigNode(chestCtrl, userDriven, 'extreme')

    """
    # -- Shoulders --
    if numChestJoints > 2: # The shoulder control is skipped if there aren't enough joints
        shoulderCtrl = controllerShape.build( name + '_shoulders', controlSpec['end'], controllerShape.ControlType.SPLINE )
        pdil.dagObj.matchTo( shoulderCtrl, srcChain[-2])  # We want to use the penultimate joint orientation
        pdil.dagObj.moveTo( shoulderCtrl, end)
        controllerShape.scaleAllCVs( shoulderCtrl, x=0.15 )
        shoulderZero = pdil.dagObj.zero(shoulderCtrl)
        shoulderZero.setParent(chestCtrl)
        pdil.dagObj.lock(shoulderCtrl, 't s')
    
        neck = joint(None, n='Neck')
        neck.setParent( shoulderCtrl )
        pdil.dagObj.moveTo( neck, end )
        pdil.dagObj.lock(neck)
        hide(neck)
    
    # -- Neck --
    neckCtrl = controllerShape.build( name + '_neck', controlSpec['neck'], controllerShape.ControlType.ROTATE )
    pdil.dagObj.matchTo( neckCtrl, end)
    if numChestJoints > 2: # The shoulder control is skipped if there aren't enough joints
        pdil.dagObj.zero(neckCtrl).setParent( shoulderCtrl )
        pdil.dagObj.lock(neckCtrl, 's t')
        space.add( neckCtrl, srcChain[-2], 'chest' )
        
    else:
        pdil.dagObj.zero(neckCtrl).setParent( chestCtrl )
        pdil.dagObj.lock(neckCtrl, 't s')
        space.add( neckCtrl, chestCtrl, 'chest' )
        
    space.addMain(neckCtrl)
    """
    # Constrain to spline proxy, up to the chest...
    constraints = []
    for src, dest in list(zip( chain, srcChain ))[:chestIndex]:
        constraints.append( pdil.constraints.pointConst( src, dest ) )
        constraints.append( pdil.constraints.orientConst( src, dest ) )
    
    # ... including the chest
    src = chain[chestIndex]
    dest = srcChain[chestIndex]
    
    
    # &&& Gotta remove/figure out what is going on here, why can't I just constrain entirely the srcChain to it's dup'd chain?
    if False: # numChestJoints > 2: # The shoulder control is skipped if there aren't enough joints
        constraints.append( pdil.constraints.pointConst( src, dest ) )
        constraints.append( pdil.constraints.orientConst( src, dest ) )
    # ... not including the chest
    else:
        chestProxy = duplicate(src, po=True)[0]
        chestProxy.setParent(chestCtrl)
        constraints.append( pdil.constraints.pointConst( chestProxy, dest ) )
        constraints.append( pdil.constraints.orientConst( chestProxy, dest ) )
        hide(chestProxy)
    
    if chestOffsetCtrl:
        constraints.append( pdil.constraints.pointConst( chain[-1], srcChain[-1] ) )
        constraints.append( pdil.constraints.orientConst( chain[-1], srcChain[-1] ) )
    
     
    #constraints.append( pdil.constraints.pointConst( neckCtrl, srcChain[-1] ) )
    #constraints.append( pdil.constraints.orientConst( neckCtrl, srcChain[-1] ) )
    
    """
    if numChestJoints > 2: # The shoulder control is skipped if there aren't enough joints
        # Make a proxy since we can't constrain with maintainOffset=True if we're making fk too.
        proxy = duplicate(srcChain[-2], po=True)[0]
        proxy.setParent(neck)
        pdil.dagObj.lock(proxy)
        
        constraints.append( pdil.constraints.pointConst( proxy, srcChain[-2] ) )
        constraints.append( pdil.constraints.orientConst( proxy, srcChain[-2] ) )
    """
    
    hide(chain, mainIk)
    
    # Bind joints to the curve
    if False: # numChestJoints > 2: # The shoulder control is skipped if there aren't enough joints
        skinCluster( crv, base, mid, chest, neck, tsb=True )
    else:
        skinCluster( crv, base, mid, chest, tsb=True )
    
    chestCtrl = pdil.nodeApi.RigController.convert(chestCtrl)
    chestCtrl.container = container
    chestCtrl.subControl['mid'] = midCtrl
    if chestOffsetCtrl:
        chestCtrl.subControl['offset'] = chestOffsetCtrl
    #if numChestJoints > 2: # The shoulder control is skipped if there aren't enough joints
    #    chestCtrl.subControl['offset'] = shoulderCtrl
    #chestCtrl.subControl['neck'] = neckCtrl
    
    # Setup advanced twist
    startAxis = duplicate( start, po=True )[0]
    startAxis.rename( 'startAxis' )
    startAxis.setParent( base )
    pdil.dagObj.lock(startAxis)
    
    endAxis = duplicate( start, po=True )[0]
    endAxis.rename( 'endAxis' )
    endAxis.setParent( chestCtrl )
    endAxis.t.set(0, 0, 0)
    pdil.dagObj.lock(endAxis)
    
    hide(startAxis, endAxis)
    
    mainIk.dTwistControlEnable.set(1)
    mainIk.dWorldUpType.set(4)
    startAxis.worldMatrix[0] >> mainIk.dWorldUpMatrix
    endAxis.worldMatrix[0] >> mainIk.dWorldUpMatrixEnd
    
    hide(startAxis, endAxis)
    
    return chestCtrl, constraints
    '''
    # For some reason, direct binding doesn't work out, it throws cycle errors
    # but it would be good to get it working like this for consistency.
    lib.weights.set( crv,
        [   [(base.name(), 1.0)],
            [(mid.name(), 0.05), (base.name(), 0.95)],
            [(mid.name(), 1.0) ],
            [(chest.name(), 1.0) ],
            [(chest.name(), 0.55), (end.name(), 0.45)],
            [(neck.name(), 1.0)],
            [(neck.name(), 1.0)] ] )
    '''


class SplineChest(MetaControl):
    ''' Spline control for the chest mass.'''
    #ik_ = 'pdil.tool.fossil.rigging.splineChest.buildSplineChest'
    ik_ = __name__ + '.' + buildSplineChest.__name__ # Uses strings so reloading development always grabs the latest
    
    ikInput = OrderedDict( [('name', ParamInfo( 'Name', 'Name', ParamInfo.STR, 'Chest')),
                            ('useTrueZero', ParamInfo( 'Use True Zero', 'Use True Zero', ParamInfo.BOOL, False)),
                            ('indexOfRibCage', ParamInfo( 'Base of Rib Cage Index', 'Index of the bottom of the rib cage.', ParamInfo.INT, -1)),
                            ] )
    
    fkArgs = {'translatable': True}


def activate_ik(chestCtrl):
    '''
    '''
    util.alignToMatcher(chestCtrl)
    matcher = util.getMatcher(chestCtrl)
    endJoint = PyNode( parentConstraint(matcher, q=True, tl=True)[0] )
    
    endBpj = rig.getBPJoint(endJoint)
    
    if chestCtrl.isPrimarySide:
        children = [c.real for c in endBpj.proxyChildren if not c.isHelper]
    else:
        children = [c.realMirror for c in endBpj.proxyChildren if not c.isHelper]
        
    if children:
        rot = xform(children[0], q=True, ws=True, ro=True)
        pos = xform(children[0], q=True, ws=True, t=True)
    
    # ---
    
    midJnt = chestCtrl.subControl['mid'].listRelatives(type='joint')[0]
    
    skin = listConnections(midJnt, type='skinCluster')
    curveShape = skin[0].outputGeometry[0].listConnections(p=True)[0].node()
    ikHandle = curveShape.worldSpace.listConnections( type='ikHandle' )[0]
    
    chain = util.getChainFromIk(ikHandle)
    
    boundJoints = util.getConstraineeChain(chain)
    
    if len(boundJoints) % 2 == 1:
        #switch_logger.debug('Mid point ODD moved, # bound = {}'.format(len(boundJoints)))
        i = int(len(boundJoints) / 2) + 1
        xform( chestCtrl.subControl['mid'], ws=True, t=xform(boundJoints[i], q=True, ws=True, t=True) )
    else:
        i = int(len(boundJoints) / 2)
        xform( chestCtrl.subControl['mid'], ws=True, t=xform(boundJoints[i], q=True, ws=True, t=True) )
        #switch_logger.debug('Mid point EVEN moved, # bound = {}'.format(len(boundJoints)))
    
    # FK match joints beyond the chest control
            
    if children:
        print(rot, pos)
        xform(chestCtrl.subControl['offset'], ws=True, ro=rot)
        xform(chestCtrl.subControl['offset'], ws=True, t=pos)
        
    """
    
    
    
    
    # Find all children joints
    jointData = []
    
    def getChildrenPositions(jnt, jointData):
        children = listRelatives(jnt, type='joint')
        for child in children:
            bpChild = rig.getBPJoint( child )
            if bpChild.card == card:
                jointData.append( (
                    child,
                    xform(child, q=True, ws=True, ro=True),
                    xform(child, q=True, ws=True, p=True)
                ) )
                getChildrenPositions(child, jointData)
                break
    
    getChildrenPositions(endJoint, jointData)
    
    for j, rot, pos in jointData:
        pass
    """

class activator(object):
    
    @staticmethod
    def prep(chestCtrl):
        matcher = util.getMatcher(chestCtrl)
        
        endJoint = PyNode( parentConstraint(matcher, q=True, tl=True)[0] )
        
        endBpj = rig.getBPJoint(endJoint)
        card = endBpj.card
        
        if chestCtrl.isPrimarySide:
            children = [c.real for c in endBpj.proxyChildren if not c.isHelper and c.card == card]
        else:
            children = [c.realMirror for c in endBpj.proxyChildren if not c.isHelper and c.card == card]
                
        midJnt = chestCtrl.subControl['mid'].listRelatives(type='joint')[0]
        
        skin = listConnections(midJnt, type='skinCluster')
        curveShape = skin[0].outputGeometry[0].listConnections(p=True)[0].node()
        ikHandle = curveShape.worldSpace.listConnections( type='ikHandle' )[0]
        
        chain = util.getChainFromIk(ikHandle)
        
        boundJoints = util.getConstraineeChain(chain)
        
        stomachIndex = int(len(boundJoints) / 2) + 1 if len(boundJoints) % 2 == 1 else int(len(boundJoints) / 2)
        
        return {
            'matcher': matcher,
            'extraFk': children,
            'stomach': boundJoints[stomachIndex]
        }

        
    @staticmethod
    def harvest(data):
        values = {
            'matcher': util.worldInfo(data['matcher']),
            'stomach': util.worldInfo(data['stomach']),
            'extraFk': util.worldInfo(data['extraFk'][0]) if data['extraFk'] else None,
        }

        return values


    @staticmethod
    def apply(data, values, chestCtrl):
        util.applyWorldInfo(chestCtrl, values['matcher'])
        util.applyWorldInfo(chestCtrl.subControl['mid'], values['stomach'])
        
        if values['extraFk']:
            util.applyWorldInfo(chestCtrl.subControl['offset'], values['extraFk'])