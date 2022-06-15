from __future__ import absolute_import, division, print_function

import collections
import functools
import json
import math

import maya.OpenMaya

from pymel.core import aimConstraint, addAttr, arclen, cluster, createNode, delete, duplicate, dt, group, hide, ikHandle, \
    orientConstraint, parentConstraint, pointConstraint, PyNode, scaleConstraint, selected, upAxis, warning, xform, MayaAttributeError

try:
    from enum import Enum
except ImportError:
    from pdil.vendor.enum import Enum

import pdil

from .. import log

from .._lib2 import controllerShape
from .. import node
from .._core import config
from .._lib import visNode


ConstraintResults = collections.namedtuple( 'ConstraintResults', 'point orient' )


class EndOrient(Enum):
    TRUE_ZERO = 'True_Zero'             # Matches world but has true zero to return to bind
    JOINT = 'Joint'                     # Match the orient of the last joint (VERIFY this just mean it matches the joint, no true zero)
    TRUE_ZERO_FOOT = 'True_Zero_Foot'   # Same as TRUE_ZERO but only in xz plane
    WORLD = 'World'


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
                visNode.connect(res[0], (tempSpec['main']['visGroup'], 1) )
            
            subControls = res[0].subControl.items()
            if subControls:
                
                # If there is one spec and sub controls, it is a chain so apply the same visgroup
                if len(tempSpec) == 1 and tempSpec['main']['visGroup']:
                    for name, ctrl in subControls:
                        visNode.connect(ctrl, (tempSpec['main']['visGroup'], 1) )
            
                # If there are 2 specs, the non-main is the repeating one
                elif len(tempSpec) == 2:
                    specName = tempSpec.keys()[:].remove('main')
                    visGroup = tempSpec['main']['visGroup']
                    if visGroup:
                        for name, ctrl in subControls:
                            visNode.connect(ctrl, (visGroup, 1) )
                
                # Finally, each additional spec should match a sub control
                else:
                    for specName in tempSpec:
                        if specName == 'main':
                            continue
                        
                        if tempSpec[specName]['visGroup']:
                            try:  # &&& Eventually this needs to not ignore errors
                                visNode.connect(
                                    res[0].subControl[specName],
                                    (tempSpec[specName]['visGroup'], 1)
                                )
                            except Exception:
                                pass
            
            return res
        # Store the default spec so it's easy to access for other things.
        setattr( newFunc, '__defaultSpec__', allSpecs )
        functools.update_wrapper( newFunc, func )
        return newFunc
        
    return realDecorator
    

# Chain stuff -----------------------------------------------------------------

def getChain(start, end):
    '''
    Returns a list of joints from start to end or an empty list if end isn't
    descended from start.
    '''
    
    joints = []
    current = end
    while current and current != start:
        joints.append( current )
        current = current.getParent()
        
    # If we never hit the start, start and end are unrelated.
    if current != start:
        return []
        
    joints.append( start )
    joints.reverse()
    
    return joints


def chainLength(joints):
    return abs(sum( [j.tx.get() for j in joints[1:]] ))
    

def dupChain(start, end, nameFormat='{0}_dup'):
    '''
    Creates a duplicate chain, pruned of all branches and children.  Can handle
    same joints and start and end.
    
    :param string nameFormat: The str.format used on the duped chain
    
    '''
    
    chain = getChain(start, end)
    
    assert chain, '{0} and {1} are not in the same hierarchy, dupChain() failed'.format(start, end)
    
    dup = duplicate(start)[0]
    
    if start != end:
        child = findChild( dup, pdil.simpleName(end) )
        assert child, 'dupChain failed to find duped child {0} in {1}'.format(end, start)
        prune( dup, child )
    else:
        child = dup
    
    dupedChain = getChain( dup, child )
    
    ends = dupedChain[-1].getChildren(type='transform')
    if ends:
        delete(ends)
    
    for src, d in zip(chain, dupedChain):
        dupName = pdil.simpleName(src, nameFormat)
        d.rename(dupName)
    return dupedChain


def chainMeasure(joints):
    ''' Returns plug for percentage distance of total joint length from current rest pos.
    '''
    n = createNode('plusMinusAverage')
    n.operation.set(1)
    
    for i, j in enumerate(joints[1:]):
        j.tx >> n.input1D[i]
    
    totalLength = chainLength(joints)
    if n.output1D.get() < 0:
        totalLength *= -1
    
    return pdil.math.divide( n.output1D, totalLength)


