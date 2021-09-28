'''
This is how rigs are actually created.

When defining controls, they must all follow this pattern:

    @defaultspec( {'shape': control.box,    'size': 10, 'color':'green 0.22' },
               pv={'shape': control.sphere, 'size': 5,  'color':'green 0.92' } )

    someControl(startJoint, endJoint, <keyword Args altering behavior>, name='', groupName='', controlSpec={} )

        return control, container
    
        `name` (Likely for most IkControls only) will be name of the control, respecting the suffix.
        
        `groupName` is the optional subgroup the control parts be put under, purely for organization.
            It falls back to the visGroup of the 'main' controller.
        `controlSpec` will be filled and can have parts overridden.  This works
            in conjunction with the `defaultspec` decorator
            
        Returns:
        `control` is the 'main' control.  Additional controls get added it it
            via control.subControl['some name'] = other control.

        `container` is the group that is made to hold all the junk under the main controller.
        

..  todo:: BUGS

    *** I REALLY NEED TO CHECK FOR THE SIDE SUFFIX!  It's super weird when something doesn't build.
        I could also do some work on deriving the rig/rigMirror by looking for the existing joint
        that's a child of the expected root joint.
        * Maybe cards also inherit parent card suffix!
        
    * ik need fk built along with them
        * And then match them
            * across time
        
    * Move mirror tagging from joints to cards completely
        
    * shape didn't appear to change for pin

    * Adding splineIk to naga chose the wrong axis to plug into spinners

    * The alignment of the dogleg bend is off IF the card is not on axis in some ways.
        I'm not sure of the exact conditions but if I leave the card at 90 rotations, everything appears fine.
        
    * Need to address when something is mirrored but doesn't have a suffix.
        
..  todo::
    * Make an -align flag for controls.  This also might entail some mirroring
    
    * Put all the controls in a group just like ikChain is done.
    
    Show anticipated controllers!

    Stretchy IK is editable (probably just expose as off and on)

    Tool to easily make a blueprint that matches an existing skeleton
    (probably will want to add tip joints to most things).
    
    Align hand control to hand joint.

    Each rig has a list of criteria so it's easy to test if rigging will actually work or not.
    Figure out why the last neck isn't connected to spine, must spine exist first?
    Joe said arms won't get made unless unless the spine exists, verify this is the case.

    Need to add FK to hindleg
    Need to add tail control like Joe has.
        Need to add FK control to it too.
        
    hindleg needs to not make the human foot.
    Need to make animal foot.
    
'''
from __future__ import absolute_import

import collections
import math
import re

#from pymel.core import *
from pymel.core import addAttr, aimConstraint, arclen, cluster, createNode, curve, \
    duplicate, delete, dt, expression, group, \
    hide, ikHandle, insertKnotCurve, joint, listRelatives, makeIdentity, \
    move, mel, orientConstraint, parent, \
    parentConstraint, pointConstraint, pointOnCurve, poleVectorConstraint, PyNode, \
    rotate, select, selected, setDrivenKeyframe, showHidden, skinCluster, \
    spaceLocator, upAxis, xform

from maya.api import OpenMaya
import maya.OpenMayaAnim
import maya.OpenMaya

from ...add import simpleName, shortName
from ...core.dagObj import lockRot, lockTrans, lockScale, Solo
from ... import core
from ... import lib
from ... import nodeApi

from . import controllerShape
from . import log
from . import node
from . import space
from . import util

from .rigging._util import adds, defaultspec, getChain, constrainTo, parentGroup, trimName, storeTrueZero, ConstraintResults, constrainAtoB, drive, EndOrient, shortestAxis, trueZeroSetup, determineClosestWorldOrient, trueZeroFloorPlane, chainLength, dupChain, prune, findChild, createMatcher, calcOutVector, saveRestLength, makeStretchySpline, _makeStretchyPrep, identifyAxis, advancedTwist, midAimer

mel.ikSpringSolver()

CONTROL_ATTR_NAME = 'influence'


def intersect(mesh, point, ray):
    fnMesh = OpenMaya.MFnMesh( core.capi.asMObject(mesh.getShape()).object() )

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

    bone = core.constrains.getOrientConstrainee(obj)
    constraint = orientConstraint( bone, q=True )
    
    plugs = orientConstraint(constraint, q=True, wal=True)
    targets = orientConstraint(constraint, q=True, tl=True)
    
    for plug, target in zip(plugs, targets):
        if target == obj:
            switchPlug = plug.listConnections(s=True, d=False, p=True)
            return switchPlug

    
def _getActiveControl(outputSide):
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

    
def getMainController(obj): # &&& TODO rename to `lead` controller, as there is already a main!  Which I did in `findNode`?  Ugg, this is worse than I thought.
    '''
    Given a controller, return the main RigController (possibly itself) or
    None if not found.
    '''
    #print('GMC, ', obj, isinstance(obj, nodeApi.fossilNodes.RigController))
    #print('   ', obj.__class__.__module__, obj.__class__.__name__)
    #if isinstance(obj, nodeApi.RigController):
    if obj.__class__.__name__ == 'RigController' and obj.__class__.__module__ == 'pdil.nodeApi.fossilNodes':
        return obj
    else:
        objs = obj.message.listConnections(type=nodeApi.RigController)
        if objs:
            return objs[0]
    
    return None
    
#pymel.internal.factories.registerVirtualClass( RigController )


def getDepth(jnt, depth):
    current = 1
    
    child = jnt
    while current < depth:
        child = child.listRelatives(type='joint')[0]
        current += 1
        
    return child


"""
def adds(*attributes):
    '''
    Marks a function with fossilDynamicAttrs to track the attributes made so
    special sauce can be identified.
    '''
    def realDecorator(func):
        setattr(func, 'fossilDynamicAttrs', attributes)
        return func
    
    return realDecorator


def defaultspec(defSpec, **additionalSpecs):
    '''
    Decorator to used to specify the default control building values.
    
    ex:
        @defaultspec( {'shape':control.box, 'size', 10: 'color': 'blue 0.22'} )
        def buildLeg( ... , controlSpec={})
            ...
            control.build( 'FootControl', controlsSpec['main'] )
            
    Or, for multiple controls:
        @defaultspec( {'shape':control.box, 'size', 10: 'color': 'blue'},
            pv={'shape':control.sphere, 'size', 8: 'color': 'green'})
        def buildLegIk( ... , controlSpec={})
            ...
            control.build( 'FootControl', controlsSpec['main'] )
            ...
            control.build( 'FootControl', controlsSpec['pv'] ) # Same keyword as was passed in to defaultspec
    
    
    The reason is this allows for partial overriding, if a value isn't specifice,
    the default is used.  This also saves from having a long default argument
    list which varies from control to control.
    
    If some aspect of a rig adds an additional control, it is trivial to add it
    as a spec into the system.
    
    ..  todo::
        I might want to log spec errors is some better way to show them all at the end
    '''

    def realDecorator(func):
        # allSpecs will be an alterable, the source remains untouched.
        allSpecs = { 'main': defSpec.copy() }
        if 'visGroup' not in allSpecs['main']:
            allSpecs['main']['visGroup'] = ''
        if 'align' not in allSpecs['main']:
            allSpecs['main']['align'] = 'y'
        
        for specName, spec in additionalSpecs.items():
            allSpecs[specName] = spec.copy()
            if 'visGroup' not in allSpecs[specName]:
                allSpecs[specName]['visGroup'] = ''
            if 'align' not in allSpecs[specName]:
                allSpecs[specName]['align'] = 'y'
                
        def newFunc(*args, **kwargs):
            
            # Make a copy of the spec that can be modified
            tempSpec = {}
            for specName, spec in allSpecs.items():
                tempSpec[specName] = spec.copy()
            
            # Override default controlSpecs with whatever the user provides
            if 'controlSpec' in kwargs:
                # Apply any overridden spec data
                for specName, spec in kwargs['controlSpec'].items():
                    if specName in tempSpec:
                        tempSpec[specName].update( spec )
                    else:
                        warning( 'Ignoring unused spec {0}'.format(specName) )
                
            kwargs['controlSpec'] = tempSpec
                
            #argspec = inspect.getargspec(func)
            #print argspec
            #print args, kwargs
                
            res = func(*args, **kwargs)
            
            # Now that all the controls are made, we can safely apply the
            # visGroup, since they apply to the '_space' group, not the actual
            # control which is connected to the ik/fk switch attr
            if tempSpec['main']['visGroup']:
                lib.sharedShape.connect(res[0], (tempSpec['main']['visGroup'], 1) )
            
            subControls = res[0].subControl.items()
            if subControls:
                
                # If there is one spec and sub controls, it is a chain so apply the same visgroup
                if len(tempSpec) == 1 and tempSpec['main']['visGroup']:
                    for name, ctrl in subControls:
                        lib.sharedShape.connect(ctrl, (tempSpec['main']['visGroup'], 1) )
            
                # If there are 2 specs, the non-main is the repeating one
                elif len(tempSpec) == 2:
                    specName = tempSpec.keys()[:].remove('main')
                    visGroup = tempSpec['main']['visGroup']
                    if visGroup:
                        for name, ctrl in subControls:
                            lib.sharedShape.connect(ctrl, (visGroup, 1) )
                
                # Finally, each additional spec should match a sub control
                else:
                    for specName in tempSpec:
                        if specName == 'main':
                            continue
                        
                        if tempSpec[specName]['visGroup']:
                            try:  # &&& Eventually this needs to not ignore errors
                                lib.sharedShape.connect(
                                    res[0].subControl[specName],
                                    (tempSpec[specName]['visGroup'], 1)
                                )
                            except:
                                pass
            
            return res
        # Store the default spec so it's easy to access for other things.
        setattr( newFunc, '__defaultSpec__', allSpecs )
        functools.update_wrapper( newFunc, func )
        return newFunc
        
    return realDecorator
"""


