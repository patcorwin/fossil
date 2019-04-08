from __future__ import print_function, division, absolute_import

from pymel.core import curve, cylinder, delete, makeIdentity, move

from . import _build_util as util


@util.commonArgs
def build():
    ctrl = cylinder( ax=[0, 1, 0], ssw=90, esw=270, r=0.455, hr=0.455, d=3, ch=0, s=4)[0]

    major = util.CirclePoints.major
    minor = util.CirclePoints.minor
    body = util.CirclePoints.body[:3]
    terminal = util.CirclePoints.terminal

    s = [-minor, 0, -major]

    opTerminal = [ terminal[0], terminal[1], -terminal[2] ]
    opS = [-minor, 0, major]

    top = [terminal, s, s] + body + [opS, opS, opTerminal, opTerminal, opTerminal]
    bot = list(reversed(top))

    line = curve( p=top + bot + [terminal, terminal, terminal] )

    line.rename( 'outline' )

    move( line.cv[ :len(top) ], [0, .125, 0], r=1)
    move( line.cv[ -1 ], [0, .125, 0], r=1)

    move( line.cv[ len(top): -1 ], [0, -.125, 0], r=1)
    line.getShape().setParent( ctrl, add=True, shape=True )
    delete(line)
    
    # Essentially this always feels 90 off by default and this is a quick fix for that.
    ctrl.ry.set(90)
    makeIdentity( ctrl, a=True, r=True )
    return ctrl