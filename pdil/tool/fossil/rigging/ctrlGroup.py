from collections import OrderedDict

from pymel.core import group, parentConstraint, xform

import pdil

from ..cardRigging import MetaControl, ParamInfo, OutputControls
from .._core import config
from .._lib2 import controllerShape
from .. import node

from . import _util as util


@util.adds()
@util.defaultspec( {'shape': 'sphere', 'color': 'blue 0.22', 'size': 10} )
def buildCtrlGroup(parentJoint, point, rotation, name='Group', translatable=True, scalable=False, mirroredTranslate=False, useTrueZero=False, groupName='', controlSpec={} ):
    '''
    Makes a control at the given point
    
    :param PyNode start: Start of joint chain
    :param bool translatable: Default=True
    :param dict controlSpec: Override default control details here.  Only has 'main'.
    '''
    
    # Can't use parentGroup() since target isn't a real joint.
    container = group( em=True, name='{0}_Proxy'.format(name) )
    
    if parentJoint:
        parentConstraint( parentJoint, container, mo=False )
    
    container.setParent( node.mainGroup() )
        
    ctrl = controllerShape.build(   name + "_ctrl",
                            controlSpec['main'],
                            type=controllerShape.ControlType.TRANSLATE if translatable else controllerShape.ControlType.ROTATE )
    
    ctrl.t.set(point)

    if not useTrueZero:
        ctrl.r.set(rotation)
    
    zeroGroup = pdil.dagObj.zero( ctrl ).setParent( container )

    if useTrueZero:
        ctrl.r.set(rotation)
        util.storeTrueZero(ctrl, rotation)
        
    if not translatable:
        pdil.dagObj.lock( ctrl, 't' )
        
    if not scalable:
        pdil.dagObj.lock( ctrl, 's' )
    
    if mirroredTranslate:
        zeroGroup.s.set(-1, -1, -1)
    
    ctrl = pdil.nodeApi.RigController.convert(ctrl)
    ctrl.container = container
    
    leadOrient, leadPoint = None, None
    return ctrl, util.ConstraintResults(leadPoint, leadOrient)
    
    
class Group(MetaControl):
    ''' A control that doesn't control a joint.  Commonly used as a space for other controls. '''
    fkInput = OrderedDict( [
        ('name', ParamInfo( 'Name', 'Name', ParamInfo.STR, '')),
        ('translatable', ParamInfo( 'Translatable', 'It can translate', ParamInfo.BOOL, default=True)),
        ('scalable', ParamInfo( 'Scalable', 'It can scale', ParamInfo.BOOL, default=False)),
        ('mirroredTranslate', ParamInfo( 'Mirror Translate', 'Translation is also mirrored on mirrored side', ParamInfo.BOOL, default=False)),
        ('useTrueZero', ParamInfo( 'True Zero', 'Use true zero like ik controls', ParamInfo.BOOL, default=False)),
    ] )

    @classmethod
    def validate(cls, card):
        # &&& Eventually just validate that all it's joints are non-helpers
        pass
    
    @classmethod
    def _buildSide(cls, card, start, end, isMirroredSide, side=None, buildFk=True):
        '''
        Most inputs are ignored because it does it's own thing since the joints
        don't exist.
        
        
        ..  todo:: Will need special attention to deal with twin mode.
        '''
        # DO NOT check rotation on a thing that doesn't exist.
        # log.Rotation.check(rig.getChain(start, end), True)
        
        ikCtrl = None
        
        sideAlteration = cls.sideAlterationFunc(side)
        fkControlSpec = cls.controlOverrides(card, 'fk')
        
        # kwargs = collections.defaultdict(dict)
        # kwargs.update( cls.fkArgs )
        # kwargs['controlSpec'].update( cls.fkControllerOptions )
        # kwargs.update( sideAlteration(**fkControlSpec) )

        kwargs = cls.readFkKwargs(card, isMirroredSide, sideAlteration)

        if not kwargs['name']:
            kwargs['name'] = pdil.simpleName(card.start())

        if side == 'left':
            kwargs['name'] += config.controlSideSuffix('left')
        elif side == 'right':
            kwargs['name'] += config.controlSideSuffix('right')

        kwargs.update( sideAlteration(**fkControlSpec) )
        
        position = xform(card.start(), q=True, ws=True, t=True)
        
        # If there is 1 joint, orient as the card (for backwards compatibility)
        # but if there are more, figure out what it's orientation should be
        if len(card.joints) == 1:
            rotation = xform(card, q=True, ws=True, ro=True)
        else:
            pdil.anim.orientJoint(card.joints[0], card.joints[1], xform(card.joints[0], q=True, ws=True, t=True) + card.upVector())
            rotation = xform(card.joints[0], q=True, ws=True, ro=True)
        
        if isMirroredSide:
            position[0] *= -1.0
            
            if card.mirror == 'twin':
                rotation[1] *= -1.0
                rotation[2] *= -1.0
            else:
                rotation[1] *= -1.0
                rotation[2] *= -1.0
        else:
            kwargs.pop('mirroredTranslate', None)

        if not card.start().parent:
            parent = None
        else:
            if isMirroredSide and card.start().parent.realMirror:
                parent = card.start().parent.realMirror
            else:
                parent = card.start().parent.real
        
        fkCtrl, emptyConstraints = buildCtrlGroup(parent, position, rotation, **kwargs)
        
        if isMirroredSide:
            # &&& Handling twin is probably super fragile, must test different maya up and orient the card in funky ways.
            space = pdil.dagObj.zero(fkCtrl, make=False)
            if card.mirror == 'twin':
                space.rz.set( space.rz.get() + 180 )
            else:
                space.rx.set( space.rx.get() + 180 )
        
        return OutputControls(fkCtrl, ikCtrl)