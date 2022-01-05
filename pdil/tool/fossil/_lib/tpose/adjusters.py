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

from pymel.core import dt, move, rotate, xform

import pdil

from ..._core import find
from ..._core import ids
from .tpcore import getRCard, getRJoint


# -----------------------------------------------------------------------------
# Alignment stuff

'''
pdil.tool.fossil.tpose.armAlign( PyNode('Shoulder_card') )
pdil.tool.fossil.tpose.wristAlign( PyNode('Shoulder_card').joints[2] )

pdil.tool.fossil.tpose.fingerAlign( PyNode('Index01_L_bpj') )
pdil.tool.fossil.tpose.fingerAlign( PyNode('Middle02_L_bpj') )
pdil.tool.fossil.tpose.fingerAlign( PyNode('Pinky02_L_bpj') )

pdil.tool.fossil.tpose.footAlign( PyNode('Ball_L_bpj') )

pdil.tool.fossil.tpose.pelvisAlign( PyNode('Pelvis_bpj'), PyNode('Ball_L_bpj'))

pdil.tool.fossil.tpose.spineAlign( PyNode('Spine_card'), 20)


with o.rigData as rigData:
    rigData['tpose'] = [{
        'order': 0,
        'call': 'spineAlign',
        'args': ['self', 20]
    }]

with o.rigData as rigData:
    rigData['tpose'] = [{
        'order': 10,
        'call': 'armAlign',
        'args': ['self']
    },
    {
        'order': 20,
        'call': 'wristAlign',
        'args': ['self.joints[2]']
    }]
    
with o.rigData as rigData:
    rigData['tpose'] = [{
        'order': 30,
        'call': 'fingerAlign',
        'args': ['self.joints[0]']
    }]
with o.rigData as rigData:
    rigData['tpose'] = [{
        'order': 40,
        'call': 'fingerAlign',
        'args': ['self.joints[0]']
    }]
with o.rigData as rigData:
    rigData['tpose'] = [{
        'order': 50,
        'call': 'fingerAlign',
        'args': ['self.joints[0]']
    }]
    
with o.rigData as rigData:
    rigData['id'] = 'leg'
    rigData['tpose'] = [{
        'order': 60,
        'call': 'legAlign',
        'args': ['self']
    },
    {
        'order': 70,
        'call': 'footAlign',
        'args': ['self.joints[2]']
    }]
    

with o.rigData as rigData:
    rigData['tpose'] = [{
        'order': 8,
        'call': 'pelvisAlign',
        'args': ['self', 'id:leg.joints[2]' ]
    }]

'''

def optional_arg_decorator(fn):
    # https://stackoverflow.com/questions/3888158/making-decorators-with-optional-arguments#comment65959042_24617244
    def wrapped_decorator(*args):
        if len(args) == 1 and callable(args[0]):
            return fn(args[0])

        else:
            def real_decorator(decoratee):
                return fn(decoratee, *args)

            return real_decorator

    return wrapped_decorator



if 'adjustCommands' not in globals():
    adjustCommands = {}


@optional_arg_decorator
def registerAdjuster(func, name=''):
    name = name if name else func.__name__
    
    spec = inspect.getargspec(func)
    
    assert 1 <= len(spec.args) <= 4, ('Align function {} must have 1-4 args, the first being that card'.format(func) )
    
    # &&& TODO, validate first arg has 'Card', and th
    
    adjustCommands[name] = func
    return func


def getCardParent(rJoint):
    ''' Returns the parent reposeCard, skipping the auto-created 'transform#'
    
    When ancestors are scaled, they can create intermediate transforms that need
    to be ignored.
    '''
    p = rJoint.getParent()
    if p.hasAttr('bpCard'):
        return p
    else:
        return p.getParent()


