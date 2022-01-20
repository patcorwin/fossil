from __future__ import absolute_import, division, print_function

import re

from pymel.core import aimConstraint, duplicate, delete, expression, group, \
    hide, joint, mel, orientConstraint, parentConstraint, pointConstraint, \
    select, selected, spaceLocator

from maya.api import OpenMaya

import pdil

from pdil import simpleName, shortName

from ._lib2 import controllerShape
from . import node

from .rigging._util import adds, defaultspec, getChain, constrainTo, parentGroup, trimName, ConstraintResults, drive,   saveRestLength, identifyAxis

mel.ikSpringSolver()


def intersect(mesh, point, ray):
    ''' This is probably some foundation for the yet-to-be surface follow stuff.
    '''
    fnMesh = OpenMaya.MFnMesh( pdil.capi.asMObject(mesh.getShape()).object() )

    p = spaceLocator()
    p.t.set(point)
    p.setParent( mesh )
    
    objSpacePos = p.t.get()

    p.setTranslation( ray, space='world' )

    objSpaceRay = p.t.get() - objSpacePos
    
    point = OpenMaya.MFloatPoint(objSpacePos)
    ray = OpenMaya.MFloatVector(objSpaceRay)
    res = fnMesh.allIntersections(point, ray, OpenMaya.MSpace.kObject, 50, False )

    # -> (hitPoints, hitRayParams, hitFaces, hitTriangles, hitBary1s, hitBary2s)

    if not len(res[0]):
        hits = []
    
    else:
        hits = []
        for hit in res[0]:
            p.t.set( hit.x, hit.y, hit.z)
            hits.append( p.getTranslation(space='world') )
    
    delete(p)
    
    return hits


def _getSwitchPlug(obj):
    '''
    !DUPED!
    Given the object a bind joint is constrained to, return the switching plug.
    '''

    bone = pdil.constraints.getOrientConstrainee(obj)
    constraint = orientConstraint( bone, q=True )
    
    plugs = orientConstraint(constraint, q=True, wal=True)
    targets = orientConstraint(constraint, q=True, tl=True)
    
    for plug, target in zip(plugs, targets):
        if target == obj:
            switchPlug = plug.listConnections(s=True, d=False, p=True)
            return switchPlug

    
def _getActiveControl(outputSide):
    ''' Give a card 'side', like hipCard.outputLeft, returns the ik or fk control that is active.
    '''
    if outputSide.ik and outputSide.fk:
        plug = _getSwitchPlug(outputSide.fk)[0]
        
        if plug.get() > 0.5:
            return outputSide.fk
        else:
            return outputSide.ik
    else:
        if outputSide.ik:
            return outputSide.ik
        else:
            return outputSide.fk


def addC(ctrl, target):
    '''
    Puts a `ctrl` on each child joint of the selected joints
    Target is a mirror list of the bound joints
    '''
    #expression -e -s "//\njoint5.rotateZ = nurbsCircle21.rotateZ + (nurbsCircle22.rz + nurbsCircle20.rotateZ)*.5;"  -o joint5 -ae 1 -uc all  expression2;
    obj = selected()[0]
        
    controls = []
    groups = []
    
    while obj:
    
        c = duplicate(ctrl)[0]
        c.setParent(obj)
        c.t.set(0, 0, 0)
        
        controls.append(c)
        
        spinner = group(em=True)
        spinner.setParent(obj)
        spinner.t.set(0, 0, 0)
        
        groups.append(spinner)
        
        pointConstraint( obj, target )
        orientConstraint( spinner, target )
        
        children = obj.listRelatives(type='joint')
        if children:
            obj = children[0]
        else:
            obj = None
            break

        target = target.listRelatives(type='joint')[0]
    
    for i, s in enumerate(groups[2:-2], 2):
        msg = '{0}.rz = {1[2]}.rz + ( {1[1]}.rz + {1[3]}.rz ) * 0.5 +  ( {1[0]}.rz + {1[4]}.rz ) * 0.2;'.format( s, controls[i - 2:i + 3] )
        expression( s=msg )
    
    msg = '{0}.rz = {1[0]}.rz + ( {1[1]}.rz ) * 0.5 +  ( {1[2]}.rz ) * 0.2;'.format( groups[0], controls[:3] )
    expression( s=msg )
    
    msg = '{0}.rz = {1[1]}.rz + ( {1[0]}.rz + {1[2]}.rz ) * 0.5 +  ( {1[3]}.rz ) * 0.2;'.format( groups[1], controls[:4] )
    expression( s=msg )
        
    msg = '{0}.rz = {1[2]}.rz + ( {1[1]}.rz ) * 0.5 +  ( {1[0]}.rz ) * 0.2;'.format( groups[-1], controls[-3:] )
    expression( s=msg )
    
    msg = '{0}.rz = {1[2]}.rz + ( {1[1]}.rz + {1[3]}.rz ) * 0.5 +  ( {1[0]}.rz ) * 0.2;'.format( groups[-2], controls[-4:] )
    expression( s=msg )
    

