from __future__ import print_function, division, absolute_import

from pymel.core import curve, delete, rotate, sphere

from . import _build_util as util


@util.commonArgs
def build():
    '''
    It takes extra work to draw circle with a single line.  This is accomplished
    by having the terminal point exactly where the curve must pass through
    and points very near it to give it the (almost) correct bend.
    
    This is repeated 3x, then that same technique is used to make a quarter
    arc, then an additional hoop.  The first 3 hoops and transition are
    made vertical, which puts the transition ending back on the ground plane,
    where the 4th hoop remains.
    '''
    ctrl = sphere( ax=[0, 1, 0], ssw=0, esw=360, r=0.49 * 0.9, d=3, s=6, nsp=4 )[0]
    
    major = util.CirclePoints.major
    minor = util.CirclePoints.minor
    body = util.CirclePoints.body
    terminal = util.CirclePoints.terminal
    
    s = [-minor, 0, -major]
    e = [minor, 0, -major]
    
    hoop = [terminal, s, s] + body + [e, e, terminal]
    count = len(hoop)
    
    transArc = [terminal] + \
        [[-minor, 0, -major]] * 2 + \
        [body[0]] + \
        [[-major, 0, -minor]] * 2 + \
        [[-.5 * 0.9, 0, 0]]
    
    line = curve(p=hoop * 3 + transArc + hoop, d=3 )
    
    rotate( line.cv[:count * 3 + len(transArc) - 1], [90, 0, 0] )
    rotate( line.cv[count:count * 2], [0, 60, 0] )
    rotate( line.cv[count * 2:count * 3], [0, -60, 0] )
    rotate( line.cv[count * 3 + len(transArc):], [0, 90, 0] )
    
    line.rename('outline')
    line.getShape().setParent(ctrl, add=True, shape=True)
    
    delete(line)
    
    return ctrl