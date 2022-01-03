from collections import OrderedDict

from maya.api import OpenMaya

from pymel.core import createNode, curve, delete, duplicate, dt, group, hide, joint, \
    loft, pointOnSurface, rebuildSurface, skinCluster, xform

import pdil

from .._lib2 import controllerShape
from ..cardRigging import MetaControl, ParamInfo
from .. import node

from . import _util as util


@util.adds()
@util.defaultspec( {'shape': 'box', 'size': 10, 'color': 'blue  0.22'},
)
# &&& OFFSET IS THE CARD'S! NORMAL
# Need to save weighting somehow...
def buildRibbon(start, end, normal, numControls=3, name='Ribbon', groupName='', controlSpec={}):

    chain = util.getChain( start, end )
    controlChain = util.dupChain(start, end)
    
    if not name:
        name = 'Ribbon'
    
    container = util.parentGroup(chain[0])
    container.setParent( node.mainGroup() )
    
    world = group(em=True)
    hide(world)
    world.setParent(container)
    
    #controlChain[0].setParent( container )
    
    crv = curve( d=1, p=[(0, 0, 0)] * len(chain) )
    
    for i, j in enumerate(chain):
        xform( crv.cv[i], t=xform(j, q=True, ws=True, t=True), ws=True )
    
    dup = duplicate(crv)[0]
    
    # &&& Obviously need to calc the offset somehow, maybe I can use the mirror state?  Maybe not, due to asymmetry
    #offset = dt.Vector(5, 0, 0)
    offset = normal

    crv.t.set(offset)
    dup.t.set(offset * -1)
    
    surfaceTrans = loft(crv, dup, uniform=True, polygon=0, sectionSpans=1, degree=3, autoReverse=True)[0]
    surfaceTrans.setParent(world)
    
    delete(crv, dup)
    
    rebuildSurface(surfaceTrans, rebuildType=0, replaceOriginal=True, spansU=1, spansV=(len(chain) - 1) * 2, dir=2, degreeV=3, degreeU=1)
    hide(surfaceTrans)
    
    surfaceShape = surfaceTrans.getShape()
    
    closest = createNode('closestPointOnSurface')
    surfaceShape.worldSpace >> closest.inputSurface
    
    vScalar = surfaceShape.minMaxRangeV.get()[1]
    
    #constraints = []
    
    for jnt, hairJoint in zip(chain, controlChain):
        #jnt.setParent(world)
        
        follicle = createNode('follicle')
        hide(follicle)
        trans = follicle.getParent()
        
        #hairJoints.append(trans)
        trans.setParent(world)
        
        pos = jnt.getTranslation(space='world')
        closest.inPosition.set(pos)
        
        surfaceShape.local >> follicle.inputSurface
        
        u = closest.parameterU.get()
        # closestPointOnSurface returns val in relation to the maxV but the follicle needs it normalized.
        v = closest.parameterV.get() / vScalar

        follicle.parameterU.set(u)
        follicle.parameterV.set(v)
        
        follicle.outTranslate >> trans.translate
        follicle.outRotate >> trans.rotate
        trans.translate.lock()
        trans.rotate.lock()
        hairJoint.setParent(trans)
        
    constraints = util.constrainAtoB(chain, controlChain)
    
    temp = pdil.capi.asMObject( surfaceShape )
    nurbsObj = OpenMaya.MFnNurbsSurface( temp.object() )

    controls = []
    controlJoints = []
    for i in range(numControls):
        percent = i / float(numControls - 1) * vScalar
        p = pointOnSurface(surfaceShape, u=.5, v=percent, p=True)
        

        ctrl = controllerShape.build(
            name + '%i' % (i + 1),
            controlSpec['main'],
            type=controllerShape.ControlType.TRANSLATE )
        
        ctrl.t.set(p)
        j = joint(ctrl)
        hide(j)
        controlJoints.append(j)
        
        ctrl.setParent(container)
        
        # Aim the control at the next joint with it's up following the surface
        if i < numControls - 1:
            target = chain[i + 1]
            normal = nurbsObj.normal(0.5, percent)
            pdil.anim.orientJoint(ctrl, target, upVector=dt.Vector(normal.x, normal.y, normal.z))
            pdil.dagObj.zero(ctrl)
        
        controls.append( ctrl )
    
    # Orient the final control to the final joint
    pdil.dagObj.matchTo( controls[-1], chain[-1])
    pdil.dagObj.zero(controls[-1])


    skinCluster( surfaceShape, controlJoints, tsb=True )


    mainCtrl = pdil.nodeApi.RigController.convert(controls[0])
    mainCtrl.container = container
    for i, ctrl in enumerate(controls[1:], 1):
        mainCtrl.subControl[str(i)] = ctrl
    
    return mainCtrl, constraints
    
    
class Ribbon(MetaControl):
    ''' Basic 3 joint ik chain. '''
    ik_ = 'pdil.tool.fossil.rigging.ribbon.buildRibbon'
    ikInput = OrderedDict( [
        ('name', ParamInfo( 'Name', 'Name', ParamInfo.STR, '')),
        ('numControls', ParamInfo( '# Controls', 'How many controls to build', ParamInfo.INT, 3)),
    ] )
    
    ikArgs = {}
    fkArgs = {'translatable': True}
    
    
    @classmethod
    def readIkKwargs(cls, card, isMirroredSide, sideAlteration=lambda **kwargs: kwargs, kinematicType='ik'):
        '''
        TODO: Needs to handle mirroring
        '''

        kwargs = cls.readKwargs(card, isMirroredSide, sideAlteration, kinematicType='ik')
        """
        if isMirroredSide:
            if 'curve' in kwargs:
                crv = kwargs['curve']
                crv = duplicate(crv)[0]
                kwargs['curve'] = crv
                move( crv.sp, [0, 0, 0], a=True )
                move( crv.rp, [0, 0, 0], a=True )
                crv.sx.set(-1)
                
                kwargs['duplicateCurve'] = False
        """
        
        kwargs['normal'] = card.upVector()
                
        return kwargs
    