def makeTestJoints(raw=True):
    geom = selected()[0]

    prevJ = None
    ctrlJ = None

    joints = []
    
    for i in range(10):
        n = duplicate(geom)[0]
        select(cl=1)
        j = joint()
        joints.append(j)
        j.tz.set(-1 * i)
        n.setParent(j)
        n.t.set(0, 0, 0)
        
        if prevJ:
            j.setParent(prevJ)
        prevJ = j
        
        if raw:
            continue
        
        gj = j
        
        select(cl=1)
        j = joint()
        j.tz.set(-2 * i)
        j.ty.set(4)
        
        if ctrlJ:
            j.setParent(ctrlJ)
        ctrlJ = j
        
        orientConstraint( j, gj, mo=1, sk='z' )
        j.tz >> gj.tz


def getControlGroup(name):
    '''
    Used to organize controls under the main group.
    '''
    match = re.match( '[_a-zA-Z]+[_a-zA-Z0-9_]*', name )

    if not match or match.group(0) != name:
        raise Exception( "An invalid group name was given" )
    
    for child in node.mainGroup().listRelatives():
        if shortName(child) == name:
            return child
    
    g = group(em=True, name=name, p=node.mainGroup())
    pdil.dagObj.lock(g)

    return g


def squashLinker(name, ctrlA, ctrlB):
    '''
    Name the control that will be made to handle the sizes of two squash controllers.
    '''

    temp = pdil.dagObj.zero(ctrlA, apply=False, make=False).getParent()
    aTarget = parentConstraint(temp, q=True, tl=True)[0]

    temp = pdil.dagObj.zero(ctrlB, apply=False, make=False).getParent()
    bTarget = parentConstraint(temp, q=True, tl=True)[0]

    if aTarget.fullPath() in bTarget.fullPath():
        child, parent = aTarget, bTarget
        childCtrl, parentCtrl = ctrlA, ctrlB
    elif bTarget.fullPath() in aTarget.fullPath():
        child, parent = bTarget, aTarget
        childCtrl, parentCtrl = ctrlB, ctrlA
    else:
        raise Exception( 'Selected controls do not map to related joints' )
    
    joints = getChain(child, parent)
        
    # Get the current distance along the bones to get the 'zeroed' value.
    total = 0
    lengthCalc = ''
    for j in joints[1:]:
        total += max( [abs(t) for t in j.t.get()] )
        lengthCalc += 'abs({0}.t{1}) + '.format(j, identifyAxis(j))
    
    lengthCalc = lengthCalc[:-3]
    
    ctrl = controllerShape.build(name, {'shape': 'sphere'})
    zeroGrp = pdil.dagObj.zero(ctrl)

    pointConstraint(child, parent, zeroGrp)
    aimConstraint( child, zeroGrp )

    pdil.dagObj.lock(ctrl, 's r ty tz')

    exp = ('{child}.size = 1.0 * ((1.0/ ({length}/{total}) )-1.0) + 1.0*{ctrl}.tx;\n'
          '{parent}.size = 1.0 * ((1.0/ ({length}/{total}) )-1.0) - 1.0*{ctrl}.tx;') \
           .format( child=childCtrl, parent=parentCtrl, ctrl=ctrl, length=lengthCalc, total=total )
        
    print( exp )
        
    expression(s=exp)


def twistSetup(control, twistJoints, startSegment, endSegment, jointLenMultiplier, twistLateralAxis=[0, 1, 0], driverLateralAxis=[0, 1, 0], defaultPower=0.5):
    '''
    Given a list of twist joints, an anchoring startSegment and the endSegment
    
    :param twistJoints: The joints that will be twisted
    :param twistDriver: The end joint that will influence the twisting
    
    
    TwistJoints bone's aim axis = the lateral axis
    TwistJoints Up axis = points to the target (wrist)

    Assumption, all the twist joints and start segment are oriented the same
        
    World up = object rotation
    up obj = target (wrist)
    up axis = I think this is the target's lateral axis

    '''
        
    #anchor = duplicate( twistJoints, po=True )[0]
    #anchor.rename( simpleName(jnt, '{0}Anchor') )
    
    for jnt in twistJoints:
        aimer = duplicate( jnt, po=True )[0]
        space = duplicate( jnt, po=True )[0]
        
        saveRestLength(space)
        pdil.math.multiply(space.restLength, jointLenMultiplier) >> space.tx
        
        aimer.rename( simpleName(jnt, '{0}Aimer') )
        space.rename( simpleName(jnt, '{0}Space') )
        space.drawStyle.set(2)
        
        jnt.setParent( space )
        
        #hide(anchor, aimer)
        hide(aimer)
    
        constraint = orientConstraint( startSegment, aimer, space )
    
        constraint.interpType.set(2)  # Set to "shortest" because it will flip otherwise.
    
        aimConstraint( endSegment, aimer, wut='objectrotation', wuo=endSegment, mo=True,
                        u=twistLateralAxis, # identifyAxis(jnt, asVector=True),  # noqa e127
                        aimVector=[1, 0, 0], # identifyAxis(jnt, asVector=True),
                        wu=driverLateralAxis,
                    )
        
        baseRotAttr, endRotAttr = constraint.getWeightAliasList()
        
        driver = drive(control, simpleName(jnt, '{0}_Auto'), endRotAttr, minVal=0, maxVal=1, dv=defaultPower)
        pdil.math.opposite(driver) >> baseRotAttr
        
            
    #ctrl = control.build( trimName(twistDriver) + "Twist", controlSpec['main'], control.ROTATE)

    #ctrl.setParent(space)
    #ctrl.t.set( 0, 0, 0 )
    #ctrl.r.set( 0, 0, 0 )
    #lock( ctrl )
    # # Unlock the twist axis
    #ctrl.attr( 'r' + identifyAxis(twist) ).unlock()
    #ctrl.attr( 'r' + identifyAxis(twist) ).setKeyable(True)
    
    # Drive the space's constraint