def calcOutVectorRaw(start, middle, end):
    '''
    Same as calcOutVector but isn't constrained to xz plane.
    '''

    s = dt.Vector( xform(start, q=1, ws=1, t=1) )
    m = dt.Vector( xform(middle, q=1, ws=1, t=1) )
    e = dt.Vector( xform(end, q=1, ws=1, t=1) )

    out = (m - s) + (m - e)
    out.normalize()

    return out


def bugleg(start, end):
    '''
    Make chain, spring IK across whole thing
    Replicate dogleg roll at both ends
    
    '''
    pass


    
def makeStretchyNonSpline(controller, ik, stretchDefault=1):
    start, chain, jointAxis, switcher = _makeStretchyPrep( controller, ik, stretchDefault )

    dist, grp = core.dagObj.measure(start, ik)
    grp.setParent( controller )
    dist.setParent( ik.getParent() )
    length = dist.distance
    
    lengthMax = chainLength(chain)
    # Regular IK only stretches
    # ratio = (abs distance between start and end) / (length of chain)
    ratio = core.math.divide( length, lengthMax )
    # multiplier is either 1 or a number greater than one needed for the chain to reach the end.
    multiplier = core.math.condition( ratio, '>', 1.0, true=ratio, false=1 )

    controller.addAttr( 'length', at='double', min=-10.0, dv=0.0, max=10.0, k=True )

    '''
    lengthMod is the below formula:

    if controller.length >= 0:
        controller.length/10.0 + 1.0 # 1.0 to 2.0 double the length of the limb
    else:
        controller.length/20.0  + 1.0 # .5 to 1.0 halve the length of the limb
    '''
    lengthMod = core.math.add(
        core.math.divide(
            controller.length,
            core.math.condition(controller.length, '>=', 0, 10.0, 20.0)
        ),
        1.0
    )
    
    jointLenMultiplier = core.math.multiply(switcher.output, lengthMod)
    
    multiplier >> switcher.input[1]
    
    for i, j in enumerate(chain[1:], 1):
        saveRestLength(j, jointAxis)
        #util.recordFloat(j, 'restLength', j.attr('t' + jointAxis).get() )
            
        # Make an attribute that is -10 to 10 map to multiplying the restLength by 0 to 2
        attrName = 'segLen' + str(i)
        controller.addAttr( attrName, at='double', k=True, min=-10, max=10 )
        normalizedMod = core.math.add(core.math.divide( controller.attr(attrName), 10), 1)
        #segmentLength = controller.attr(attrName)
        # normalizedMod = core.path.parse(' (segmentLength / 10) + 1')
        
        "j.attr('t' + jointAxis) = lockSwitcher.output = jointLenMultiplier * normalizedMod * j.restLength"
        
        # As of 2/9/2019 it looks to be fine to make this even if it's not used by the ik to lock the elbow (like in dogleg)
        lockSwitcher = createNode('blendTwoAttr', n='lockSwitcher')
        
        # core.math.parse('jointLenMultiplier * normalizedMod * j.restLength') >> lockSwitcher.input[0]
        core.math.multiply(
            jointLenMultiplier,
            core.math.multiply( normalizedMod, j.restLength)
        ) >> lockSwitcher.input[0] # >> j.attr('t' + jointAxis)
    
        lockSwitcher.output >> j.attr('t' + jointAxis)
    
    return controller.attr('stretch'), jointLenMultiplier
    

# Spline
def ___addControllers(ctrl):
    jnts = listRelatives(ad=True) + selected()
    for j in jnts:

        g = group(em=1)
        g.setParent(j)
        g.t.set(0, 0, 0)
        core.math.divide( j.rz, -1 ) >> g.rz
        dup = duplicate(ctrl)[0]
        dup.setParent(g)
        dup.t.set(0, 0, 0)


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
    
            
def findDepth(start, end):
    '''
    Find how many joints deep the end is from the start.  This is done in terms
    of overall length so a if end is the child of start, it will return 2, if
    it is a grandchild, 3 etc.
    '''
    depth = 2
    p = end.getParent()
    while p and p != start:
        p = p.getParent()
        depth += 1
        
    if not p:
        raise Exception( end + ' is not a descendent of ' + start  )
        
    return depth


def getIkGroup():
    '''
    DEPRECATED
    Makes, if needed, and returns the group holding ik controls
    '''
    
    for child in node.mainGroup().listRelatives():
        if shortName(child) == 'ikParts':
            return child
    
    return group(em=True, name='ikParts', p=node.mainGroup())


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
    lockRot(g)
    lockScale(g)
    lockTrans(g)
    return g


def parentProxy(target):
    '''
    Makes a group that follows the parent so children of this newly created group
    will behave as children of the target group.
    
    ..  todo::
        Replace with parentGroup, which read better in a hierarchy to know what is going on
    '''
    
    name = target.name() + '_Proxy'
    
    for child in node.mainGroup().listRelatives():
        if shortName(child) == name:
            return child
    
    grp = group( em=True )
    grp.rename( name )
    grp.setParent( node.mainGroup() )
    
    parentConstraint( target, grp, mo=False )
    
    return grp


def transferKeyableUserAttrs( src, dest ):
    '''
    '''
    for attr in src.listAttr( ud=True, k=True ):
        type = attr.get(type=True)
        kwargs = {}
        if type == 'enum':
            kwargs['enumName'] = ':'.join( attr.getEnums().keys() )
        dest.addAttr( attr.plugAttr(), at=type, k=True, **kwargs )
        newAttr = dest.attr( attr.plugAttr() )
        newAttr.set( attr.get() )
        newAttr >> attr
    
        newAttr.setMin( attr.getMin() )
        newAttr.setMax( attr.getMax() )


def squashLinker(name, ctrlA, ctrlB):
    '''
    Name the control that will be made to handle the sizes of two squash controllers.
    '''

    temp = core.dagObj.zero(ctrlA, apply=False, make=False).getParent()
    aTarget = parentConstraint(temp, q=True, tl=True)[0]

    temp = core.dagObj.zero(ctrlB, apply=False, make=False).getParent()
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
    zeroGrp = core.dagObj.zero(ctrl)

    pointConstraint(child, parent, zeroGrp)
    aimConstraint( child, zeroGrp )

    ctrl.ty.lock()
    ctrl.tz.lock()
    lockScale(ctrl)
    lockRot(ctrl)

    exp = ('{child}.size = 1.0 * ((1.0/ ({length}/{total}) )-1.0) + 1.0*{ctrl}.tx;\n' +
          '{parent}.size = 1.0 * ((1.0/ ({length}/{total}) )-1.0) - 1.0*{ctrl}.tx;') \
           .format( child=childCtrl, parent=parentCtrl, ctrl=ctrl, length=lengthCalc, total=total )
        
    print( exp )
        
    expression(s=exp)


