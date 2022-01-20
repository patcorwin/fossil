from __future__ import absolute_import, division, print_function

from collections import OrderedDict
from functools import partial

from pymel.core import dt, geometryConstraint, normalConstraint, pointConstraint, spaceLocator, xform

import pdil

from ..cardRigging import MetaControl, ParamInfo, OutputControls, colorParity

from .. import log
from .._lib import space
from .._lib2 import controllerShape

from . import _util as util
from .. import node


def getUpVectors(j):
    # HACK!!!!  Needs to work in surfaceFollow
    return dt.Vector(0, 0, 1), dt.Vector(0, 0, 1)


@util.adds()
@util.defaultspec( {'shape': 'box',     'size': 10, 'color': 'blue  0.22'},
            manual={'shape': 'pin',     'size':  3, 'color': 'green 0.22', 'align': 'nx'},
            offset={'shape': 'band',    'size':  5, 'color': 'green 0.22', 'align': 'nx'}
 )
def buildSurfaceFollow(joints, groupOrigin, surface=None, controlSpec={}):
    
    groupOrigin = dt.Vector(groupOrigin)
    container = util.parentGroup(joints[0])
    container.setParent( node.mainGroup() )
    
    mainCtrl = controllerShape.build(
        util.trimName(joints[0].getParent()) + 'Surface_ctrl',
        controlSpec['main'],
        type=controllerShape.ControlType.TRANSLATE )
    
    mainCtrl = pdil.nodeApi.RigController.convert(mainCtrl)
    
    mainCtrl.setParent(container)
    xform(mainCtrl, ws=True, t=groupOrigin)
    
    pdil.dagObj.lock(mainCtrl, 's')
    
    pdil.dagObj.zero(mainCtrl)
    
    subControls = []
    locs = []
    offsets = []
    for i, j in enumerate(joints):
        loc = spaceLocator()
        locs.append( loc )
        pdil.dagObj.matchTo(loc, j)
        
        geometryConstraint(surface, loc)
        
        objUp, worldObjUp = getUpVectors(j)
        
        normalConstraint(surface, loc,
            wuo=mainCtrl,
            wut='objectrotation',
            upVector=objUp,
            worldUpVector=worldObjUp)

        offsetCtrl = controllerShape.build( util.trimName(j) + 'Offset_ctrl',
                                            controlSpec['offset'],
                                            type=controllerShape.ControlType.TRANSLATE )

        pdil.dagObj.matchTo(offsetCtrl, loc)

        offsets.append( offsetCtrl )
        offsetCtrl.setParent(loc)
        pdil.dagObj.zero(offsetCtrl)

        subCtrl = controllerShape.build( util.trimName(j) + '_ctrl',
                                            controlSpec['manual'],
                                            type=controllerShape.ControlType.TRANSLATE )

        subControls.append(subCtrl)
        
        pdil.dagObj.matchTo(subCtrl, loc)
        
        subCtrl.setParent(mainCtrl)
        
        pdil.dagObj.zero(subCtrl)
        
        pointConstraint(subCtrl, loc)
        
        pdil.dagObj.lock(subCtrl, 'r s')
        pdil.dagObj.lock(offsetCtrl, 's')
        
        loc.setParent(subCtrl)
        
        space.add( offsetCtrl, loc, spaceName='surface')
        
        mainCtrl.subControl[str(i)] = subCtrl
        mainCtrl.subControl[str(i) + '_offset'] = offsetCtrl
    
    constraints = util.constrainAtoB(joints, offsets)
    
    mainCtrl.container = container
    
    return mainCtrl, constraints
    
    
