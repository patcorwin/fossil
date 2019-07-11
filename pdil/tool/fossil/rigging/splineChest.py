from __future__ import absolute_import, division, print_function

from collections import OrderedDict

from pymel.core import duplicate, group, hide, joint, ikHandle, makeIdentity, move, orientConstraint, parent, parentConstraint, skinCluster, xform

from .... import core
from .... import lib
from .... import nodeApi

from .. import controllerShape
from .. import space

from ..cardRigging import MetaControl, ParamInfo

from . import _util as util


@util.adds('stretch')
@util.defaultspec( {'shape': 'box',    'color': 'orange 0.22', 'size': 10 },
            middle={'shape': 'sphere', 'color': 'green  0.22', 'size': 7  },
            offset={'shape': 'sphere', 'color': 'orange  0.22', 'size': 3 },
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
        midPoint = chain[1]
    else:
        raise Exception('Need to implement even number of stomach joints')
        
    container = group(em=True, p=lib.getNodes.mainGroup(), n=name + "_controls")
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
    core.dagObj.moveTo(base, chain[0])
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
    core.dagObj.lockScale(chestCtrl)
    space.add( chestCtrl, start.getParent(), 'local' )
    space.add( chestCtrl, start.getParent(), 'local_posOnly', mode=space.Mode.TRANSLATE )
    space.addWorld( chestCtrl )  # Not sure this space is useful...
    space.addTrueWorld( chestCtrl )
    space.add( chestCtrl, start.getParent(), 'worldRotate', mode=space.Mode.ALT_ROTATE, rotateTarget=space.getMainGroup())


    # Put pivot point at the bottom
    chestCtrl.ty.set( chestCtrl.boundingBox()[1][1] )
    
    lib.sharedShape.remove(chestCtrl)
    chestCtrl.setPivots( [0, 0, 0], worldSpace=True )
    makeIdentity( chestCtrl, a=True, t=True )
    lib.sharedShape.use(chestCtrl)
    
    move( chestCtrl, xform(chestBase, q=True, ws=True, t=True), rpr=True )
    chestZero = core.dagObj.zero(chestCtrl)
    
    if useTrueZero:
        rot = util.determineClosestWorldOrient(chestBase)
        
        util.storeTrueZero(chestCtrl, rot)
        core.dagObj.rezero( chestCtrl )  # Not sure why this is needed but otherwise the translate isn't zeroed
        chestCtrl.r.set( rot )
    
    chest = joint(None, n='Chest')
    chest.setParent( chestCtrl )
    core.dagObj.moveTo(chest, chestBase)
    core.dagObj.lockScale(core.dagObj.lockRot(core.dagObj.lockTrans(chest)))
    hide(chest)

    chestMatcher = util.createMatcher(chestCtrl, srcChain[chestIndex])
    chestMatcher.setParent(container)
    
    
    # -- Chest Offset -- &&& Currently hard coded to make a single offset joint
    chestOffsetCtrl = None
    if chestIndex < (len(chain) - 1):
        chestOffsetCtrl = controllerShape.build( name + '_main', controlSpec['offset'], controllerShape.ControlType.SPLINE )
        chestOffsetCtrl.setParent(chestCtrl)
        core.dagObj.matchTo( chestOffsetCtrl, chain[-1])
        move(chestOffsetCtrl, [0, 0.7, 3], r=True)
        core.dagObj.zero(chestOffsetCtrl)
        core.dagObj.lockScale(chestOffsetCtrl)
        parentConstraint(chestOffsetCtrl, chain[-1], mo=True)
    
    # -- Mid --
    midCtrl = controllerShape.build( name + '_mid', controlSpec['middle'], controllerShape.ControlType.SPLINE )
    core.dagObj.matchTo( midCtrl, midPoint )
    core.dagObj.lockScale(midCtrl)
    midCtrl.setParent( container )
    
    mid = joint(None, n='Mid')
    core.dagObj.moveTo( mid, midPoint )
    mid.setParent( midCtrl )
    core.dagObj.lockScale(core.dagObj.lockRot(core.dagObj.lockTrans(mid)))
    hide(mid)
    
    # Mid control's rotation aims at the chest
    core.dagObj.zero(midCtrl)
    
    aimer = util.midAimer(base, chestCtrl, midCtrl)
    aimer.setParent(container)
    hide(aimer)
    
    space.add(midCtrl, aimer, spaceName='default')
    userDriven = space.addUserDriven(midCtrl, 'extreme')  # Best name I got, extreme poses!
    parentConstraint( base, chestCtrl, userDriven, mo=True, skipRotate=('x', 'y', 'z'))
    orientConstraint( base, chestCtrl, userDriven, mo=True)

    """
    # -- Shoulders --
    if numChestJoints > 2: # The shoulder control is skipped if there aren't enough joints
        shoulderCtrl = controllerShape.build( name + '_shoulders', controlSpec['end'], controllerShape.ControlType.SPLINE )
        core.dagObj.matchTo( shoulderCtrl, srcChain[-2])  # We want to use the penultimate joint orientation
        core.dagObj.moveTo( shoulderCtrl, end)
        controllerShape.scaleAllCVs( shoulderCtrl, x=0.15 )
        shoulderZero = core.dagObj.zero(shoulderCtrl)
        shoulderZero.setParent(chestCtrl)
        core.dagObj.lockScale(core.dagObj.lockTrans(shoulderCtrl))
    
        neck = joint(None, n='Neck')
        neck.setParent( shoulderCtrl )
        core.dagObj.moveTo( neck, end )
        core.dagObj.lockScale(core.dagObj.lockRot(core.dagObj.lockTrans(neck)))
        hide(neck)
    
    # -- Neck --
    neckCtrl = controllerShape.build( name + '_neck', controlSpec['neck'], controllerShape.ControlType.ROTATE )
    core.dagObj.matchTo( neckCtrl, end)
    if numChestJoints > 2: # The shoulder control is skipped if there aren't enough joints
        core.dagObj.zero(neckCtrl).setParent( shoulderCtrl )
        core.dagObj.lockScale(core.dagObj.lockTrans(neckCtrl))
        space.add( neckCtrl, srcChain[-2], 'chest' )
        
    else:
        core.dagObj.zero(neckCtrl).setParent( chestCtrl )
        core.dagObj.lockScale(core.dagObj.lockTrans(neckCtrl))
        space.add( neckCtrl, chestCtrl, 'chest' )
        
    space.addWorld(neckCtrl)
    """
    # Constrain to spline proxy, up to the chest...
    constraints = []
    for src, dest in zip( chain, srcChain )[:chestIndex]:
        constraints.append( core.constraints.pointConst( src, dest ) )
        constraints.append( core.constraints.orientConst( src, dest ) )
    
    # ... including the chest
    src = chain[chestIndex]
    dest = srcChain[chestIndex]
    
    
    # &&& Gotta remove/figure out what is going on here, why can't I just constrain entirely the srcChain to it's dup'd chain?
    if False: # numChestJoints > 2: # The shoulder control is skipped if there aren't enough joints
        constraints.append( core.constraints.pointConst( src, dest ) )
        constraints.append( core.constraints.orientConst( src, dest ) )
    # ... not including the chest
    else:
        chestProxy = duplicate(src, po=True)[0]
        chestProxy.setParent(chestCtrl)
        constraints.append( core.constraints.pointConst( chestProxy, dest ) )
        constraints.append( core.constraints.orientConst( chestProxy, dest ) )
        hide(chestProxy)
    
    if chestOffsetCtrl:
        constraints.append( core.constraints.pointConst( chain[-1], srcChain[-1] ) )
        constraints.append( core.constraints.orientConst( chain[-1], srcChain[-1] ) )
    
     
    #constraints.append( core.constraints.pointConst( neckCtrl, srcChain[-1] ) )
    #constraints.append( core.constraints.orientConst( neckCtrl, srcChain[-1] ) )
    
    """
    if numChestJoints > 2: # The shoulder control is skipped if there aren't enough joints
        # Make a proxy since we can't constrain with maintainOffset=True if we're making fk too.
        proxy = duplicate(srcChain[-2], po=True)[0]
        proxy.setParent(neck)
        core.dagObj.lockTrans(core.dagObj.lockRot(core.dagObj.lockScale(proxy)))
        
        constraints.append( core.constraints.pointConst( proxy, srcChain[-2] ) )
        constraints.append( core.constraints.orientConst( proxy, srcChain[-2] ) )
    """
    
    hide(chain, mainIk)
    
    # Bind joints to the curve
    if False: # numChestJoints > 2: # The shoulder control is skipped if there aren't enough joints
        skinCluster( crv, base, mid, chest, neck, tsb=True )
    else:
        skinCluster( crv, base, mid, chest, tsb=True )
    
    chestCtrl = nodeApi.RigController.convert(chestCtrl)
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
    core.dagObj.lockTrans(core.dagObj.lockRot(core.dagObj.lockScale(startAxis)))
    
    endAxis = duplicate( start, po=True )[0]
    endAxis.rename( 'endAxis' )
    endAxis.setParent( chestCtrl )
    endAxis.t.set(0, 0, 0)
    core.dagObj.lockTrans(core.dagObj.lockRot(core.dagObj.lockScale(endAxis)))
    
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
    ik_ = 'pdil.tool.fossil.rigging.splineChest.buildSplineChest'
    ikInput = OrderedDict( [('name', ParamInfo( 'Name', 'Name', ParamInfo.STR, 'Chest')),
                            ('useTrueZero', ParamInfo( 'Use True Zero', 'Use True Zero', ParamInfo.BOOL, False)),
                            ('indexOfRibCage', ParamInfo( 'Rib Cage Index', 'Index of the bottom of the rib cage.', ParamInfo.INT, -1)),
                            ] )
    
    fkArgs = {'translatable': True}