def findChild(chain, target):
    '''
    Given a joint chain, find the child of the target name
    '''
    
    for child in chain.listRelatives(type='joint'):
        if child.name().rsplit('|')[-1] == target:
            return child

    for child in chain.listRelatives(type='joint'):
        t = findChild(child, target)
        if t:
            return t
            
    return None


def prune(start, end, trimEnd=True):
    '''
    Cut the joint chain to just the start and end joints, no branching.
    
    :param bool trimEnd: True by default, removing any children of `end`.
    '''
    p = end.getParent()
    keep = end
    
    if trimEnd:
        ends = end.listRelatives(type='transform')
        if ends:
            delete(ends)
    
    if not end.longName().startswith( start.longName() ):
        raise Exception( "{0} is not a descendant of {1}".format( end, start) )
    
    while True:
        for child in p.listRelatives():
            if child != keep:
                delete(child)
                
        keep = p
        p = p.getParent()
        
        if keep == start:
            return


def constrainTo(constrainee, target, includeScale=False):
    '''
    Point, orient, optionally scale constrains the first to the second, returning
    a list of the controlling plugs.
    '''
    
    o = orientConstraint( target, constrainee, mo=True )
    p = pointConstraint( target, constrainee, mo=True )
    
    if not includeScale:
        return o.getWeightAliasList()[-1], p.getWeightAliasList()[-1]
    else:
        s = scaleConstraint( target, constrainee, mo=True )
        return o.getWeightAliasList()[-1], p.getWeightAliasList()[-1], s.getWeightAliasList()[-1]
        
        
def constrainAtoB(chain, controlChain, mo=True):
    '''
    Point/orient constraint the first chain to the second, driving all their
    weights by the lead joint.
    '''
    points = []
    orients = []
    for _controller, orig in zip( controlChain, chain ):
        points.append( pointConstraint( _controller, orig, mo=mo ).getWeightAliasList()[-1] )
        orients.append( orientConstraint( _controller, orig, mo=mo ).getWeightAliasList()[-1] )
    
    for p in points[1:]:
        points[0] >> p
        
    for o in orients[1:]:
        orients[0] >> o
        
    return ConstraintResults(points[0], orients[0])
        

# True zero stuff -------------------------------------------------------------

def storeTrueZero(obj, rot):
    '''
    True zero puts control's zero state to be world aligned so we have to store
    what the "neutral" pose is.
    '''
    obj.addAttr( 'trueZero', at='double3' )
    
    obj.addAttr( 'trueZeroX', at='double', p='trueZero' )
    obj.addAttr( 'trueZeroY', at='double', p='trueZero' )
    obj.addAttr( 'trueZeroZ', at='double', p='trueZero' )

    obj.trueZero.set( channelBox=True )
    obj.trueZeroX.set( channelBox=abs(rot[0]) > 0.00000000001 )
    obj.trueZeroY.set( channelBox=abs(rot[1]) > 0.00000000001 )
    obj.trueZeroZ.set( channelBox=abs(rot[2]) > 0.00000000001 )
    obj.trueZero.set( rot )
    obj.trueZero.lock()
    obj.trueZeroX.lock()
    obj.trueZeroY.lock()
    obj.trueZeroZ.lock()


def trueZeroSetup(rotationTarget, ctrl):
    '''
    Stores the closest world orient of the rotation target on the given control.

    ..  todo::
        Use this function in all the places where matchOrient exists.
    '''
    rot = determineClosestWorldOrient(rotationTarget)
    ctrl.r.set( rot )
    storeTrueZero(ctrl, rot)
    
    
def trueZeroFloorPlane(rotationTarget, ctrl):
    
    """
    trans = xform(rotationTarget, q=True, ws=True, t=True)
    
    # Make a unit X vector (assume left side is +x, right is -x)
    if trans[0] >= 0:
        tx = dt.Matrix([[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [1.0, 0.0, 0.0, 1.0]])
    else:
        tx = dt.Matrix([[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [-1.0, 0.0, 0.0, 1.0]])
    
    # Move out from the rotator by the unit X vector (in world space)
    altered = tx * rotationTarget.worldMatrix.get()

    # Get the X and Z world position of the new point
    alteredX = altered[3][0]
    alteredZ = altered[3][2]

    # Find the difference in X and Z world positions to calc Y
    
    deltaX = alteredX - trans[0]
    deltaZ = alteredZ - trans[2]

    rad = math.atan2(deltaX, deltaZ)
    degrees = math.degrees(rad)
    """
    degrees = trueWorldFloorAngle(rotationTarget)
    ctrl.ry.set(degrees)
    storeTrueZero(ctrl, [0, degrees, 0])


