from __future__ import print_function, division, absolute_import

from pymel.core import curve, delete, move, nurbsPlane

from . import _build_util as util


@util.commonArgs
def build():
    
    ctrl = nurbsPlane( ax=[0, 1, 0], w=1, d=1, lr=1 )[0]
    move( ctrl.cv, [0, 0.5, 0], r=1, os=1, wd=True)
    other = nurbsPlane( ax=[0, 1, 0], w=1, d=1, lr=1 )[0]
    move( other.cv, [0, -0.5, 0], r=1, os=1, wd=True)
    
    points = [
        (-0.5, 0, 0.5),
        (0.5, 0, 0.5),
        (0.5, 0, -0.5),
        (-0.5, 0, -0.5),
        (-0.5, 0, 0.5),
    ]
    
    line = curve( p=[(p[0], p[1] + .5, p[2]) for p in points] + [(p[0], p[1] - .5, p[2]) for p in points], d=1 )
    line.rename('outline')
    
    other.getShape().setParent( ctrl, add=True, shape=True )
    line.getShape().setParent( ctrl, add=True, shape=True )
    
    delete(line, other)
    
    return ctrl