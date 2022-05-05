from __future__ import absolute_import, division, print_function

try:
    basestring
except NameError:
    basestring = str

from collections import OrderedDict
from copy import deepcopy
import inspect
import math
import operator
import re

from pymel.core import dt, move, PyNode, rotate, xform

import pdil

from ..._core import find
from ..._core import ids
from .tpcore import getRCard, getRJoint


# All the registered adjustement commands
if 'adjustCommands' not in globals():
    adjustCommands = {}


# If an adjustment command can take a joint from another card, that arg is listed here.
# Ex: _anyJoint['pelvisAlign' = ['referenceJoint']
if '_anyJoint' not in globals():
    _anyJoint = {}



def optionalKwargs(in_decorator):
    ''' Convenience to make a decorator optionally with arguements.
    '''
    
    def wrapped_decorator(func=None, name='', anyJoint=()):
        '''
        Will get only the actual target decoratee as `func` when called with no args.
        If in_decorator has kwargs, it returns the 'real' decorator.
        '''        
        if func:
            return in_decorator(func)
        else:
            def decorator_with_args(func):
                return in_decorator(func, name=name, anyJoint=anyJoint)
            return decorator_with_args

    return wrapped_decorator


@optionalKwargs
def registerAdjuster(func, name='', anyJoint=()):
    ''' `name` can be used to specify a different name stored in the adjuster
    `anyJoint` is a list of the args that can be any joint, not just those on the card
    '''
    global adjustCommands
    global _anyJoint
    
    name = name if name else func.__name__
    
    spec = inspect.getargspec(func)
    
    assert 1 <= len(spec.args) <= 4, ('TPose adjust function {} must have 1-4 args, the first being that card'.format(func) )
    
    # &&& TODO, validate first arg has 'Card', and th
    _anyJoint[name] = anyJoint[:]
    
    for argName in anyJoint:
        assert argName in spec.args, 'TPose adjust function {} specifies an `anyJoint` {} that is not an arguement'.format(func, argName)
    
    adjustCommands[name] = func
    return func


def getCardParent(rJoint):
    ''' Returns the parent reposeCard, skipping the auto-created 'transform#' that Maya adds.
    
    When ancestors are scaled, they can create intermediate transforms that need
    to be ignored.
    '''
    p = rJoint.getParent()
    if p.hasAttr('bpCard'):
        return p
    else:
        return p.getParent()


@registerAdjuster
def armAlign(shoulderCard, angle=2.0):
    ''' Rotates the lead joint to point down the +X axis, and the other joints
    to be almost straight, with a slight bend pointing behind, -Z.

    angle: In degrees, how much it is bent from +X axis

    MUST have a parent joint to rotate properly
    ASSUMES elbow already points backwards
    ASSUMES 3 joint humaniod arm
    '''
    shoulderJoint = shoulderCard.joints[0]
    
    shoulderRepose = getRJoint(shoulderJoint)
    
    xform( getCardParent(shoulderRepose), ws=True, ro=[0, 0, 90] )
    
    out = pdil.dagObj.getPos( getRJoint(shoulderCard.joints[1]) ) - pdil.dagObj.getPos( getRJoint(shoulderCard.joints[0]) )
    toRotate = math.degrees( out.angle( (1, 0, 0) ) )
    rotate(shoulderRepose, [0, -toRotate + angle, 0 ], ws=True, r=True) # &&& Assumption is that -toRotate will align with +X axis, then offest by `angle`
    
    elbowRepose = getRJoint(shoulderCard.joints[1])
    out = pdil.dagObj.getPos( getRJoint(shoulderCard.joints[2]) ) - pdil.dagObj.getPos( getRJoint(shoulderCard.joints[1]) )
    toRotate = math.degrees( out.angle( (1, 0, 0) ) )
    rotate(elbowRepose, [0, toRotate - angle, 0 ], ws=True, r=True)


@registerAdjuster
def wristAlign(_card, wristJoint ):
    '''
    Assumptions, aiming down +x, MUST have orientTarget set, CANNOT already be at 90
    '''
    rotatingJoint = getRJoint(wristJoint)
    rotatingJoint.ry.unlock()
    rotatingJoint.rz.unlock()
    
    targetJoint = getRJoint( wristJoint.orientTarget )
    targetCard = getCardParent(targetJoint)

    aim = pdil.dagObj.getPos(targetJoint) - pdil.dagObj.getPos(rotatingJoint)

    rotate(rotatingJoint, [0, math.degrees( math.atan( aim.z / aim.x ) ), 0], ws=True, r=True )

    rotate(rotatingJoint, [0, 0, -math.degrees(math.atan(aim.y / aim.x))], ws=True, r=True )

    m = xform(targetCard, q=True, ws=True, m=True)
    rotate(rotatingJoint, [ -math.degrees( math.atan( m[2] / m[1] ) )  ], ws=True, r=True)

    