def trueWorldFloorAngle(obj):
    '''
    Only true for Y up, returns the smallest Y axis worldspace angle needed to
    rotate to be axis aligned.
    
    To rotate the object run `rotate([0, a, 0], r=1, ws=1, fo=True)`
    '''
    m = xform(obj, q=True, ws=True, m=True)

    # The valid axes to check
    rows = (0, 1, 2)
    cols = (2,)

    hirow = rows[0]
    hicol = cols[0]
    highest = m[ hirow * 4 + hicol ]

    for col in cols:
        for row in rows:
            if abs(m[ row * 4 + col]) > abs(highest):
                highest = m[ row * 4 + col]
                hirow = row
                hicol = col
    #print 'col: {}    row: {}   h: {}'.format(hicol, hirow, highest)
    # The `col` determines the world axis
    if hicol == 0:
        worldAxis = dt.Vector([1.0, 0, 0])
    elif hicol == 1:
        worldAxis = dt.Vector([0, 1.0, 0])
    elif hicol == 2:
        worldAxis = dt.Vector([0, 0, 1.0])
    
    # If the highest is negative, flip it; i.e a local axis closely matched -z
    if highest < 0:
        worldAxis *= -1.0
    
    # The `row` determins the local axis
    if hirow == 0:
        localAxis = dt.Vector(m[0], 0, m[2]).normal()
    elif hirow == 1:
        localAxis = dt.Vector(m[4], 0, m[6]).normal()
    elif hirow == 2:
        localAxis = dt.Vector(m[8], 0, m[10]).normal()
        
    a = math.degrees(localAxis.angle(worldAxis))

    # If the cross in negative, flip the angle
    if localAxis.cross(worldAxis).y < 0:
        a *= -1
        
    return a










# Stretchiness ----------------------------------------------------------------


def recordFloat(obj, name, val):
    if not obj.hasAttr(name):
        obj.addAttr( name, at='double' )
        
    obj.attr(name).set(val)


def saveRestLength(j, jointAxis='x'):
    recordFloat(j, 'restLength', j.attr('t' + jointAxis).get() )


def makeStretchySpline(controller, ik, stretchDefault=1):
    start, chain, jointAxis, switcher = _makeStretchyPrep( controller, ik, stretchDefault )
    
    crv = ik.inCurve.listConnections()[0]
    length = arclen(crv, ch=1).arcLength
    lengthMax = arclen(crv, ch=1).arcLength.get()
    # Spline squashes and stretches
    multiplier = pdil.math.divide( length, lengthMax )
    
    jointLenMultiplier = switcher.output
    
    multiplier >> switcher.input[1]
    
    for i, j in enumerate(chain[1:], 1):
        #util.recordFloat(j, 'restLength', j.attr('t' + jointAxis).get() )
        saveRestLength(j, jointAxis)
        pdil.math.multiply( jointLenMultiplier, j.restLength) >> j.attr('t' + jointAxis)
    
    return controller.attr('stretch'), jointLenMultiplier


def _makeStretchyPrep(controller, ik, stretchDefault=1):
    ''' Adds `stretch` and `modAmount` attrs to controller
    '''
    start = ik.startJoint.listConnections()[0]
    end = ik.endEffector.listConnections()[0].tz.listConnections()[0]
    chain = getChain( start, end )
    jointAxis = identifyAxis( end )
    
    switcher = createNode('blendTwoAttr', n='stretchSlider')
    switcher.input[0].set(1)

    drive(controller, 'stretch', switcher.attributesBlender, minVal=0, maxVal=1, dv=max(min(stretchDefault, 1), 0) )
    controller.stretch.set(1)
    
    controller.addAttr('modAmount', at='double', k=False)
    controller.modAmount.set(cb=True)
    chainMeasure(chain) >> controller.modAmount
    
    return start, chain, jointAxis, switcher


