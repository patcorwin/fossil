from __future__ import print_function, division, absolute_import

from pymel.core import curve, cylinder, delete, move

from . import _build_util as util


@util.commonArgs
def build():
    ctrl = cylinder( ax=[0, 1, 0], ssw=0, esw=360, r=0.455, hr=0.455, d=3, ch=0)[0]
    
    major = util.CirclePoints.major
    minor = util.CirclePoints.minor
    body = util.CirclePoints.body
    terminal = util.CirclePoints.terminal
    
    s = [-minor, 0, -major]
    e = [minor, 0, -major]
    
    top = [terminal, s, s] + body + [e, e, terminal, terminal, terminal]
    bot = [terminal, terminal, terminal, terminal, s, s] + body + [e, e, terminal, terminal, terminal]
    
    line = curve( p=top + bot )
    line.rename( 'outline' )
    move( line.cv[ :len(top) ], [0, .125, 0], r=1)
    move( line.cv[ len(top): ], [0, -.125, 0], r=1)
    line.getShape().setParent( ctrl, add=True, shape=True )
    delete(line)
    
    return ctrl