def squashDrive(squashCtrl):
    '''
    Given a squash controller, have its size driven by the .tx of the joint it
    is built off of.
    '''

    # Find the bone this controls is built off of.
    zeroGrp = core.dagObj.zero(squashCtrl, make=0, apply=0)
    if not zeroGrp:
        return

    container = zeroGrp.getParent()
    targetBone = parentConstraint(container, q=True, tl=True)
    if not targetBone:
        return

    targetBone = targetBone[0]

    # Build setDrivenKey.
    setDrivenKeyframe( squashCtrl, at=['size'], cd=targetBone.tx )
    length = targetBone.tx.get()
    setDrivenKeyframe( squashCtrl, at=['size'], v=-5.0, cd=targetBone.tx, dv=[length * 2] )
    setDrivenKeyframe( squashCtrl, at=['size'], v=5.0, cd=targetBone.tx, dv=[length * .25] )


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
        core.math.multiply(space.restLength, jointLenMultiplier) >> space.tx
        
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
        core.math.opposite(driver) >> baseRotAttr
        
            
    #ctrl = control.build( trimName(twistDriver) + "Twist", controlSpec['main'], control.ROTATE)

    #ctrl.setParent(space)
    #ctrl.t.set( 0, 0, 0 )
    #ctrl.r.set( 0, 0, 0 )
    #lockScale( ctrl )
    #lockTrans( ctrl )
    #lockRot( ctrl )
    # # Unlock the twist axis
    #ctrl.attr( 'r' + identifyAxis(twist) ).unlock()
    #ctrl.attr( 'r' + identifyAxis(twist) ).setKeyable(True)
    
    # Drive the space's constraint
#    anchorAttr, autoAttr = orientConstraint( constraint, q=1, wal=1 )
#    drive( ctrl, 'AutoTwistPower', autoAttr, minVal=0, maxVal=1, dv=defaultPower )
#    core.math.opposite( ctrl.AutoTwistPower ) >> anchorAttr
#    ctrl.AutoTwistPower.set( defaultPower )
    
    #orientConstraint( ctrl, twist )
    
    #ctrl = nodeApi.RigController.convert(ctrl)
    #ctrl.container = container
    
    #return ctrl, #container


def getBPJoint(realJoint):
    jnt = realJoint.message.listConnections(type=nodeApi.BPJoint)
    if jnt:
        return jnt[0]




#------------------------------------------------------------------------------
# Controls are actually made below here!
#------------------------------------------------------------------------------


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
        core.dagObj.matchTo( ctrl, j )
        space = core.dagObj.zero( ctrl )
        
        if mirroredTranslate:
            space.s.set(-1, -1, -1,)
        
        # If the parent is a twist, make it a child of the most recent non-twist so twists are isolated.
        if top == container or (prevBPJ and not prevBPJ.info.get('twist')):
            space.setParent( top )
        else:
            space.setParent( validCtrl )
        
        top = ctrl
        
        if not translatable:
            lockTrans( ctrl )
            
        if not scalable:
            lockScale( ctrl )
    
        if scalable:
            orient, point, scaleConst = constrainTo( j, ctrl, includeScale=True )
            
            if leadScale:
                leadScale >> scaleConst
            else:
                leadScale = scaleConst
            
        else:
            orient, point = constrainTo( j, ctrl )
                
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
        
    controls[0] = nodeApi.RigController.convert(controls[0])
    controls[0].container = container
    for i, c in enumerate(controls[1:]):
        controls[0].subControl[str(i)] = c
        
    return controls[0], ConstraintResults(leadPoint, leadOrient )


@adds()  # ??? adds
def splineEndTwist(start, end, name):

    container = group(em=True, p=getIkGroup(), n=name + "_controls")
    container.inheritsTransform.set(False)
    container.inheritsTransform.lock()
    
    mainIk, _effector, crv = ikHandle( sol='ikSplineSolver',
        sj=start,
        ee=end,
        ns=1)
        
    controls = addControlsToCurve(crv)
    
    space.addMain( controls[0], mode=space.Mode.ROTATE )
    space.add( controls[0], start.getParent(), mode=space.Mode.ROTATE )
    
    for prev, ctrl in zip( controls[:-1], controls[1:] ):
        space.add( ctrl, prev )
        space.addMain(ctrl)


@adds('AutoTwistPower')
@defaultspec( {'shape': 'disc', 'color': 'blue 0.22', 'size': 5, 'align': 'x'} )
def twist(twist, twistDriver, twistLateralAxis=[0, 1, 0], driverLateralAxis=[0, 1, 0], defaultPower=0.5, controlSpec={}):
    '''
    Twist bone's aim axis = the lateral axis
    Twist Up axis = points to the target (wrist)
    
    World up = object rotation
    up obj = target (wrist)
    up axis = I think this is the target's lateral axis
    
    ..  todo::
        I'm not sure, but it look like a "_L" is sneaking into the name somewhere
    '''
    
    container = parentGroup(twist)
    container.setParent( node.mainGroup() )
    container.rename( trimName(twist) + '_twist' )
    
    anchor = duplicate( twist, po=True )[0]
    aimer = duplicate( twist, po=True )[0]
    space = duplicate( twist, po=True )[0]
    anchor.rename( simpleName(twist, '{0}Anchor') )
    aimer.rename( simpleName(twist, '{0}Aimer') )
    space.rename( simpleName(twist, '{0}Space') )
    space.drawStyle.set(2)
    
    hide(anchor, aimer)
    parent( anchor, aimer, space, container )
    
    constraint = orientConstraint( anchor, aimer, space )
    constraint.interpType.set(2)  # Set to "shortest" because it will flip otherwise.
    
    aimConstraint( twistDriver, aimer, wut='objectrotation', wuo=twistDriver, mo=True,
                    u=identifyAxis(twist, asVector=True),  # noqa e127
                    aimVector=twistLateralAxis,
                    wu=driverLateralAxis,
                )
    
    ctrl = controllerShape.build( trimName(twistDriver) + "Twist", controlSpec['main'], controllerShape.ControlType.ROTATE)

    ctrl.setParent(space)
    ctrl.t.set( 0, 0, 0 )
    ctrl.r.set( 0, 0, 0 )
    lockScale( ctrl )
    lockTrans( ctrl )
    lockRot( ctrl )
    # Unlock the twist axis
    ctrl.attr( 'r' + identifyAxis(twist) ).unlock()
    ctrl.attr( 'r' + identifyAxis(twist) ).setKeyable(True)
    
    # Drive the space's constraint
    anchorAttr, autoAttr = orientConstraint( constraint, q=1, wal=1 )
    drive( ctrl, 'AutoTwistPower', autoAttr, minVal=0, maxVal=1, dv=defaultPower )
    core.math.opposite( ctrl.AutoTwistPower ) >> anchorAttr
    ctrl.AutoTwistPower.set( defaultPower )
    
    orientConstraint( ctrl, twist )
    
    ctrl = nodeApi.RigController.convert(ctrl)
    ctrl.container = container
    
    return ctrl, container


@adds('stretch')
@defaultspec( {'shape': 'box',    'color': 'orange 0.22', 'size': 10 },
     shoulder={'shape': 'box',    'color': 'orange 0.22', 'size': 10 },  # noqa e128
         neck={'shape': 'pin',    'color': 'orange 0.22', 'size': 10, 'align': 'z'} )
