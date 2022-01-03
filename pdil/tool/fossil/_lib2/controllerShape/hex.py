from __future__ import print_function, division, absolute_import

from pymel.core import circle, delete, torus

from . import _build_util as util


@util.commonArgs
def build():
    ctrl = torus(ax=[0, 1, 0], ssw=30, esw=390, msw=360, r=0.40, hr=0.25, d=1, s=6, nsp=4, ch=False)[0]
    
    line = circle( nr=[0, 1, 0], sw=360, r=0.40, d=1, s=6, ch=False )[0]
    line.rename('outline')
    line.getShape().setParent( ctrl, add=True, shape=True )
    delete(line)
    
    return ctrl