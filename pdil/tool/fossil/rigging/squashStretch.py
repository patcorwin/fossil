from collections import OrderedDict
from functools import partial

from pymel.core import dt, hide, listRelatives, setDrivenKeyframe, spaceLocator, xform

import pdil


from ..cardRigging import MetaControl, ParamInfo, colorParity, OutputControls

from .. import log
from .. import node
from .._lib import misc
from .._lib import space
from .._lib2 import controllerShape

from . import _util as util


@util.adds()
@util.defaultspec( {'shape': 'box',    'size': 10, 'color': 'blue  0.22'},
            manual={'shape': 'sphere', 'size':  5, 'color': 'green 0.22'}
)
def buildSquashAndStretch(joints, squashCenter, orientAsParent=True, rangeMin=-5, rangeMax=5, scaleMin=0.5, scaleMax=2, controlSpec={}):
    '''
    :param joints: List of joints that will scale
    :param squashCenter: The worldspace center point to place the master squash control.
    :param orientAsParent: Whether the control should be oriented ?? Does this make sense?... Probably not
    '''
    
    squashCenter = dt.Vector(squashCenter)
    container = util.parentGroup(joints[0])
    container.setParent( node.mainGroup() )
    
    mainCtrl = controllerShape.build(   util.trimName(joints[0].getParent()) + "SquashMain_ctrl",
                                controlSpec['main'],
                                type=controllerShape.ControlType.TRANSLATE )
    mainCtrl = pdil.nodeApi.RigController.convert(mainCtrl)
    mainCtrl.setParent(container)
    
    mainCtrl.addAttr( 'size', at='double', min=rangeMin, max=rangeMax, dv=0.0, k=True )
    
    pdil.dagObj.lock(mainCtrl, 's')
    
    if orientAsParent:
        pdil.dagObj.matchTo( mainCtrl, joints[0].getParent() )
                            
    xform(mainCtrl, ws=True, t=squashCenter)
    
    pdil.dagObj.zero(mainCtrl)
    
    subControls = []
    for i, j in enumerate(joints):
        subCtrl = controllerShape.build(util.trimName(j) + "_ctrl",
                                controlSpec['manual'],
                                type=controllerShape.ControlType.TRANSLATE )
        subControls.append(subCtrl)
        pdil.dagObj.matchTo(subCtrl, j)
        subCtrl.setParent(container)
        pdil.dagObj.zero(subCtrl)
        pdil.dagObj.lock(subCtrl, 'r s')
        
        scalingLoc = spaceLocator()
        scalingLoc.rename( util.trimName(j) + '_squasher' )
        pdil.dagObj.matchTo(scalingLoc, j)
        hide(scalingLoc)
        scalingLoc.setParent(mainCtrl)
        
        space.add(subCtrl, scalingLoc, 'standard')
                
        ctrlPos = dt.Vector(xform(subCtrl, q=True, ws=True, t=True))
        
        setDrivenKeyframe( scalingLoc, at=['tx', 'ty', 'tz'], cd=mainCtrl.size )
        
        mainCtrl.size.set(rangeMin)
        lower = (ctrlPos - squashCenter) * scaleMin + squashCenter
        xform(scalingLoc, ws=True, t=lower)
        setDrivenKeyframe( scalingLoc, at=['tx', 'ty', 'tz'], cd=mainCtrl.size )
        
        mainCtrl.size.set(rangeMax)
        upper = (ctrlPos - squashCenter) * scaleMax + squashCenter
        xform(scalingLoc, ws=True, t=upper)
        setDrivenKeyframe( scalingLoc, at=['tx', 'ty', 'tz'], cd=mainCtrl.size )
        
        mainCtrl.size.set(0.0)
        xform(scalingLoc, ws=True, t=(ctrlPos))
        
        mainCtrl.subControl[str(i)] = subCtrl
        
    constraints = util.constrainAtoB(joints, subControls)
    
    mainCtrl.container = container
    
    return mainCtrl, constraints


class SquashStretch(MetaControl):
    ''' Special controller providing translating bones simulating squash and stretch. '''
    displayInUI = False

    #ik_ = 'pdil.tool.fossil.rigging.buildSquashAndStretch'
    ik_ = __name__ + '.' + buildSquashAndStretch.__name__
    
    ikInput = OrderedDict( [
        ('rangeMin', ParamInfo( 'Min Range', 'Lower bounds of the keyable attr.', ParamInfo.FLOAT, -5.0)),
        ('rangeMax', ParamInfo( 'Max Range', 'Upper bounds of the keyable attr.', ParamInfo.FLOAT, 5.0)),
        ('scaleMin', ParamInfo( 'Shrink Value', 'When the attr is at the lower bounds, scale it to this amount.', ParamInfo.FLOAT, .5)),
        ('scaleMax', ParamInfo( 'Expand Value', 'When the attr is at the upper bounds, scale it to this amount.', ParamInfo.FLOAT, 2)),
    ] )
    
    #orientAsParent=True, min=0.5, max=1.5
    
    @classmethod
    def build(cls, card):
        '''
        Custom build that uses all the joints, except the last, which is used
        as a virtual center/master control for all the scaling joints.
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
            
            ikCtrl, ikConstraints = cls.ik( joints, pivotPoint, **kwargs )
            return OutputControls(None, ikCtrl)
    
        side = card.findSuffix()
    
        #if not util.canMirror( card.start() ) or card.isAsymmetric():
        if not side or card.isAsymmetric():
            suffix = card.findSuffix()
            if suffix:
                ctrls = _buildSide(joints, pivotPoint, False, suffix)
            else:
                ctrls = _buildSide(joints, pivotPoint, False)

            card.outputCenter.ik = ctrls.ik
        else:
            ctrls = _buildSide(joints, pivotPoint, False, 'L')
            card.outputLeft.ik = ctrls.ik

            pivotPoint[0] *= -1
            joints = [j.realMirror for j in card.joints[:-1]]
            ctrls = _buildSide(joints, pivotPoint, True, 'R' )
            card.outputRight.ik = ctrls.ik
    
    @staticmethod
    def getSquashers(ctrl):
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
                sdkInfo[side] = [ misc.findSDK(o) for o in cls.getSquashers(ctrl) ]
                
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
                    squashers = cls.getSquashers(ctrl)
                    for squasher, crv in zip(squashers, curves):
                        misc.applySDK(squasher, crv)