def splineChestFourJoint(start, end, name='Chest', groupName='', controlSpec={}):
    '''
    Simplified version of splineChest but with only 3 joints and no mid section.
    '''

    if not name:
        name = trimName(start) + '_Spline'
    container = group( n=name + '_splineChest' )
    container.setParent( node.mainGroup() )
    if start.getParent():
        parentConstraint(start.getParent(), container, mo=True)
   
    chain = getChain( start, end )
        
    controlChain = dupChain(start, end)
    controlChain[0].setParent(container)
    hide(controlChain[0])
    
    constraints = constrainAtoB( chain, controlChain )
    
    # Chest controller
    chestCtrl = controllerShape.build( name, controlSpec['main'], type=controllerShape.ControlType.IK )
    chestCtrl.setParent(container)
    core.dagObj.moveTo( chestCtrl, chain[1] )
    core.dagObj.zero(chestCtrl)
    trueZeroSetup(chain[1], chestCtrl)
    lockScale(chestCtrl)
    
    space.add( chestCtrl, start.getParent(), 'local' )
    space.add( chestCtrl, start.getParent(), 'local_posOnly', mode=space.Mode.TRANSLATE )
    space.addMain( chestCtrl )
    space.addTrueWorld( chestCtrl )
    
    # Main Ik
    mainIk = ikHandle( sol='ikSCsolver', sj=controlChain[0], ee=controlChain[1] )[0]
    hide(mainIk)
    mainIk.setParent( chestCtrl )
    
    # Allow the chain to not stretch
    orientTarget = duplicate( chain[1], po=True )[0]
    orientTarget.setParent(chestCtrl)
    lockTrans(lockScale(orientTarget))
    orientConstraint( orientTarget, controlChain[1] )
    hide(orientTarget)
    
    lockRot(mainIk)
    lockTrans(mainIk)
    lockScale(mainIk)
    
    # Shoulder controller
    chestFollow = group(em=True, n='chestFollow', p=container)
    #parentConstraint(controlChain[1], chestFollow)
    parentConstraint(chestCtrl, chestFollow)
    
    shoulderCtrl = controllerShape.build( name + '_Shoulder', controlSpec['shoulder'], type=controllerShape.ControlType.IK )
    core.dagObj.matchTo(shoulderCtrl, controlChain[-1])
    shoulderCtrl.setParent(chestFollow)
    core.dagObj.zero(shoulderCtrl)
    lockTrans(lockScale(shoulderCtrl))
    
    #lower = ikHandle( sol='ikSCsolver', sj=controlChain[-3], ee=controlChain[-2], n='lowerChest')[0]
    #upper = ikHandle( sol='ikSCsolver', sj=controlChain[-2], ee=controlChain[-1], n='upperChest')[0]
    #lower.setParent(shoulderCtrl)
    #upper.setParent(shoulderCtrl)
    
    chestBaseAim = group(em=True, n='chestBaseAim', p=shoulderCtrl)
    core.dagObj.moveTo(chestBaseAim, controlChain[-2])
    #parentConstraint(shoulderCtrl, chestBaseAim, sr=list('xyz'), mo=True)
    pointConstraint(chestBaseAim, controlChain[-2])
    
    #
    # Neck controller
    neckCtrl = controllerShape.build( name + '_Neck', controlSpec['neck'], type=controllerShape.ControlType.IK )
    core.dagObj.matchTo(neckCtrl, controlChain[-1])
    core.dagObj.zero(neckCtrl).setParent(shoulderCtrl)
    orientConstraint(neckCtrl, controlChain[-1], mo=True)
    pointConstraint(neckCtrl, controlChain[-1])
    
    aimConstraint(chestBaseAim, orientTarget, aim=[1, 0, 0], u=[0, 1, 0], wut='objectrotation', wuo=chestCtrl, mo=True)
    aimConstraint(shoulderCtrl, controlChain[-2], aim=[1, 0, 0], u=[0, 1, 0], wut='objectrotation', wuo=chestCtrl, mo=True)
    
    #makeStretchySpline(chestCtrl, mainIk)
    makeStretchyNonSpline(chestCtrl, mainIk)
    # It's easier to lock and hide to ignore this than not add the length attr at all.
    chestCtrl.length.set(k=False)
    chestCtrl.length.lock()
    
    # Register all the parts of the control for easy identification at other times.
    chestCtrl = nodeApi.RigController.convert(chestCtrl)
    chestCtrl.container = container
    chestCtrl.subControl['neck'] = neckCtrl
    chestCtrl.subControl['shoulders'] = shoulderCtrl
    
    return chestCtrl, constraints


@adds('stretch')
@defaultspec( {'shape': 'box',    'color': 'orange 0.22', 'size': 10 },
         neck={'shape': 'pin',    'color': 'orange 0.22', 'size': 10, 'align': 'z'} )  # noqa e128
def splineChestThreeJoint(start, end, name='Chest', groupName='', controlSpec={}):
    '''
    Simplified version of splineChest but with only 3 joints and no mid section.
    '''

    if not name:
        name = trimName(start) + '_Spline'
    container = group( n=name + '_grpX' )
    container.setParent( node.mainGroup() )
    if start.getParent():
        parentConstraint(start.getParent(), container, mo=True)
   
    chain = getChain( start, end )
        
    controlChain = dupChain(start, end)
    controlChain[0].setParent(container)
    hide(controlChain[0])
    
    constraints = constrainAtoB( chain, controlChain )
    
    # Chest controller
    chestCtrl = controllerShape.build( name, controlSpec['main'], type=controllerShape.ControlType.IK )
    chestCtrl.setParent(container)
    core.dagObj.moveTo( chestCtrl, chain[1] )
    core.dagObj.zero(chestCtrl)
    trueZeroSetup(chain[1], chestCtrl)
    lockScale(chestCtrl)

    space.add( chestCtrl, start.getParent(), 'local' )
    space.add( chestCtrl, start.getParent(), 'local_posOnly', mode=space.Mode.TRANSLATE )
    space.addMain( chestCtrl )
    space.addTrueWorld( chestCtrl )

    # Main Ik
    mainIk = ikHandle( sol='ikSCsolver', sj=controlChain[0], ee=controlChain[1] )[0]
    hide(mainIk)
    mainIk.setParent( chestCtrl )
    
    # Allow the chain to not stretch
    orientTarget = duplicate( chain[1], po=True )[0]
    orientTarget.setParent(chestCtrl)
    lockTrans(lockRot(lockScale(orientTarget)))
    orientConstraint( orientTarget, controlChain[1] )
    hide(orientTarget)
    
    lockRot(mainIk)
    lockTrans(mainIk)
    lockScale(mainIk)
    
    # Neck
    chestFollow = group(em=True, n='chestFollow', p=container)
    neckCtrl = controllerShape.build( name + '_Neck', controlSpec['neck'], type=controllerShape.ControlType.IK )
    core.dagObj.matchTo(neckCtrl, controlChain[-1])
    core.dagObj.zero(neckCtrl).setParent(chestFollow)
    parentConstraint(controlChain[1], chestFollow, mo=True)
    parentConstraint(neckCtrl, controlChain[-1], mo=True)
    lockTrans(lockScale(neckCtrl))
    
    
    makeStretchySpline(chestCtrl, mainIk)
    # It's easier to lock and hide to ignore this than not add the length attr at all.
    chestCtrl.length.set(k=False)
    chestCtrl.length.lock()
    
    # Register all the parts of the control for easy identification at other times.
    chestCtrl = nodeApi.RigController.convert(chestCtrl)
    chestCtrl.container = container
    chestCtrl.subControl['neck'] = neckCtrl
    
    return chestCtrl, constraints


@adds('stretch')
@defaultspec( {'shape': 'box',    'color': 'orange 0.22', 'size': 10 },
       middle={'shape': 'sphere', 'color': 'green  0.22', 'size': 7  },   # noqa e128
          end={'shape': 'box',    'color': 'orange 0.22', 'size': 10 },
         neck={'shape': 'pin',    'color': 'orange 0.22', 'size': 10, 'align': 'z'},)