class SurfaceFollow(MetaControl):
    ''' Special controller providing translating bones simulating squash and stretch. '''
    #displayInUI = False

    ik_ = 'pdil.tool.fossil.rigging.surfaceFollow.buildSurfaceFollow'
    ikInput = OrderedDict( [
        ('surface', ParamInfo('Mesh', 'The surface to follow', ParamInfo.NODE_0)),
        #('rangeMin', ParamInfo( 'Min Range', 'Lower bounds of the keyable attr.', ParamInfo.FLOAT, -5.0)),
        #('rangeMax', ParamInfo( 'Max Range', 'Upper bounds of the keyable attr.', ParamInfo.FLOAT, 5.0)),
        #('scaleMin', ParamInfo( 'Shrink Value', 'When the attr is at the lower bounds, scale it to this amount.', ParamInfo.FLOAT, .5)),
        #('scaleMax', ParamInfo( 'Expand Value', 'When the attr is at the upper bounds, scale it to this amount.', ParamInfo.FLOAT, 2)),
    ] )
    
    #orientAsParent=True, min=0.5, max=1.5
    
    @classmethod
    def build(cls, card):
        '''
        Custom build that uses all the joints, except the last, which is used
        as a virtual center/master control for all surface following joints.
        '''
        assert len(card.joints) > 2
        pivotPoint = xform(card.joints[-1], q=True, ws=True, t=True)
        joints = [j.real for j in card.joints[:-1]]
    
        ikControlSpec = cls.controlOverrides(card, 'ik')
    
        def _buildSide( joints, pivotPoint, isMirroredSide, side=None ):
            log.Rotation.check(joints, True)
            if side == 'left':
                sideAlteration = partial( colorParity, 'L' )
            elif side == 'right':
                sideAlteration = partial( colorParity, 'R' )
            else:
                sideAlteration = lambda **kwargs: kwargs  # noqa
            
            kwargs = cls.readIkKwargs(card, isMirroredSide, sideAlteration)
            kwargs.update( cls.ikArgs )
            kwargs['controlSpec'].update( cls.ikControllerOptions )
            kwargs.update( sideAlteration(**ikControlSpec) )
            
            print('ARGS', joints, pivotPoint, kwargs)
            
            ikCtrl, ikConstraints = cls.ik( joints, pivotPoint, **kwargs )
            return OutputControls(None, ikCtrl)
        
        suffix = card.findSuffix()
        #if not util.canMirror( card.start() ) or card.isAsymmetric():
        if not suffix or card.isAsymmetric():
            #suffix = card.findSuffix()
            if suffix:
                ctrls = _buildSide(joints, pivotPoint, False, suffix)
            else:
                ctrls = _buildSide(joints, pivotPoint, False)

            card.outputCenter.ik = ctrls.ik
        else:
            ctrls = _buildSide(joints, pivotPoint, False, 'left')
            card.outputLeft.ik = ctrls.ik

            pivotPoint[0] *= -1
            joints = [j.realMirror for j in card.joints[:-1]]
            ctrls = _buildSide(joints, pivotPoint, True, 'right' )
            card.outputRight.ik = ctrls.ik
    
    """
    @staticmethod
    def getExtraControls(ctrl):
        '''
        Returns the objs the squasher controls follow, which have the set driven keys.
        Cheesy at the moment because it's just the list of children (alphabetized).
        '''
        squashers = listRelatives(ctrl, type='transform')
        return sorted( set(squashers) )
    
    @classmethod
    def saveState(cls, card):
        sdkInfo = {}
        for ctrl, side, kinematicType in card.getMainControls():
            if kinematicType == 'ik':
                sdkInfo[side] = [ lib.anim.findSetDrivenKeys(o) for o in cls.getExtraControls(ctrl) ]
                
        state = card.rigState
        state['squasherSDK'] = sdkInfo
        card.rigState = state
        
    @classmethod
    def restoreState(cls, card):
        state = card.rigState
        if 'squasherSDK' not in state:
            return
        
        for ctrl, side, kinematicType in card.getMainControls():
            if kinematicType == 'ik':
                if side in state['squasherSDK']:
                    curves = state['squasherSDK'][side]
                    squashers = cls.getExtraControls(ctrl)
                    for squasher, crv in zip(squashers, curves):
                        lib.anim.applySetDrivenKeys(squasher, crv)
    """