def makeStretchyNonSpline(controller, ik, stretchDefault=1):
    ''' Returns (`stretch plug`, `joint length multiplier`, <dict of extra nodes>)

    Extra nodes are the computed lengths driven by the use

    '''
    start, chain, jointAxis, switcher = _makeStretchyPrep( controller, ik, stretchDefault )
    
    length, distNode, grp = pdil.dagObj.measure(start, ik)
    grp.setParent( controller )
    distNode.setParent( ik.getParent() )
    
    lengthMax = chainLength(chain)
    # Regular IK only stretches
    # ratio = (abs distance between start and end) / (length of chain)
    ratio = pdil.math.divide( length, lengthMax )  # lengthMax is a stub, replaced later
    # multiplier is either 1 or a number greater than one needed for the chain to reach the end.
    multiplier = pdil.math.condition( ratio, '>', 1.0, true=ratio, false=1 )
    
    controller.addAttr( 'length', at='double', min=-10.0, dv=0.0, max=10.0, k=True )
    
    '''
    lengthMod is the below formula:
    
    if controller.length >= 0:
        controller.length/10.0 + 1.0   # 1.0 to 2.0 double the length of the limb
    else:
        controller.length/20.0  + 1.0   # .5 to 1.0 halve the length of the limb
    '''
    lengthMod = pdil.math.add(
        pdil.math.divide(
            controller.length,
            pdil.math.condition(controller.length, '>=', 0, 10.0, 20.0)
        ),
        1.0
    )
    
    jointLenMultiplier = pdil.math.multiply(switcher.output, lengthMod)
    
    multiplier >> switcher.input[1]
    
    nodes = {'overallLength': lengthMod, 'distToController': length}
    
    for i, j in enumerate(chain[1:], 1):
        saveRestLength(j, jointAxis)
        #util.recordFloat(j, 'restLength', j.attr('t' + jointAxis).get() )
            
        # Make an attribute that is -10 to 10 map to multiplying the restLength by 0 to 2
        attrName = 'segLen' + str(i)
        controller.addAttr( attrName, at='double', k=True, min=-10, max=10 )
        normalizedMod = pdil.math.add(pdil.math.divide( controller.attr(attrName), 10), 1)
        
        "j.attr('t' + jointAxis) = lockSwitcher.output = jointLenMultiplier * normalizedMod * j.restLength"
        
        # As of 2/9/2019 it looks to be fine to make this even if it's not used by the ik to lock the elbow (like in dogleg)
        lockSwitcher = createNode('blendTwoAttr', n='lockSwitcher')
        
        computedLength = pdil.math.multiply( normalizedMod, j.restLength)
        
        pdil.math.multiply(
            jointLenMultiplier,
            computedLength
        ) >> lockSwitcher.input[0] # >> j.attr('t' + jointAxis)
    
        lockSwitcher.output >> j.attr('t' + jointAxis)
        
        nodes['computedLength%i' % i] = computedLength
    
    computedTotalUnscaled = createNode('plusMinusAverage')
    computedTotalUnscaled.operation.set( 1 )
    for i in range( len(chain) - 1 ):
        nodes['computedLength%i' % (i + 1)] >> computedTotalUnscaled.input1D[i]
        
    computedTotalScaled = pdil.math.multiply(computedTotalUnscaled.output1D, lengthMod)
    
    if computedTotalScaled.get() < 0: # Handle -x side
        computedTotalScaled = pdil.math.multiply( computedTotalScaled, -1.0 )
    
    # Replaces lengthMax with computed length (segLen# * length)
    computedTotalScaled >> ratio.node().input2X
    
    nodes['computedTotalScaled'] = computedTotalScaled
    
    return controller.attr('stretch'), jointLenMultiplier, nodes


# IK / Spline stuff -----------------------

def ikRP(name, start, end):
    node = ikHandle( sol='ikRPsolver', sj=start, ee=end)[0]
    node.rename(name)
    hide(node)
    return node


def advancedTwist(start, end, baseCtrl, endCtrl, ik):
    # Setup advanced twist
    startAxis = duplicate( start, po=True )[0]
    startAxis.rename( 'startAxis' )
    startAxis.setParent( baseCtrl )
    pdil.dagObj.lock(startAxis)
    
    endAxis = duplicate( start, po=True )[0]
    endAxis.rename( 'endAxis' )
    endAxis.setParent( endCtrl )
    endAxis.t.set(0, 0, 0)
    pdil.dagObj.lock(endAxis)
    
    hide(startAxis, endAxis)
    
    ik.dTwistControlEnable.set(1)
    ik.dWorldUpType.set(4)
    startAxis.worldMatrix[0] >> ik.dWorldUpMatrix
    endAxis.worldMatrix[0] >> ik.dWorldUpMatrixEnd