"""
@registerAdjuster
def legBasicAlign(legCard):
    '''
    Sets card vertical.
    '''
    xform( getCardParent(getRJoint(legCard.joints[0])), ws=True, ro=[0, 0, 0] )
"""


@registerAdjuster
def legAlign(legCard):
    ''' Maintains the z postion of the end joint while putting it into the YZ plane.
    '''
    
    rCard = getCardParent(getRJoint(legCard.joints[0]))
    start = getRJoint( legCard.joints[0] )
    end = getRJoint( legCard.end() )
    
    ''' We need to preserve the z position of the end joint,
    so use that z component, but the out vector length doesn't change.
    '''
    
    out = pdil.dagObj.getPos(end) - pdil.dagObj.getPos(start)
    
    desiredAngleFromVertical = math.asin( out.z / out.length() )
        
    ''' Then zero the rotations, and do the same calculations to see how off it is.
    '''
    xform(rCard, ws=True, ro=[0, 0, 0])
    
    planeStartPos = pdil.dagObj.getPos( start )
    planeEndPos = pdil.dagObj.getPos( end )

    planeOut = planeEndPos  - planeStartPos
    currentAngleFromVertical = math.asin( planeOut.z / planeOut.length() )
    
    #-
    xRot = math.degrees(desiredAngleFromVertical - currentAngleFromVertical)
    
    xRot = math.copysign(xRot, planeOut.cross(out).x)

    rotate(rCard, [xRot, 0, 0], ws=True, r=True)
    


@registerAdjuster
def footAlign(_card, ankleJoint ):
    ''' Put on the any card (leg or foot makes sense) to aim the ankle joint down Z
    
    Not a great system.
    
    Aims the given joint down z?
    Assumptions, aim down +Z
    REQUIRES ORIENT TARGET
    '''
    rotatingJoint = getRJoint(ankleJoint)
    rotatingJoint.ry.unlock()
    rotatingJoint.rz.unlock()
    
    orientState = ankleJoint.getOrientState()
    targetJoint = getRJoint( orientState.joint )
    targetCard = getCardParent(targetJoint)
    
    aim = pdil.dagObj.getPos(targetJoint) - pdil.dagObj.getPos(rotatingJoint)
    
    # Aim the ankleJoint down +Z
    rotate(rotatingJoint, [0, -math.degrees(math.atan2( aim.x, aim.z )), 0], ws=True, r=True )
    
    # Tilt the ankleJoint on X to aim flat along the X-Z plane
    rotate(rotatingJoint, [math.degrees(math.atan2(aim.y, aim.z)), 0, 0], ws=True, r=True )
    
    # Use x-basis to roll around Z axis to be flat
    m = xform(targetCard, q=True, ws=True, m=True)
    rotate(rotatingJoint, [0, 0, -math.degrees( math.atan2( m[1], m[0] ) )], ws=True, r=True)

    
@registerAdjuster
def fingerAlign(_card, baseJoint ):
    ''' Points joints directly down +X with up vector along -Z
    '''
    
    fingerCardRepose = getCardParent(getRJoint(baseJoint))
    
    xform( fingerCardRepose, ws=True, ro=[90, 90, 180] )
    
    reposes = [getRJoint(j) for j in baseJoint.card.joints]
    
    for jointA, jointB in zip(reposes, reposes[1:]):
        bPos = pdil.dagObj.getPos( jointB )
        aPos = pdil.dagObj.getPos( jointA )
        out = bPos - aPos
        toRotate = math.degrees( out.angle( (1, 0, 0) ) )
        
        if aPos.y < bPos.y:
            toRotate *= -1
        
        rotate(jointA, [0, 0, toRotate ], ws=True, r=True)

    
@registerAdjuster(anyJoint=['referenceJoint'])
def pelvisAlign( pelvisCard, referenceJoint ):
    ''' Adjusts the height by how much the reference joint moves in the repose.
    
    Commonly on the pelvis, with toe as referenceJoint.  When the legs are straighted, this will raise
    the repose to maintain floor contant.
    '''
    pelvisCardRepose = getRCard( pelvisCard )
    delta = pdil.dagObj.getPos( referenceJoint ) - pdil.dagObj.getPos( getRJoint(referenceJoint) )
    move(pelvisCardRepose, [0, delta.y, 0], ws=True, r=True)

    