@registerAdjuster
def armAlign(shoulderCard):
    ''' Rotates the lead joint to point down the +X axis, and the other joints
    to be almost straight, with a slight bend pointing behind, -Z.

    MUST have a parent joint to rotate properly
    '''
    shoulderJoint = shoulderCard.joints[0]
    
    shoulderRepose = getRJoint(shoulderJoint)
    
    xform( getCardParent(shoulderRepose), ws=True, ro=[0, 0, 90] )
    
    out = pdil.dagObj.getPos( getRJoint(shoulderCard.joints[1]) ) - pdil.dagObj.getPos( getRJoint(shoulderCard.joints[0]) )
    toRotate = math.degrees( out.angle( (1, 0, 0) ) )
    rotate(shoulderRepose, [0, -toRotate + 2, 0 ], ws=True, r=True)
    
    elbowRepose = getRJoint(shoulderCard.joints[1])
    out = pdil.dagObj.getPos( getRJoint(shoulderCard.joints[2]) ) - pdil.dagObj.getPos( getRJoint(shoulderCard.joints[1]) )
    toRotate = math.degrees( out.angle( (1, 0, 0) ) )
    rotate(elbowRepose, [0, toRotate - 2, 0 ], ws=True, r=True)


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

    
@registerAdjuster
def legAlign(legCard):
    '''
    Sets card vertical.
    '''
    xform( getCardParent(getRJoint(legCard.joints[0])), ws=True, ro=[0, 0, 0] )


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

    rotate(rotatingJoint, [0, -math.degrees( math.atan( aim.x / aim.z ) ), 0], ws=True, r=True )

    rotate(rotatingJoint, [math.degrees(math.atan(aim.y / aim.z)), 0, 0], ws=True, r=True )


    m = xform(targetCard, q=True, ws=True, m=True)
    rotate(rotatingJoint, [0, 0, -math.degrees( math.atan( m[1] / m[0] ) )], ws=True, r=True)

    
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

    
@registerAdjuster
def pelvisAlign( pelvisCard, referenceJoint ):
    '''
    Adjusts the height by how much the reference joint moves in the repose.
    Commonly set to the toe, when the legs are straighted, this will raise so
    the repose so it stays on top of the floor.
    '''
    pelvisCardRepose = getRCard( pelvisCard )
    delta = pdil.dagObj.getPos( referenceJoint ) - pdil.dagObj.getPos( getRJoint(referenceJoint) )
    move(pelvisCardRepose, [0, delta.y, 0], ws=True, r=True)

    
@registerAdjuster
def spineAlign( spineCard, rotation, threshold=6 ):
    '''
    Rotates the joints of the card cumulatively to `rotation`, which is spread out proportionally.
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
def worldRotate(card, rotation=[0, 0, 0]):
    ''' Applies a world rotation to the repose card.
    '''
    rCard = getCardParent(getRJoint(card.joints[0]))
    rotate(rCard, rotation, ws=True, r=True, fo=True) # Not sure if `fo` is needed


# It's cheesy to cache parents globally, but for now better than an overly complicated
# system to pass this data around
if '_falseParentCache' not in globals():
    _falseParentCache = {}


@registerAdjuster
def falseParentSetupAlign(card, bpJoint):
    ''' Temporarily parent the rCard under the rJoint so it inherits any modifications.
    '''
    global _falseParentCache
    rCard = getRCard(card)
    rJoint = getRJoint(bpJoint)

    _falseParentCache[rCard] = rCard.getParent()

    rCard.setParent(rJoint)


@registerAdjuster
def _falseParentTeardown(card, _bpJoint):
    ''' Temporarily parent the rCard under the rJoint so it inherits any modifications.
    
    _bpJoint is unused but exists to match signature of falseParentSetupAlign for easy substitution.
    '''
    global _falseParentCache
    rCard = getRCard(card)
    
    rCard.setParent(_falseParentCache[rCard])


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

    print('CONVERTED', converted)
    cmd( *converted )


def addAdjuster(card, command, args):
    order = 0
    for _card in find.blueprintCards():

        for adjuster in _card.rigData.get('tpose', []):
            order = max(order, adjuster['order'])
    order += 1
    
    with card.rigData as data:
        adjusters = data.setdefault('tpose', [])
        
        adjusters.append(
            OrderedDict([
                ('args', args),
                ('call', command),
                ('order', order),
            ])
        )