def splineChest(start, end, name='Chest', numChestJoints=3, useTrueZero=True, groupName='', controlSpec={}):
    '''
    Makes a spline which considers the last 3 joints the "chest/neck".  A chest
    mass is made, with the neck providing a small amount of offset mainly
    affecting that mass.  A mid control is made to adjust the stomach.
    
    ..  todo::
        * Add support for groupName
        * Finish adding ParamInfo support for strings so a specific name can be given
        * Make the number of stomach joints variable but the chest always is always
            3rd from the top
    '''
    srcChain = getChain( start, end )
    
    chain = dupChain( start, end, '{0}_spline' )
    
    chestBase = chain[-numChestJoints]
    chestIndex = len(chain) - numChestJoints
        
    midPoint = chain[1]  # &&& NEED TO FIGURE OUT REAL MID POINT
        
    container = group(em=True, p=node.mainGroup(), n=name + "_controls")
    container.inheritsTransform.set(False)
    container.inheritsTransform.lock()
    chain[0].setParent(container)
    
    mainIk, _effector, crv = ikHandle( sol='ikSplineSolver',
        sj=chain[0],
        ee=chain[-1],
        ns=3,
        simplifyCurve=False)
    
    crvShape = crv.getShape()
    crvShape.overrideEnabled.set(True)
    crvShape.overrideDisplayType.set(2)
    
    parent( mainIk, crv, container )
        
    # -- Base --
    base = joint(None, n='Base')
    core.dagObj.moveTo(base, chain[0])
    base.setParent( container )
    parentConstraint( start.getParent(), base, mo=True)
    hide(base)
        
    # -- Chest control --
    chestCtrl = controllerShape.build( name + '_main', controlSpec['main'], controllerShape.ControlType.SPLINE )
    chestCtrl.setParent(container)
    makeStretchySpline( chestCtrl, mainIk )
    chestCtrl.stretch.set(1)
    chestCtrl.stretch.lock()
    chestCtrl.stretch.setKeyable(False)
    lockScale(chestCtrl)
    space.add( chestCtrl, start.getParent(), 'local' )
    space.add( chestCtrl, start.getParent(), 'local_posOnly', mode=space.Mode.TRANSLATE )
    space.addMain( chestCtrl )
    space.addTrueWorld( chestCtrl )

    # Put pivot point at the bottom
    chestCtrl.ty.set( chestCtrl.boundingBox()[1][1] )
    
    lib.sharedShape.remove(chestCtrl)
    chestCtrl.setPivots( [0, 0, 0], worldSpace=True )
    makeIdentity( chestCtrl, a=True, t=True )
    lib.sharedShape.use(chestCtrl)
    
    move( chestCtrl, xform(chestBase, q=True, ws=True, t=True), rpr=True )
    chestZero = core.dagObj.zero(chestCtrl)
    
    if useTrueZero:
        rot = determineClosestWorldOrient(chestBase)
        
        storeTrueZero(chestCtrl, rot)
        core.dagObj.rezero( chestCtrl )  # Not sure why this is needed but otherwise the translate isn't zeroed
        chestCtrl.r.set( rot )
    
    chest = joint(None, n='Chest')
    chest.setParent( chestCtrl )
    core.dagObj.moveTo(chest, chestBase)
    lockScale(lockRot(lockTrans(chest)))
    hide(chest)

    chestMatcher = createMatcher(chestCtrl, srcChain[chestIndex])
    chestMatcher.setParent(container)
    
    # -- Mid --
    midCtrl = controllerShape.build( name + '_mid', controlSpec['middle'], controllerShape.ControlType.SPLINE )
    core.dagObj.matchTo( midCtrl, midPoint )
    lockScale(midCtrl)
    midCtrl.setParent( container )
    
    mid = joint(None, n='Mid')
    core.dagObj.moveTo( mid, midPoint )
    mid.setParent( midCtrl )
    lockScale(lockRot(lockTrans(mid)))
    hide(mid)
    
    # Mid control's rotation aims at the chest
    core.dagObj.zero(midCtrl)
    
    aimer = midAimer(base, chestCtrl, midCtrl)
    aimer.setParent(container)
    hide(aimer)
    '''
    aimer = group(em=True, name='aimer')
    aimer.setParent(container)
    #aimer = polyCone(axis=[1, 0, 0])[0]
    core.dagObj.moveTo(aimer, midCtrl)
    pointConstraint(chestCtrl, base, aimer, mo=True)
    
    # Determine which axis of the chest control is closest to the midControl's Y axis.
    chestMatrix = xform(chestCtrl, q=True, ws=True, m=True)
    midMatrix = xform(midCtrl, q=True, ws=True, m=True)
    midCtrlYUp = dt.Vector(midMatrix[4:7])
    
    choices = [
        (chestMatrix[4:7], [0, 1, 0]),
        ([-x for x in chestMatrix[4:7]], [0, -1, 0]),
        (chestMatrix[8:11], [0, 0, -1]),
        ([-x for x in chestMatrix[8:11]], [0, 0, 1]),
    ]
    
    low = midCtrlYUp.angle(choices[0][0])
    axis = choices[0][1]
    for vector, destAxis in choices[1:]:
        if midCtrlYUp.angle(vector) < low:
            low = midCtrlYUp.angle(vector)
            axis = destAxis
    
    aimConstraint( chestCtrl, aimer, wut='objectrotation', aim=[1, 0, 0], wuo=chestCtrl, upVector=[0, 1, 0], wu=axis, mo=False)
    '''
    
    space.add(midCtrl, aimer, spaceName='default')

    # -- Shoulders --
    if numChestJoints > 2: # The shoulder control is skipped if there aren't enough joints
        shoulderCtrl = controllerShape.build( name + '_shoulders', controlSpec['end'], controllerShape.ControlType.SPLINE )
        core.dagObj.matchTo( shoulderCtrl, srcChain[-2])  # We want to use the penultimate joint orientation
        core.dagObj.moveTo( shoulderCtrl, end)
        controllerShape.scaleAllCVs( shoulderCtrl, [0.15, 1, 1] )
        shoulderZero = core.dagObj.zero(shoulderCtrl)
        shoulderZero.setParent(chestCtrl)
        lockScale(lockTrans(shoulderCtrl))
    
        neck = joint(None, n='Neck')
        neck.setParent( shoulderCtrl )
        core.dagObj.moveTo( neck, end )
        lockScale(lockRot(lockTrans(neck)))
        hide(neck)
    
    # -- Neck --
    neckCtrl = controllerShape.build( name + '_neck', controlSpec['neck'], controllerShape.ControlType.ROTATE )
    core.dagObj.matchTo( neckCtrl, end)
    if numChestJoints > 2: # The shoulder control is skipped if there aren't enough joints
        core.dagObj.zero(neckCtrl).setParent( shoulderCtrl )
        lockScale(lockTrans(neckCtrl))
        space.add( neckCtrl, srcChain[-2], 'chest' )
        
    else:
        core.dagObj.zero(neckCtrl).setParent( chestCtrl )
        lockScale(lockTrans(neckCtrl))
        space.add( neckCtrl, chestCtrl, 'chest' )
        
    space.addMain(neckCtrl)
    
    # Constrain to spline proxy, up to the chest...
    constraints = []
    for src, dest in zip( chain, srcChain )[:chestIndex]:
        constraints.append( core.constraints.pointConst( src, dest ) )
        constraints.append( core.constraints.orientConst( src, dest ) )
    
    # ... including the chest
    src = chain[chestIndex]
    dest = srcChain[chestIndex]
    if numChestJoints > 2: # The shoulder control is skipped if there aren't enough joints
        constraints.append( core.constraints.pointConst( src, dest ) )
        constraints.append( core.constraints.orientConst( src, dest ) )
    # ... not including the chest
    else:
        chestProxy = duplicate(src, po=True)[0]
        chestProxy.setParent(chestCtrl)
        constraints.append( core.constraints.pointConst( chestProxy, dest ) )
        constraints.append( core.constraints.orientConst( chestProxy, dest ) )
        hide(chestProxy)
        
    constraints.append( core.constraints.pointConst( neckCtrl, srcChain[-1] ) )
    constraints.append( core.constraints.orientConst( neckCtrl, srcChain[-1] ) )
    
    if numChestJoints > 2: # The shoulder control is skipped if there aren't enough joints
        # Make a proxy since we can't constrain with maintainOffset=True if we're making fk too.
        proxy = duplicate(srcChain[-2], po=True)[0]
        proxy.setParent(neck)
        lockTrans(lockRot(lockScale(proxy)))
        
        constraints.append( core.constraints.pointConst( proxy, srcChain[-2] ) )
        constraints.append( core.constraints.orientConst( proxy, srcChain[-2] ) )
    
    hide(chain, mainIk)
    
    # Bind joints to the curve
    if numChestJoints > 2: # The shoulder control is skipped if there aren't enough joints
        skinCluster( crv, base, mid, chest, neck, tsb=True )
    else:
        skinCluster( crv, base, mid, chest, tsb=True )
    
    chestCtrl = nodeApi.RigController.convert(chestCtrl)
    chestCtrl.container = container
    chestCtrl.subControl['mid'] = midCtrl
    if numChestJoints > 2: # The shoulder control is skipped if there aren't enough joints
        chestCtrl.subControl['offset'] = shoulderCtrl
    chestCtrl.subControl['neck'] = neckCtrl
    
    # Setup advanced twist
    startAxis = duplicate( start, po=True )[0]
    startAxis.rename( 'startAxis' )
    startAxis.setParent( base )
    lockTrans(lockRot(lockScale(startAxis)))
    
    endAxis = duplicate( start, po=True )[0]
    endAxis.rename( 'endAxis' )
    endAxis.setParent( chestCtrl )
    endAxis.t.set(0, 0, 0)
    lockTrans(lockRot(lockScale(endAxis)))
    
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