@registerAdjuster
def spineAlign( spineCard, rotation, threshold=6 ):
    ''' Rotates the joints of the card cumulatively to `rotation`, which is spread out proportionally.
    
    Joints less than `threshold` from the up axis are not considered.
    '''
    up = dt.Vector(0, 1, 0)
    
    spineEnd = spineCard.joints[-1] # &&& This should validate the end joint is real and not a helper
    childrenOfSpineCards = [getRJoint(bpj).getParent() for bpj in spineEnd.proxyChildren]
    preserve = { card: pdil.dagObj.getRot(card) for card in childrenOfSpineCards }
    
    # Get the positions of the spine joints AND the next joint, since that determines the rotation of the final spine
    reposeJoints = [getRJoint(j) for j in spineCard.joints ]
    pos = [pdil.dagObj.getPos( rj ) for rj in reposeJoints ]
    
    nextJoint = spineEnd.getOrientState()
    if nextJoint.joint:
        pos.append( pdil.dagObj.getPos( getRJoint(nextJoint.joint) ) )
    
    angles = [ math.degrees((child - cur).angle( up ))
               for cur, child in zip( pos, pos[1:] ) ]
    
    currentRotations = [pdil.dagObj.getRot( rj ) for rj in reposeJoints]
    
    adjust = [ (i, angle) for i, angle in enumerate(angles) if angle > threshold ]
    total = sum( (angle for _, angle in adjust ) )
        
    for i, angle in adjust:
        currentRotations[i].x -= rotation * ( angle / total )
        xform(reposeJoints[i], ws=True, ro=currentRotations[i] )
    
    
    for bpj, rot in preserve.items():
        xform(bpj, ws=True, ro=rot)


@registerAdjuster
def worldRotate(card, cardRotation=[0, 0, 0]):
    ''' Applies a relative world rotation to the repose card.
    '''
    rCard = getCardParent(getRJoint(card.joints[0]))
    rotate(rCard, cardRotation, ws=True, r=True, fo=True) # Not sure if `fo` is needed


@registerAdjuster
def xformRotation(card, cardRotation=None, jointRotations=[]):
    ''' Applies an world xform rotation to the repose card and joints.
    
    Args:
        cardRotation: [x, y, z] rotation for the card.
        jointRotations: A list of [x, y, z] rotation or `None` indicating no alteration.
    '''
    if cardRotation:
        rCard = getCardParent(getRJoint(card.joints[0]))
        xform(rCard, ws=True, ro=cardRotation)

    for bpj, rotation in zip( card.joints, jointRotations ):
        if rotation:
            xform( getRJoint(bpj), ws=True, ro=rotation)



@registerAdjuster(anyJoint=['otherJoint'])
def setPivot(card, otherJoint):
    ''' Move the repose card's pivot to the give joint
    '''
    pivot = pdil.dagObj.getPos(getRJoint(otherJoint))
    xform(getRCard(card), ws=True, piv=pivot )


@registerAdjuster
def keepRotation(card):
    ''' Applies the world rotation of the blueprint card.
    '''
    rot = pdil.dagObj.getRot(card)
    xform( getRCard(card), ws=True, ro=rot )


@registerAdjuster
def floorPlaneForward(card, baseJoint):
    ''' Rotates in world Y axis to point directly forward.  'Forward' is determined by the baseJoint and it's child
    '''
    rCard = getRCard(card)
    orientState = baseJoint.getOrientState()
    targetRJoint = getRJoint( orientState.joint )
    
    aim = pdil.dagObj.getPos(targetRJoint) - pdil.dagObj.getPos(getRJoint(baseJoint))
    print(baseJoint, targetRJoint)
    rotate(rCard, [0, -math.degrees(math.atan2( aim.x, aim.z )), 0], ws=True, r=True )


# It's cheesy to cache parents globally, but for now better than an overly complicated
# system to pass this data around
if '_falseParentCache' not in globals():
    _falseParentCache = {}


@registerAdjuster(anyJoint=['bpJoint'])
def falseParentSetupAlign(card, bpJoint):
    ''' Temporarily parent the rCard under the rJoint so it inherits any modifications.
    '''
    global _falseParentCache
    rCard = getRCard(card)
    rJoint = getRJoint(bpJoint)

    _falseParentCache[rCard] = rCard.getParent()

    rCard.tx.unlock()
    rCard.ty.unlock()
    rCard.tz.unlock()
    
    rCard.setParent(rJoint)


@registerAdjuster
def _falseParentTeardown(card, _bpJoint):
    ''' Temporarily parent the rCard under the rJoint so it inherits any modifications.
    
    _bpJoint is unused but exists to match signature of falseParentSetupAlign for easy substitution.
    '''
    global _falseParentCache
    rCard = getRCard(card)
    
    rCard.setParent(_falseParentCache.pop(rCard))


