from __future__ import absolute_import, division, print_function

from collections import OrderedDict


from pymel.core import aimConstraint, duplicate, hide, orientConstraint, parent

import pdil

from ..cardRigging import MetaControl, ParamInfo

from .._core import config
from .._lib2 import controllerShape
from .. import node

from . import _util as util


@util.adds('AutoTwistPower')
@util.defaultspec( {'shape': 'disc', 'color': 'blue 0.22', 'size': 5, 'align': 'x'} )
def buildTwist(twist, twistDriver, twistLateralAxis=[0, 1, 0], driverLateralAxis=[0, 1, 0], defaultPower=0.5, controlSpec={}):
    '''
    Twist bone's aim axis = the lateral axis
    Twist Up axis = points to the target (wrist)
    
    World up = object rotation
    up obj = target (wrist)
    up axis = I think this is the target's lateral axis
    
    ..  todo::
        I'm not sure, but it look like a "_L" is sneaking into the name somewhere
    '''
    
    container = util.parentGroup(twist)
    container.setParent( node.mainGroup() )
    container.rename( util.trimName(twist) + '_twist' )
    
    anchor = duplicate( twist, po=True )[0]
    aimer = duplicate( twist, po=True )[0]
    space = duplicate( twist, po=True )[0]
    anchor.rename( pdil.simpleName(twist, '{0}Anchor') )
    aimer.rename( pdil.simpleName(twist, '{0}Aimer') )
    space.rename( pdil.simpleName(twist, '{0}Space') )
    space.drawStyle.set(2)
    
    hide(anchor, aimer)
    parent( anchor, aimer, space, container )
    
    constraint = orientConstraint( anchor, aimer, space )
    constraint.interpType.set(2)  # Set to "shortest" because it will flip otherwise.
    
    aimConstraint( twistDriver, aimer, wut='objectrotation', wuo=twistDriver, mo=True,
                    u=util.identifyAxis(twist, asVector=True),  # noqa e127
                    aimVector=twistLateralAxis,
                    wu=driverLateralAxis,
                )
    
    ctrl = controllerShape.build( util.trimName(twistDriver) + "Twist", controlSpec['main'], controllerShape.ControlType.ROTATE)

    ctrl.setParent(space)
    ctrl.t.set( 0, 0, 0 )
    ctrl.r.set( 0, 0, 0 )
    pdil.dagObj.lock( ctrl )
    # Unlock the twist axis
    ctrl.attr( 'r' + util.identifyAxis(twist) ).unlock()
    ctrl.attr( 'r' + util.identifyAxis(twist) ).setKeyable(True)
    
    # Drive the space's constraint
    anchorAttr, autoAttr = orientConstraint( constraint, q=1, wal=1 )
    util.drive( ctrl, 'AutoTwistPower', autoAttr, minVal=0, maxVal=1, dv=defaultPower )
    pdil.math.opposite( ctrl.AutoTwistPower ) >> anchorAttr
    ctrl.AutoTwistPower.set( defaultPower )
    
    orientConstraint( ctrl, twist )
    
    ctrl = pdil.nodeApi.RigController.convert(ctrl)
    ctrl.container = container
    
    return ctrl, container


class TwistHelper(MetaControl):
    ''' Special controller to automate distributed twisting, like on the forearm. '''
    #displayInUI = False

    fk_ = 'pdil.tool.fossil.rigging.twistHelper.buildTwist'

    fkInput = OrderedDict( [
        ('defaultPower', ParamInfo( 'Default Power', 'Default automatic twist power', ParamInfo.FLOAT, 0.5)),
    ] )

    @classmethod
    def build(cls, card, buildFk=True):
        '''
        ..  todo::
            Make this actually respect control overrides.
        '''

        #twist(twist, twistDriver, twistLateralAxis=[0,0,1], driverLateralAxis=[0,0,1], controlSpec={}):

        kwargs = cls.readFkKwargs(card, False)

        side = card.findSuffix()

        #if not util.canMirror( card.start() ) or card.isAsymmetric():
        if not side or card.isAsymmetric():
            ctrl, container = cls.fk(card.joints[0].real, card.extraNode[0].real, **kwargs)
            card.outputCenter.fk = ctrl
        else:
            # Build one side...
            #side = config.letterToWord[sideCode]
            
            ctrl, container = cls.fk(card.joints[0].real, card.extraNode[0].real, **kwargs)
            card.getSide(side).fk = ctrl
            
            # ... then flip the side info and build the other
            #side = config.otherLetter(side)
            side = config.otherSideCode(side)
            ctrl, container = cls.fk(card.joints[0].realMirror, card.extraNode[0].realMirror, **kwargs)
            card.getSide(side).fk = ctrl