#    anchorAttr, autoAttr = orientConstraint( constraint, q=1, wal=1 )
#    drive( ctrl, 'AutoTwistPower', autoAttr, minVal=0, maxVal=1, dv=defaultPower )
#    pdil.math.opposite( ctrl.AutoTwistPower ) >> anchorAttr
#    ctrl.AutoTwistPower.set( defaultPower )
    
    #orientConstraint( ctrl, twist )
    
    #ctrl = nodeApi.RigController.convert(ctrl)
    #ctrl.container = container
    
    #return ctrl, #container


def getBPJoint(realJoint):
    jnt = realJoint.message.listConnections(type=pdil.nodeApi.BPJoint)
    if jnt:
        return jnt[0]


@adds()
@defaultspec( {'shape': 'sphere', 'color': 'orange 0.22', 'size': 10} )
def fkChain(start, end, translatable=False, scalable=False, names=None, groupName='', mirroredTranslate=False, controlSpec={} ):
    '''
    Make an FK chain between the given joints.
    
    Args:
        start: PyNode, start of joint chain
        end: PyNode, end of chain
        translatable:
        scalable:
        names:
        mirroredTranslate: If true, inverts scale of zeroGroup so translation mirrors just like rotation
            
    ..  todo::
        I think I want to control spec housed elsewhere for easier accessibility.
    
    '''
    
    joints = getChain( start, end )
    if not joints:
        assert 'Could not make an chain between {0} and {1} because they are not in the same hierarchy'.format( start, end )
    
    container = parentGroup(start)
    
    container.setParent( node.mainGroup() )
    
    container.rename( trimName(start) + '_fkChain' )
    
    top = container
    
    leadOrient, leadPoint, leadScale = None, None, None
    
    controls = []
    
    validCtrl = None
    prevBPJ = None
    
    # This should never be hit in production, fk should always specify the correct names
    if names is None:
        names = [trimName(j) for j in names]
    
    for j, name in zip(joints, names):
        ctrl = controllerShape.build( name + "_ctrl",
                                controlSpec['main'],
                                type=controllerShape.ControlType.TRANSLATE if translatable else controllerShape.ControlType.ROTATE )
        controls.append( ctrl )
        pdil.dagObj.matchTo( ctrl, j )
        space = pdil.dagObj.zero( ctrl )
        
        if mirroredTranslate:
            space.s.set(-1, -1, -1,)
        
        # If the parent is a twist, make it a child of the most recent non-twist so twists are isolated.
        if top == container or (prevBPJ and not prevBPJ.info.get('twist')):
            space.setParent( top )
        else:
            space.setParent( validCtrl )
        
        top = ctrl
        
        if not translatable:
            pdil.dagObj.lock( ctrl, 't' )
            
        if not scalable:
            pdil.dagObj.lock( ctrl, 's' )
            orient, point = constrainTo( j, ctrl )
    
        else:
            orient, point, scaleConst = constrainTo( j, ctrl, includeScale=True )
            
            if leadScale:
                leadScale >> scaleConst
            else:
                leadScale = scaleConst
        
        if leadOrient:
            leadOrient >> orient
            leadPoint >> point
        else:
            leadOrient, leadPoint = orient, point
        
        
        prevBPJ = getBPJoint(j)
        if not prevBPJ.info.get('twist'):
            validCtrl = ctrl
        
    #drive( start, CONTROL_ATTR_NAME, leadOrient )
    #drive( start, CONTROL_ATTR_NAME, leadPoint )
    
    #drive( controls[0], CONTROL_ATTR_NAME, start.attr(CONTROL_ATTR_NAME) )
    #controls[0].attr(CONTROL_ATTR_NAME).set(1)
    #controls[0].attr(CONTROL_ATTR_NAME).setKeyable(False)
    
    # Always unlock the translate of the lead rotate if more than 1 joint
    if start != end:
        controls[0].tx.unlock()
        controls[0].ty.unlock()
        controls[0].tz.unlock()
        controls[0].tx.setKeyable(True)
        controls[0].ty.setKeyable(True)
        controls[0].tz.setKeyable(True)
        
    controls[0] = pdil.nodeApi.RigController.convert(controls[0])
    controls[0].container = container
    for i, c in enumerate(controls[1:]):
        controls[0].subControl[str(i)] = c
        
    return controls[0], ConstraintResults(leadPoint, leadOrient )