def runAdjusters(cards=None, progress=None):
    ''' Apply the adjustments to the given cards, default to all. Optional progress called twice for each card.
    '''
    adjustments = []
    
    followup = []
    
    if not cards:
        cards = find.blueprintCards()
    
    # If a false parent is setup, make sure it gets undone
    for card in cards:
        temp = card.rigData.get('tpose', [])
        for t in temp:
            t['card'] = card
            if t['call'] == 'falseParentSetupAlign':
                teardown = deepcopy(t)
                teardown['call'] = '_falseParentTeardown'
                followup.append( teardown )
            
        adjustments += temp
        if progress:
            progress.update()
        
    #print('{} Adjustments found'.format(len(adjustments)) )
    adjustments.sort( key=operator.itemgetter('order') )
    
    adjustments += followup
    
    for adjust in adjustments:
        rCard = getRCard( adjust['card'] )
        if rCard.hasAttr('adjusted'):
            if rCard.adjusted.get():
                print('Already adjusted', adjust['card'])
                continue
        
        try:
            applyTposeAdjust( adjust )
        except Exception:
            print('ERROR ADJUSTING', adjust['order'], adjust['call'])
            raise

    for card in cards:
        rCard = getRCard( card )
        if not rCard.hasAttr('adjusted'):
            rCard.addAttr('adjusted', at='bool')
        rCard.adjusted.set(True)
        if progress:
            progress.update()


adjusterInputRE = re.compile(r'((?P<self>self)|(id:(?P<id>[a-zA-Z]+)))(\.joints\[(?P<joint>\d+)\])?')


def applyTposeAdjust(adjust):
    ''' Perform the transform according the `adjust` dict.
    
    adjust = {
        'card': <the fossil card (the adjust function with conver to repose card)>,
        'call': <the function to apply, must be a registered `adjustCommands`>,
        'args': <list of strings, each will be parsed an converted to nodes>
    }
    
    An arg can be:
        'self': A reference to itself.
        'self.joint[#]': A reference to a specific joint.
        '<other>': A reference to another card by id.
        '<other>.joint[#]': A reference to another card's joint.
    
    '''
    cmd = adjustCommands[ adjust['call'] ]
    
    card = adjust['card']
    
    converted = []
    for arg in adjust['args']:
        if isinstance(arg, basestring):
            result = adjusterInputRE.match(arg).groupdict()
            
            #targetCard = card if result['self'] else util.FIND(None, cardId=result['id'])
            targetCard = card # if result['self'] else ids.readIdSpec( arg )
            jointIndex = int(result['joint']) if result['joint'] else None
            
            if jointIndex is None:
                converted.append( targetCard )
            else:
                converted.append( targetCard.joints[ jointIndex ] )

        elif isinstance(arg, dict):
            converted.append( ids.readIdSpec( arg ) )

        else:
            converted.append(arg)
    #print( 'Converted args', cmd, converted )
    cmd( *converted )


def addAdjuster(card, command, args):
    ''' `command` must be in `adjustCommands`, done via `registerAdjuster()` decorator.
    `args` is a list, always starting with 'self' and the appropriate inputs for the function.
    BPJoint will be converted to a json friendly format automatically.
    '''
    order = 0
    for _card in find.blueprintCards():
        for adjuster in _card.rigData.get('tpose', []):
            order = max(order, adjuster['order'])
    order += 1
    
    for i, arg in enumerate(args):
        if isinstance(arg, PyNode) and arg.__class__.__name__ == 'BPJoint':
            if arg.card == card:
                args[i] = 'self.joints[{}]'.format( card.joints.index(arg) )
            else:
                args[i] = ids.getIdSpec(arg)
    
    with card.rigData as data:
        adjusters = data.setdefault('tpose', [])
        
        adjusters.append(
            OrderedDict([
                ('args', args),
                ('call', command),
                ('order', order),
            ])
        )
        
        
def reorder(currentIndex, newIndex):
    
    orders = [ adjuster['order']
        for card in find.blueprintCards()
        for adjuster in card.rigData.get('tpose', []) ]
    
    orders.sort()
    
    changeTo = {i: i for i in orders}
    
    changeTo[currentIndex] = newIndex
    
    # Only scoot if needed
    if newIndex in changeTo:
        # If moving later, scoot all the inbetween adjusters up one to make room
        if currentIndex < newIndex:
            for i in range(currentIndex + 1, newIndex):
                if i in changeTo:
                    changeTo[i] -= 1
                
        # Otherwise scoot everything inbtween later to make room up front
        elif currentIndex > newIndex:
            for i in range(newIndex, currentIndex):
                if i in changeTo:
                    changeTo[i] += 1
    
    # Finally, update
    for card in find.blueprintCards():
        for i, adjuster in enumerate(card.rigData.get('tpose', [])):
            if changeTo[ adjuster['order'] ] != adjuster['order']:
                
                with card.rigData as rigData:
                    rigData['tpose'][i]['order'] = changeTo[ adjuster['order'] ]