def midAimer(start, end, midCtrl, name='aimer', upVector=None):
    '''
    Creates an object point contrained to two others, aiming at the second.  Up
    vector defaults to the control's Y.
    '''
    aimer = group(em=True, name=name)
    #aimer.setParent(container)
    #aimer = polyCone(axis=[1, 0, 0])[0]
    pdil.dagObj.moveTo(aimer, midCtrl)
    pointConstraint(end, start, aimer, mo=True)
    
    
    aimV = dt.Vector(xform(end, q=True, ws=True, t=True)) - dt.Vector( xform(aimer, q=1, ws=1, t=1) )
    aimV.normalize()
    
    if upVector:
        midCtrlYUp = upVector
    else:
        temp = xform(midCtrl, q=True, ws=True, m=True)
        midCtrlYUp = dt.Vector( temp[4:7] )
    
    """
    # Generally the X axis is a good default up since things are normally  on that plane
    if abs(aimV[0]) < 0.0001 or min([abs(v) for v in aimV]) == abs(aimV[0]):
        upV = dt.Vector([-1, 0, 0])
        forwardV = aimV.cross(upV)
        recalcUp = forwardV.cross(aimV)
        
        # Reference
        #xrow = aimV
        #yrow = recalcUp
        #zrow = forwardV
        midCtrlYUp = recalcUp
        print( 'midCtrlYUp', midCtrlYUp )
    else:
        # Choose Y up as the up (hopefully this works)
        if abs(aimV[1]) < abs(aimV[0]) and abs(aimV[1]) < abs(aimV[2]):
            upV = dt.Vector([0, 1, 0])
            forwardV = aimV.cross(upV)
            recalcUp = forwardV.cross(aimV)
            
            # Reference
            #xrow = aimV
            #yrow = recalcUp
            #zrow = forwardV
            midCtrlYUp = recalcUp
            pass
    #
    """
    
    # Determine which axis of the end is closest to the midControl's Y axis.
    endMatrix = xform(end, q=True, ws=True, m=True)
    #midMatrix = xform(aimer, q=True, ws=True, m=True)
    #midCtrlYUp = dt.Vector(midMatrix[4:7])
    
    choices = [
        (endMatrix[:3], [1, 0, 0]),
        ([-x for x in endMatrix[:3]], [-1, 0, 0]),
        (endMatrix[4:7], [0, 1, 0]),
        ([-x for x in endMatrix[4:7]], [0, -1, 0]),
        (endMatrix[8:11], [0, 0, -1]),
        ([-x for x in endMatrix[8:11]], [0, 0, 1]),
    ]
    
    # Seed with the first choice as the best...
    low = midCtrlYUp.angle(dt.Vector(choices[0][0]))
    axis = choices[0][1]
    # ... and see if any others are better
    for vector, destAxis in choices[1:]:
        vector = dt.Vector(vector)  # Just passing 3 numbers sometimes gets a math error.
        
        if midCtrlYUp.angle(vector) < low:
            low = midCtrlYUp.angle(vector)
            axis = destAxis
    
    aimConstraint( end, aimer, wut='objectrotation', aim=[1, 0, 0], wuo=end, upVector=[0, 1, 0], wu=axis, mo=False)
    
    return aimer


_45_DEGREES = math.radians(45)


def slerp(start, end, percent):

    dot = start.dot(end)
    
    theta = math.acos(dot) * percent # angle between * percent

    relativeVec = end - start * dot
    relativeVec.normalize()
    
    return ((start * math.cos(theta)) + (relativeVec * math.sin(theta)))

    
