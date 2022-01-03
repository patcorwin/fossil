from __future__ import print_function

from pymel.core import move, dt, xform


def to(card, otherJoint):
    pos = xform( card.start(), q=True, ws=True, t=True )
    dest = xform( otherJoint, q=True, ws=True, t=True )
        
    xform( card, ws=True, r=True, t=(dt.Vector(dest) - dt.Vector(pos)) )


def toObjByCenter(card, otherJoint):
    pos = xform( card, q=True, ws=True, t=True )
    dest = xform( otherJoint, q=True, ws=True, t=True )
        
    xform( card, ws=True, r=True, t=(dt.Vector(dest) - dt.Vector(pos)) )


def left(card, amount=5):
    move( card, [amount, 0, 0], r=True, ws=True )


def right(card, amount=5):
    move( card, [-amount, 0, 0], r=True, ws=True )


def up(card, amount=5):
    move( card, [0, amount, 0], r=True, ws=True )


def down(card, amount=5):
    move( card, [0, -amount, 0], r=True, ws=True )


def forward(card, amount=5):
    move( card, [0, 0, amount], r=True, ws=True )


def backward(card, amount=5):
    move( card, [0, 0, -amount], r=True, ws=True )


def closer(card, amount=5):
    if xform(card, q=True, ws=True, t=True)[0] > 0:
        right(card, amount)
    else:
        left(card, amount)


def farther(card, amount=5):
    if xform(card, q=True, ws=True, t=True)[0] < 0:
        right(card, amount)
    else:
        left(card, amount)