@adds('stretch', 'length')
@defaultspec( {'shape': 'box',    'size': 10, 'color': 'green 0.22' },  # noqa e231
           pv={'shape': 'sphere', 'size': 5,  'color': 'green 0.22' },
       socket={'shape': 'sphere', 'size': 5,  'color': 'green 0.22', 'visGroup': 'socket' } )
def ikChain(start, end, pvLen=None, stretchDefault=1, endOrientType=EndOrient.TRUE_ZERO, name='', groupName='', controlSpec={}):
    '''
    
    :param int pvLen: How far from the center joint to be, defaults to half the length of the chain.
    ..  todo::
        * Have fk build as rotate only if not stretchy
        
    '''
    
    #controlChain = getChain( start, end )
    chain = getChain( start, end )
    
    #if not controlChain:
    #   assert 'Could not make an chain between {0} and {1} because they are not in the same hierarchy'.format( start, end )
    
    controlChain = dupChain(start, end)
    
    out = calcOutVector(controlChain[0], controlChain[1], controlChain[-1])
    
    constraints = constrainAtoB( chain, controlChain )
    '''
    for cc, orig in zip( controlChain, chain ):
        pointConstraint( cc, orig )
        orientConstraint( cc, orig )
    '''
    
    #duplicate(controlChain)
    
    # Main Ik
    mainIk = ikHandle( sol='ikRPsolver', sj=controlChain[0], ee=controlChain[-1] )[0]
    # NOT using Spring because it acts odd.  If the pelvis turns, the poleVectors follow it.
    # Make as RP first so the ik doesn't flip around
    #PyNode('ikSpringSolver').message >> mainIk.ikSolver
    
    hide(mainIk)
    
    if not name:
        name = trimName(start) + '_Ik'
    
    ctrl = controllerShape.build( name, controlSpec['main'], type=controllerShape.ControlType.IK )
    
    container = group( n=name + '_grp' )
    container.setParent( node.mainGroup() )
    
    core.dagObj.moveTo( ctrl, end )
    core.dagObj.zero( ctrl ).setParent( container )
    
    if endOrientType == EndOrient.TRUE_ZERO:
        trueZeroSetup(end, ctrl)
    elif endOrientType == EndOrient.TRUE_ZERO_FOOT:
        trueZeroFloorPlane(end, ctrl)
    elif endOrientType == EndOrient.JOINT:
        core.dagObj.matchTo(ctrl, end)
        
        ctrl.rx.set( shortestAxis(ctrl.rx.get()) )
        ctrl.ry.set( shortestAxis(ctrl.ry.get()) )
        ctrl.rz.set( shortestAxis(ctrl.rz.get()) )
        
        core.dagObj.zero(ctrl)
    elif endOrientType == EndOrient.WORLD:
        # Do nothing, it's built world oriented
        pass
    
    lockScale(ctrl)
    
    mainIk.setParent( ctrl )
    orientTarget = duplicate( end, po=True )[0]
    orientTarget.setParent(ctrl)
    lockTrans(lockRot(lockScale(orientTarget)))
    orientConstraint( orientTarget, controlChain[-1] )
    hide(orientTarget)
    
    lockRot(mainIk)
    lockTrans(mainIk)
    lockScale(mainIk)
        
    # PoleVector
    if not pvLen or pvLen < 0:
        pvLen = chainLength(controlChain) * 0.5
    pvPos = out * pvLen + dt.Vector(xform(controlChain[1], q=True, ws=True, t=True))
    pvCtrl = controllerShape.build( name + '_pv', controlSpec['pv'], type=controllerShape.ControlType.POLEVECTOR )
    
    lockScale(lockRot(pvCtrl))
    xform(pvCtrl, ws=True, t=pvPos)
    controllerShape.connectingLine(pvCtrl, controlChain[1] )
    poleVectorConstraint( pvCtrl, mainIk )
    core.dagObj.zero(pvCtrl).setParent(container)
    
    # Socket offset control
    socketOffset = controllerShape.build( name + '_socket', controlSpec['socket'], type=controllerShape.ControlType.TRANSLATE )
    socketContainer = parentGroup( start )
    socketContainer.setParent( container )
    
    core.dagObj.moveTo( socketOffset, start )
    core.dagObj.zero( socketOffset ).setParent( socketContainer )
    lockRot( socketOffset )
    lockScale( socketOffset )
    pointConstraint( socketOffset, controlChain[0] )
    
    # Reuse the socketOffset container for the controlling chain
    controlChain[0].setParent( socketContainer )
    hide( controlChain[0] )
    
    ''' Currently unable to get this to update, maybe order of operations needs to be enforced?
    # Add switch to reverse the direction of the bend
    reverseAngle = controlChain[1].jointOrient.get()[1] * -1.1
    ctrl.addAttr( 'reverse', at='short', min=0, max=1, dv=0, k=True )
    preferredAngle = core.math.condition( ctrl.reverse, '=', 0, 0, reverseAngle )
    twist = core.math.condition( ctrl.reverse, '=', 0, 0, -180)
    preferredAngle >> controlChain[1].preferredAngleY
    twist >> mainIk.twist
    core.math.condition( mainIk.twist, '!=', 0, 0, 1 ) >> mainIk.twistType # Force updating??
    '''

    makeStretchyNonSpline(ctrl, mainIk, stretchDefault)
    
    # Register all the parts of the control for easy identification at other times.
    ctrl = nodeApi.RigController.convert(ctrl)
    ctrl.container = container
    ctrl.subControl['pv'] = pvCtrl
    ctrl.subControl['socket'] = socketOffset

    # Add default spaces
    space.addMain( pvCtrl )
    #space.add( pvCtrl, ctrl, spaceName=shortName(ctrl, '{0}_posOnly') )
    #space.add( pvCtrl, ctrl, spaceName=shortName(ctrl, '{0}_posOnly'), mode=space.TRANSLATE)
    space.add( pvCtrl, ctrl )
    space.add( pvCtrl, ctrl, mode=space.Mode.TRANSLATE)
    
    return ctrl, constraints


@adds('stretch', 'length')
@defaultspec( {'shape': 'box',    'size': 10, 'color': 'green 0.22' },  # noqa e231
           pv={'shape': 'sphere', 'size': 5,  'color': 'green 0.22' },
       socket={'shape': 'sphere', 'size': 5,  'color': 'green 0.22', 'visGroup': 'socket' } )