def calcOutVector(start, middle, end):
    '''
    Given the lead joint of 3 (or dt.Vectors), determine the vector pointing directly away along the xz plane.
    
    ..  todo::
        Gracefully handle if the ik is on the xz plane already.
    '''
    
    s = dt.Vector( xform(start, q=1, ws=1, t=1) ) if isinstance( start, PyNode) else start
    m = dt.Vector( xform(middle, q=1, ws=1, t=1) ) if isinstance( middle, PyNode) else middle
    e = dt.Vector( xform(end, q=1, ws=1, t=1) ) if isinstance( end, PyNode) else end
    
    up = s - e
    
    if upAxis(q=True, ax=True) == 'y':
        kneeScale = ( m.y - e.y ) / up.y if up.y else 0.0
    else:
        kneeScale = ( m.z - e.z ) / up.z if up.z else 0.0
    
    modifiedUp = kneeScale * up
    newPos = modifiedUp + e
    
    outFromKnee = m - newPos
    outFromKnee.normalize()
    
    # If we are halfway to the x/z plane, lerp between the old formula and a new one
    testUp = dt.Vector(up)
    if testUp.y < 0:
        testUp.y *= -1.0
        
    angleToVertical = dt.Vector( 0, 1, 0 ).angle( testUp )
    
    if angleToVertical > _45_DEGREES:
        # Calculate a point perpendicular to the line created by the start and end
        # going through the middle
        theta = up.angle( m - e )
        
        distToMidpoint = math.cos(theta) * (m - e).length()
        
        midPoint = distToMidpoint * up.normal() + e
        
        altOutFromKnee = m - midPoint
        
        altOutFromKnee.normalize()
    
        # lerp between the vectors
        percent = (angleToVertical - _45_DEGREES) / _45_DEGREES # 45 to up axis will favor old, on y axis favors new
        outFromKnee = slerp(outFromKnee, altOutFromKnee, percent)
    
    
    angleBetween = (m - s).angle( e - m )
    
    log.TooStraight.check(angleBetween)
    
    
    outFromKnee.normalize()
    
    return outFromKnee
    

# Ik/Fk Switching -----------------------

def getChainFromIk(ikHandle):
    '''
    Given an ikHandle, return a chain of the joints affected by it.
    '''
    start = ikHandle.startJoint.listConnections()[0]
    endEffector = ikHandle.endEffector.listConnections()[0]
    end = endEffector.tx.listConnections()[0]

    chain = getChain(start, end)
    return chain


def getConstraineeChain(chain):
    '''
    If the given chain has another rotate constrained to it, return it
    '''
    boundJoints = []
    for j in chain:
        temp = pdil.constraints.getOrientConstrainee(j)
        if temp:
            boundJoints.append(temp)
        else:
            break

    return boundJoints


def createMatcher(ctrl, target):
    '''
    Creates an object that follows target, based on ctrl so ctrl can match it
    easily.
    '''
    matcher = duplicate(ctrl, po=True)[0]
    parentConstraint( target, matcher, mo=True )

    matcher.rename( ctrl.name() + '_matcher' )
    hide(matcher)

    if not ctrl.hasAttr( 'matcher' ):
        ctrl.addAttr('matcher', at='message')

    matcher.message >> ctrl.matcher
    
    if matcher.hasAttr('fossilCtrlType'):
        matcher.deleteAttr( 'fossilCtrlType' )
    
    return matcher


def getMatcher(ctrl):
    try:
        matcher = ctrl.matcher.listConnections()[0]
        return matcher
    except Exception:
        warning('{0} does not have a matcher setup'.format(ctrl))


def alignToMatcher(ctrl):
    try:
        matcher = getMatcher(ctrl)
        xform( ctrl, ws=True, t=xform(matcher, q=True, ws=True, t=True) )
        xform( ctrl, ws=True, ro=xform(matcher, q=True, ws=True, ro=True) )
    except Exception:
        warning('{0} does not have a matcher setup'.format(ctrl))


def angleBetween( a, mid, c ):
    ''' Give 3 points, return the angle (degrees) and axis between the vectors.
    '''
    aPos = dt.Vector(xform(a, q=True, ws=True, t=True))
    midPos = dt.Vector(xform(mid, q=True, ws=True, t=True))
    cPos = dt.Vector(xform(c, q=True, ws=True, t=True))

    aLine = midPos - aPos
    bLine = midPos - cPos

    aLine.normalize()
    bLine.normalize()

    axis = aLine.cross(bLine)

    if axis.length() > 0.01:
        return math.degrees(math.acos(aLine.dot(bLine))), axis
    else:
        return 0, axis


def worldInfo(obj):
    return [xform(obj, q=True, ws=True, t=True), xform(obj, q=True, ws=True, ro=True)]


def applyWorldInfo(obj, info):
    xform(obj, ws=True, t=info[0])
    xform(obj, ws=True, ro=info[1])


# -----------------------

def jsonGet(obj, attrName):
    try:
        return json.loads(obj.attr(attrName).get(), object_pairs_hook=collections.OrderedDict)
    except MayaAttributeError:
        return {}


