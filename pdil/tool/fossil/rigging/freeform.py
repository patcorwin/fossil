from collections import OrderedDict
import logging

from pymel.core import group

import pdil

from .._lib2 import controllerShape
from ..cardRigging import MetaControl, ParamInfo, OutputControls
from .. import node

from . import _util as util

log = logging.getLogger('fossil_controller_debug')


@util.adds()
@util.defaultspec( {'shape': 'sphere', 'color': 'orange 0.22', 'size': 10} )
def buildFreeform(joints, translatable=False, mirroredTranslate=False, scalable=False, groupName='', controlSpec={} ):
    '''
    Make an FK chain between the given joints.
    
    :param PyNode start: Start of joint chain
    :param PyNode end: End of chain
    :param bool translatable: Default=False
    :param bool mirroredTranslate: If true, translations will be flipped
    :param dict controlSpec: Override default control details here.  Only has 'main'.
    
    ..  todo::
        I think I want to control spec housed elsewhere for easier accessibility.
    
    '''
    
    # Make a top level section for each lead joint in the subHierarchy
    #topLevel = [j for j in joints if j.getParent() not in joints]

    topContainer = group(n=pdil.simpleName(joints[0], '{0}_Freeform'), p=node.mainGroup(), em=True)
    
    #top = container
    #leadOrient, leadPoint = None, None
    
    controls = []
    
    done = {}
    for j in joints:
        done[j] = False

    for j in joints:

        ctrl = controllerShape.build(   util.trimName(j) + "_ctrl",
                                controlSpec['main'],
                                type=controllerShape.ControlType.TRANSLATE if translatable else controllerShape.ControlType.ROTATE )
        controls.append( ctrl )
        pdil.dagObj.matchTo( ctrl, j )

        constraints = util.constrainTo( j, ctrl, includeScale=scalable )

        space = pdil.dagObj.zero( ctrl )
        if mirroredTranslate:
            space.s.set(-1, -1, -1)
        
        done[j] = (ctrl, space)

        # Lock unneeded transforms
        if not translatable:
            pdil.dagObj.lock( ctrl, 't' )
        
        if not scalable:
            pdil.dagObj.lock( ctrl, 's' )
        else:
            # Preserving scaling symmetry if translations are mirrored
            if mirroredTranslate:
                constraints[2].node().offsetZ.set(-1)

    # Parenting the controllers is challenging since they could occur in any order
    for jnt, (ctrl, space) in done.items():
        if jnt.getParent() in done:
            space.setParent( done[jnt.getParent()][0] )
        else:
            container = util.parentGroup(jnt)
            container.setParent(topContainer)
            container.rename( util.trimName(jnt) + '_fkChain' )

            space.setParent(container)

    # A leader must be choosen, so just use the order they were built in
    ctrl = pdil.nodeApi.RigController.convert(controls[0])
    log.debug( 'The leader is {}'.format(ctrl) )
    for i, c in enumerate(controls[1:]):
        ctrl.subControl[str(i)] = c
        log.debug( 'Adding {} {}'.format(i, c) )

    ctrl.container = topContainer

    return ctrl, None # ConstraintResults(leadPoint, leadOrient )
    
    
class Freeform(MetaControl):
    ''' Allows for non-linear arbitrary joint chains with translating and rotating controls. '''
    fkInput = OrderedDict( [
        ('translatable', ParamInfo( 'Translatable', 'It can translate', ParamInfo.BOOL, default=True)),
        ('scalable', ParamInfo( 'Scalable', 'It can scale', ParamInfo.BOOL, default=False)),
        ('mirroredTranslate', ParamInfo( 'Mirror Translate', 'Translation is also mirrored on mirrored side', ParamInfo.BOOL, default=False)),
    ] )

    @classmethod
    def validate(cls, card):
        pass
    
    @classmethod
    def _buildSide(cls, card, start, end, isMirroredSide, side=None, buildFk=True):
        '''
        Since the joints aren't in a chain, just pass them all along to get sorted out later.
        '''
        
        #log.Rotation.check(rig.getChain(start, end), True)
        
        ikCtrl = None
        
        sideAlteration = cls.sideAlterationFunc(side)
        fkControlSpec = cls.controlOverrides(card, 'fk')
        
        kwargs = cls.readFkKwargs(card, isMirroredSide, sideAlteration)
        
        kwargs.update( sideAlteration(**fkControlSpec) )
        
        # Pass the correct joints to the correct side.  Also only the mirrored side gets `mirroredTranslate`
        if isMirroredSide:
            joints = [j.realMirror for j in card.joints if not j.isHelper]
        else:
            kwargs.pop('mirroredTranslate', None)
            
            joints = [j.real for j in card.joints if not j.isHelper]
        
        log.debug('Building {}, mirrored={}  kwargs={}'.format(card, isMirroredSide, kwargs) )
        
        fkCtrl, emptyConstraints = buildFreeform(joints, **kwargs)
        
        return OutputControls(fkCtrl, ikCtrl)