def ikChain2(start, end, pvLen=None, stretchDefault=1, endOrientType=EndOrient.TRUE_ZERO, twists={}, makeBendable=False, name='', groupName='', controlSpec={}):
    '''
    
    :param int pvLen: How far from the center joint to be, defaults to half the length of the chain.
    ..  todo::
        * Have fk build as rotate only if not stretchy
    
    :param dict twists: Indicates how many twists each section has, ex {1: 2} means
        joint[1] has 2 twists, which means a 3 joint arm chain becomes
        shoulder, elbow, twist1, twist2, wrist

    '''
    
    chain = getChain( start, end )
    
    # Simplify the names
    controlChain = dupChain(start, end)
    for j, orig in zip(controlChain, chain):
        j.rename( trimName(orig) + '_proxy' )
    
    mainJointCount = len(chain) - sum( twists.values() )
    
    # Take the linear chain and figure out what are the "main ik", and which
    # are the twist joints.  Also parent the mainArmature as a solo chain for ik application.
    mainArmature = []
    subTwists = {}
    cur = 0
    for i in range(mainJointCount):
        mainArmature.append( controlChain[cur] )
        
        if len(mainArmature) > 1:  # Need to reparent so the 'pivot' joints are independent of the twists
        
            if mainArmature[-1].getParent() != mainArmature[-2]: # ... unless this section has no twists and is already parented.
                mainArmature[-1].setParent(mainArmature[-2])
        
        cur += 1
        if i in twists:
            subTwists[ mainArmature[-1] ] = []
            
            for ti in range(twists[i]):
                subTwists[ mainArmature[-1] ].append( controlChain[cur] )
                controlChain[cur].setParent(w=True)  # This ends up being temporary so the ik is applied properly
                cur += 1

    # actual ik node
    mainIk = ikHandle( sol='ikRPsolver', sj=mainArmature[0], ee=mainArmature[-1] )[0]
    # NOT using Spring because it acts odd.  If the pelvis turns, the poleVectors follow it.
    # Make as RP first so the ik doesn't flip around
    #PyNode('ikSpringSolver').message >> mainIk.ikSolver


    # Build the main ik control
    
    hide(mainIk)
    hide(controlChain)
    
    if not name:
        name = trimName(start)
    
    ctrl = controllerShape.build( name + '_Ik', controlSpec['main'], type=controllerShape.ControlType.IK )
    
    container = group( n=name + '_grp' )
    container.setParent( node.mainGroup() )
    
    core.dagObj.moveTo( ctrl, end )
    core.dagObj.zero( ctrl ).setParent( container )

    # Orient the main ik control
    if endOrientType == EndOrient.TRUE_ZERO:
        trueZeroSetup(end, ctrl)
    elif endOrientType == EndOrient.TRUE_ZERO_FOOT:
        trueZeroFloorPlane(end, ctrl)
    elif endOrientType == EndOrient.JOINT:
        core.dagObj.matchTo(ctrl, end)
        
        ctrl.rx.set( shortestAxis(ctrl.rx.get()) )
        ctrl.ry.set( shortestAxis(ctrl.ry.get()) )
        ctrl.rz.set( shortestAxis(ctrl.rz.get()) )
        
        core.dagObj.zero(ctrl)
    elif endOrientType == EndOrient.WORLD:
        # Do nothing, it's built world oriented
        pass
    
    lockScale(ctrl)
    
    mainIk.setParent( ctrl )
    
    # I think orientTarget is for matching fk to ik
    orientTarget = duplicate( end, po=True )[0]
    orientTarget.setParent(ctrl)
    lockTrans(lockRot(lockScale(orientTarget)))
    orientConstraint( orientTarget, mainArmature[-1] )
    hide(orientTarget)
    
    lockRot(mainIk)
    lockTrans(mainIk)
    lockScale(mainIk)


    attr, jointLenMultiplier = makeStretchyNonSpline(ctrl, mainIk, stretchDefault)
    # &&& Need to do the math for all the
    
    # Make the offset joints and setup all the parenting of twists
    subArmature = []
    rotationOffsetCtrls = []
    bendCtrls = []
    for i, j in enumerate(mainArmature[:-1]):  # [:-1] Since last joint can't logically have twists
        if makeBendable:
            j.drawStyle.set(2)  # Probably should make groups but not drawing bones works for now.
        offset = duplicate(j, po=True)[0]
        offset.setParent(j)
        offset.rename( simpleName(j, '{}_Twist') )
        
        #subArmature.append(offset)  ### OLD
        if True: ### NEW
            if not makeBendable:
                subArmature.append(offset)
            else:
                if i == 0:
                    subArmature.append(offset)
                else:
                    offsetCtrl = controllerShape.build('Bend%i' % (len(bendCtrls) + 1),
                        {'shape': 'band', 'size': 10, 'color': 'green 0.22', 'align': 'x' })
                    core.dagObj.matchTo(offsetCtrl, offset)
                    offsetCtrl.setParent(offset)
                    showHidden(offsetCtrl, a=True)
                    subArmature.append(offsetCtrl)
                    bendCtrls.append(offsetCtrl)
                
        
        rotationOffsetCtrls.append(offset)  # &&& Deprectated?
        
        attrName = simpleName(j, '{}_Twist')
        ctrl.addAttr( attrName, at='double', k=True )
        ctrl.attr(attrName) >> offset.rx
        
        if i in twists:
            for subTwist in subTwists[j]:
                subTwist.setParent(j)
                #subArmature.append(subTwist) ### NEW comment out
                
                attrName = simpleName(subTwist)
                ctrl.addAttr( attrName, at='double', k=True )
                ctrl.attr(attrName) >> subTwist.rx
                
                if not makeBendable:
                    subArmature.append(subTwist)
                else:
                    if True: ### NEW
                        offsetCtrl = controllerShape.build('Bend%i' % (len(bendCtrls) + 1),
                            {'shape': 'band', 'size': 10, 'color': 'green 0.22', 'align': 'x' })
                        core.dagObj.matchTo(offsetCtrl, subTwist)
                        offsetCtrl.setParent(subTwist)
                        subTwist.drawStyle.set(2)  # Probably should make groups but not drawing bones works fine for now.
                        showHidden(offsetCtrl, a=True)
                        subArmature.append(offsetCtrl)
                        bendCtrls.append(offsetCtrl)
                
                #offset.rename( simpleName(j, '{0}_0ffset') )
                

    #for mainJoint, (startSegment, endSegment) in zip( mainArmature, zip( rotationOffsetCtrls, rotationOffsetCtrls[1:] + [mainArmature[-1]] )):
    #    if mainJoint in subTwists:
    #        twistSetup(subTwists[mainJoint], startSegment, endSegment)
    
    # Since we don't want twists affecting eachother, base them off the mainArmature
    for startSegment, endSegment in zip( mainArmature, mainArmature[1:] ):
        #print( 'HAS SUB TWISTS', startSegment in subTwists )
        if startSegment in subTwists:
            twistSetup(ctrl, subTwists[startSegment], startSegment, endSegment, jointLenMultiplier)
            
            
    '''
    # Build the groups to hold the twist controls
    groups = []
    for i, (j, nextJ) in enumerate(zip(mainArmature[:-1], mainArmature[1:])):
        g = group(em=True)
        parentConstraint(j, g)
        g.rename( core.dagObj.simpleName(g, '{0}_grp') )
        groups.append(g)

        g.setParent(container)
        
        if j in subTwists:
            
            #totalDist = core.dagObj.distanceBetween(j, nextJ)
            
            for subTwist in subTwists[j]:
                
                dist = core.dagObj.distanceBetween(j, subTwist)
                
                #disc = 'disc'()
                disc = controllerShape.build('Twist', {'shape': 'disc', 'align': 'x', 'size': 3})
                disc.setParent(g)
                disc.t.set( 0, 0, 0 )
                disc.r.set( 0, 0, 0 )
                
                core.dagObj.lockAll(disc)
                disc.rx.unlock()
                disc.tx.unlock()
                
                # Manage the lengths of the twist joints and their controls
                mult = core.math.multiply( dist, jointLenMultiplier)
                mult >> disc.tx
                mult >> subTwist.tx
                
                disc.rx >> subTwist.rx
    '''

    constraints = constrainAtoB( chain, subArmature + [mainArmature[-1]] )
    
        
    # PoleVector
    if not pvLen or pvLen < 0:
        pvLen = chainLength(mainArmature) * 0.5
    out = calcOutVector(mainArmature[0], mainArmature[1], mainArmature[-1])
    pvPos = out * pvLen + dt.Vector(xform(mainArmature[1], q=True, ws=True, t=True))
    pvCtrl = controllerShape.build( name + '_pv', controlSpec['pv'], type=controllerShape.ControlType.POLEVECTOR )
    
    lockScale(lockRot(pvCtrl))
    xform(pvCtrl, ws=True, t=pvPos)
    controllerShape.connectingLine(pvCtrl, mainArmature[1] )
    poleVectorConstraint( pvCtrl, mainIk )
    core.dagObj.zero(pvCtrl).setParent(container)
    
    # Socket offset control
    socketOffset = controllerShape.build( name + '_socket', controlSpec['socket'], type=controllerShape.ControlType.TRANSLATE )
    socketContainer = parentGroup( start )
    socketContainer.setParent( container )
    
    core.dagObj.moveTo( socketOffset, start )
    core.dagObj.zero( socketOffset ).setParent( socketContainer )
    lockRot( socketOffset )
    lockScale( socketOffset )
    pointConstraint( socketOffset, mainArmature[0] )
    
    # Reuse the socketOffset container for the controlling chain
    mainArmature[0].setParent( socketContainer )