def parentGroup(target):
    '''
    Returns a group that is constrained to the parent of the target.
    Used to allow control hierarchies to live elsewhere.
    
    ..  todo::
        Get rid of parentProxy, which is dumb
    '''
    
    name = pdil.simpleName(target, '{0}_Proxy' )
    grp = group( em=True, name=name )

    info = jsonGet(target, 'fossilAccessoryInfo')

    if info.get('parent'):
        parentConstraint( info['parent'], grp, mo=False )

    # Don't constrain top level nodes since they need to follow main, not b_Root
    elif target.getParent() != node.getTrueRoot():
        parentConstraint( target.getParent(), grp, mo=False )

    return grp


def trimName(jnt):
    '''
    Given an joint, return its simple name without b_ or rig_ if those prefixes exist.
    '''
    name = pdil.simpleName(jnt)
    prefix = config._settings['joint_prefix']
    if name.startswith( prefix ):
        return name[ len(prefix): ]
    
    return name

    
def drive(control, attr, driven, minVal=None, maxVal=None, asInt=False, dv=None, flipped=False):
    '''
    Add the attr to the control and feed it into driven.
    '''
    
    attrType = 'short' if asInt else 'double'
    
    if not control.hasAttr( attr ):
        control.addAttr( attr, at=attrType, k=True )
        if minVal is not None:
            control.attr( attr ).setMin(minVal)
        if maxVal is not None:
            control.attr( attr ).setMax(maxVal)
        
        if dv is not None:
            defaultVal = dv
            if maxVal is not None:
                defaultVal = min(defaultVal, maxVal)
            if minVal is not None:
                defaultVal = max(defaultVal, minVal)
            addAttr(control.attr(attr), e=True, dv=dv)
            
    if flipped:
        pdil.math.multiply(control.attr(attr), -1) >> driven
    else:
        control.attr(attr) >> driven
    
    return control.attr(attr)
    
    
def shortestAxis(srcAngle):
    angle = abs(srcAngle) % 90
    
    if angle >= 89.99999:  # Due to float error, allow for some negligible slop to align the axis
        angle -= 90
    
    return math.copysign(angle, srcAngle)

    
def determineClosestWorldOrient(obj):
    '''
    Given an object, returns the shortest rotation that aligns the object with
    the world.  This is used to allow IK elements to have world alignment but
    easily return to the bind pose.
    '''

    ''' # This is essentially a math version of the following:
        x = spaceLocator()
        y = spaceLocator()
        pdil.dagObj.moveTo( x, obj )
        pdil.dagObj.moveTo( y, obj )
        x.tx.set( 1 + x.tx.get() )
        y.ty.set( 1 + y.ty.get() )
        x.setParent(obj)
        y.setParent(obj)
        
        def zeroSmaller(loc):
            vals = [abs(v) for v in loc.t.get() ]
            largetVal = max(vals)
            index = vals.index(largetVal)
            for i, attr in enumerate('xyz'):
                if i == index:
                    continue
                loc.attr( 't' + attr ).set(0)
        
        zeroSmaller( x )
        zeroSmaller( y )
        
        ref = spaceLocator()
        pdil.dagObj.moveTo( ref, obj )
        aimConstraint( x, ref, wut='object', wuo=y )
        
        rot = ref.r.get()
        delete( x, y, ref )
        return rot
    '''

    # Make 2 world spaced points one unit along x and y
    x = dt.Matrix( [ (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0), (1, 0, 0, 0) ] )
    y = dt.Matrix( [ (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0), (0, 1, 0, 0) ] )
    #z = dt.Matrix( [ (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0), (0, 0, 1, 0,) ] )
    
    world = obj.worldMatrix.get()
    inv = world.inverse()

    # Find the local matrices respective of the obj
    localX = x * inv
    localY = y * inv
    
    # For X, zero out the two smaller axes for each, ex t=.2, .3, .8 -> t=0, 0, .8
    def useX(matrix):
        return dt.Matrix( [matrix[0], matrix[1], matrix[2], [matrix[3][0], 0, 0, matrix[3][3]]] )
    
    def useY(matrix):
        return dt.Matrix( [matrix[0], matrix[1], matrix[2], [0, matrix[3][1], 0, matrix[3][3]]] )
        
    def useZ(matrix):
        return dt.Matrix( [matrix[0], matrix[1], matrix[2], [0, 0, matrix[3][2], matrix[3][3]]] )
    
    xUsed, yUsed, zUsed = [False] * 3
    if abs(localX[3][0]) > abs(localX[3][1]) and abs(localX[3][0]) > abs(localX[3][2]):
        localX = useX(localX)
        xUsed = True
    elif abs(localX[3][1]) > abs(localX[3][0]) and abs(localX[3][1]) > abs(localX[3][2]):
        localX = useY(localX)
        yUsed = True
    else:
        localX = useZ(localX)
        zUsed = True

    # Do the same for Y
    if xUsed:
        if abs(localY[3][1]) > abs(localY[3][2]):
            localY = useY(localY)
            yUsed = True
        else:
            localY = useZ(localY)
            zUsed = True
    
    elif yUsed:
        if abs(localY[3][0]) > abs(localY[3][2]):
            localY = useX(localY)
            xUsed = True
        else:
            localY = useZ(localY)
            zUsed = True
    
    elif zUsed:
        if abs(localY[3][0]) > abs(localY[3][1]):
            localY = useX(localX)
            xUsed = True
        else:
            localY = useY(localY)
            yUsed = True
    
    # Find the 'world' (but treating the obj's pos as the origin) positions.
    worldX = localX * world
    worldY = localY * world
    
    # Convert this into a rotation matrix by mimicing an aim constraint
    x = dt.Vector(worldX[-1][:-1])
    y = dt.Vector(worldY[-1][:-1])

    x.normalize()
    y.normalize()
    z = x.cross(y)
    y = z.cross(x)

    msutil = maya.OpenMaya.MScriptUtil()
    mat = maya.OpenMaya.MMatrix()
    msutil.createMatrixFromList([
        x[0], x[1], x[2], 0.0,
        y[0], y[1], y[2], 0.0,
        z[0], z[1], z[2], 0.0,
        0.0, 0.0, 0.0, 1.0
        ], mat) # noqa e123
    rot = maya.OpenMaya.MEulerRotation.decompose(mat, maya.OpenMaya.MEulerRotation.kXYZ)

    return dt.Vector(math.degrees( rot.x), math.degrees(rot.y), math.degrees(rot.z))
    