#    hide( mainArmature[0] )
    
    ''' Currently unable to get this to update, maybe order of operations needs to be enforced?
    # Add switch to reverse the direction of the bend
    reverseAngle = controlChain[1].jointOrient.get()[1] * -1.1
    ctrl.addAttr( 'reverse', at='short', min=0, max=1, dv=0, k=True )
    preferredAngle = core.math.condition( ctrl.reverse, '=', 0, 0, reverseAngle )
    twist = core.math.condition( ctrl.reverse, '=', 0, 0, -180)
    preferredAngle >> controlChain[1].preferredAngleY
    twist >> mainIk.twist
    core.math.condition( mainIk.twist, '!=', 0, 0, 1 ) >> mainIk.twistType # Force updating??
    '''
    
    if True: # &&& LOCKABLE
        endToMidDist, g1 = core.dagObj.measure(ctrl, pvCtrl, 'end_to_mid')
        startToMidDist, g2 = core.dagObj.measure(socketOffset, pvCtrl, 'start_to_mid')
        parent(endToMidDist, g1, startToMidDist, g2, container)
        
        #ctrl.addAttr( 'lockPV', at='double', min=0.0, dv=0.0, max=1.0, k=True )
        
        #switcher.input[0].set(1)
        
        #print('--'* 20)
        #print(mainArmature)

        for jnt, dist in zip(mainArmature[1:], [startToMidDist, endToMidDist]):
            axis = identifyAxis(jnt)
            lockSwitch = jnt.attr('t' + axis).listConnections(s=True, d=False)[0]
            if jnt.attr('t' + axis).get() < 0:
                core.math.multiply( dist.distance, -1) >> lockSwitch.input[1]
            else:
                dist.distance >> lockSwitch.input[1]
            
            drive(ctrl, 'lockPV', lockSwitch.attributesBlender, 0, 1)
            
        """
        axis = identifyAxis(mainArmature[-1])
        lockSwitchA = mainArmature[-1].attr('t' + axis).listConnections(s=True, d=False)[0]
        if mainArmature[-1].attr('t' + axis).get() < 0:
            core.math.multiply( endToMidDist.distance, -1) >> lockSwitchA.input[1]
        else:
            endToMidDist.distance, -1 >> lockSwitchA.input[1]
        
        lockSwitchB = mainArmature[-2].attr('t' + axis).listConnections(s=True, d=False)[0]
        startToMidDist.distance >> lockSwitchB.input[1]
        #print(lockSwitchA, lockSwitchB, '-'* 20)
        drive(ctrl, 'lockPV', lockSwitchA.attributesBlender, 0, 1)
        drive(ctrl, 'lockPV', lockSwitchB.attributesBlender, 0, 1)
        """
    
    # Register all the parts of the control for easy identification at other times.
    ctrl = nodeApi.RigController.convert(ctrl)
    ctrl.container = container
    ctrl.subControl['pv'] = pvCtrl
    ctrl.subControl['socket'] = socketOffset
    for i, bend in enumerate(bendCtrls):
        ctrl.subControl['bend%i' % i] = bend

    # Add default spaces
    space.addMain( pvCtrl )
    #space.add( pvCtrl, ctrl, spaceName=shortName(ctrl, '{0}_posOnly') )
    #space.add( pvCtrl, ctrl, spaceName=shortName(ctrl, '{0}_posOnly'), mode=space.TRANSLATE)
    space.add( pvCtrl, ctrl )
    space.add( pvCtrl, ctrl, mode=space.Mode.TRANSLATE)
    
    return ctrl, constraints


def midVector(av, bv):
    av = dt.Vector(av)
    bv = dt.Vector(bv)
    
    angle = av.angle(bv)
    axis = av.axis(bv)

    return av.rotateBy(axis, angle/2.0)


def midOrient(a, b):

    aMatrix = xform(a, q=True, ws=True, m=True)
    bMatrix = xform(b, q=True, ws=True, m=True)
    
    xMid = midVector(aMatrix[:3], bMatrix[:3])
    yMid = midVector(aMatrix[4:7], bMatrix[4:7])
    zMid = midVector(aMatrix[8:11], bMatrix[8:11])
    
    return xMid, yMid, zMid


def tempComp(o, a, b):
    x, y, z = midOrient(a, b)
    
    m = xform(o, q=1, ws=1, m=1)
    
    print( x.distanceTo(m[:3]), y.distanceTo(m[4:7], z.distanceTo(m[8:11])) )
    
    
def midOrient2(a, b):

    aMatrix = xform(a, q=True, ws=True, m=True)
    bMatrix = xform(b, q=True, ws=True, m=True)
    
    xMid = midVector(aMatrix[:3], bMatrix[:3]).normal()
    yMid = midVector(aMatrix[4:7], bMatrix[4:7]).normal()
    zMid = xMid.cross(yMid).normal()
    yMid = zMid.cross(xMid).normal()
    return xMid, yMid, zMid

"""
@adds()
@defaultspec( {'shape': 'box',    'size': 10, 'color': 'blue 0.22'} )
def chainedIk(start, end, driveChain, handleInfo, splineOptions={}, controlSpec={}):
    '''
    driveChain will get the spline control to drive the start->end chain.
    
    The start->end chain will get a series daisy chained ik handles that are
    parented into the driveChain.
    
    ..  todo::
        Since I make the spline first, I think I might be able to disable the
        allowOffset as it won't make any difference (I think)
    
    '''
    
    chain = getChain(start, end)
    controlChain = dupChain(start, end)
    constraints = constrainAtoB( chain, controlChain )
    
    #container = parentGroup(joints[0])
    #container.setParent( node.mainGroup() )
    
    chunkStartIndex = 0
    
    if 'controlSpec' in splineOptions:
        del splineOptions['controlSpec']
        
    mainCtrl, _constraints = splineIk(driveChain[0], driveChain[-1], controlSpec=controlSpec, **splineOptions)
    
    for ikJoint, ikParent, pvParent in handleInfo:

        jIndex = chain.index(ikJoint.real)
        chunk = controlChain[chunkStartIndex:jIndex + 1]
        chunkStartIndex = jIndex

        out = calcOutVectorRaw(chunk[0], chunk[1], chunk[-1])
        
        ik = ikHandle( sol='ikRPsolver', sj=chunk[0], ee=chunk[-1] )[0]
        ik.rename( 'ik_' + ikJoint.name() )
        
        # PoleVector
        pvPos = out * chainLength(chunk) / 2.0 + dt.Vector(xform(chunk[1], q=True, ws=True, t=True))
        pv = spaceLocator(n='pv_' + ikJoint.name())
        pv.t.set(pvPos)
        poleVectorConstraint( pv, ik )
        
        pv.setParent(pvParent)
        ik.setParent(ikParent)
        
    hide(driveChain[0], controlChain[0])
    
    driveChain[0].setParent( mainCtrl.container )
    controlChain[0].setParent( mainCtrl.container )
    #mainCtrl = RigController.convert(mainCtrl)
    #mainCtrl.container = container
    
    parentConstraint( mainCtrl, controlChain[0], mo=True)
    
    return mainCtrl, constraints
"""