def identifyAxis(jnt, asVector=False):
    '''
    Determines the primary axis of the joint in relation to its parent,
    returning 'x', 'y' or 'z' or the appropriate vector if asVector is True.
    '''
        
    jointAxis = max( zip( [abs(n) for n in jnt.t.get()], 'xyz' ) )[1]
    
    if asVector:
        jointAxis = {'x': [1, 0, 0], 'y': [0, 1, 0], 'z': [0, 0, 1]}[jointAxis]
        
    return jointAxis
    
    
def driveConstraints(srcConstraintResult, destConstraintResult):
    '''
    Have the destConstraintResult controlled by the source.
    
    Intended use is for chains where some joints, likely the tip, are constrained
    to the controller instead of the drive chain
    '''
    
    srcConstraintResult.point >> destConstraintResult.point
    srcConstraintResult.orient >> destConstraintResult.orient

    
def addControlsToCurve(name, crv=None,
    spec={'shape': 'sphere', 'size': 10, 'color': 'blue 0.22'} ):  # noqa e128
    '''
    Given a curve, make a control sphere at each CV.
    
    :return: List of newly made controls.
    '''
    if not crv:
        crv = selected()[0]

    controls = []
        
    for i, cv in enumerate(crv.cv):
        #l = control.sphere( '{0}{1:0>2}'.format( name, i+1), size, 'blue', type=control.SPLINE )
        shape = controllerShape.build('{0}{1:0>2}'.format(name, i + 1), spec, type=controllerShape.ControlType.SPLINE)
        
        pdil.dagObj.moveTo( shape, cv )
        handle = cluster(cv)[1]
        handle.setParent(shape)
        hide(handle)
        controls.append(shape)

    return controls


def registerRigNode(leadControl, node, name):
    ''' Connects `node` to `leadControl`, tagged as `name` so interals (like spaces) can easily be restored.
    
    Some controls make custom setups for spaces and this ensurce they get saved
    a restorable way.  This also can be used to expose internal calculations to
    easily restore (ex, automation based on stretched distance).
    '''
    
    node.addAttr('fossilNodeLink', at='message')
    pdil.factory.setJsonAttr(node, 'fossilNodeData', {'name': name})
    
    leadControl.message >> node.fossilNodeLink