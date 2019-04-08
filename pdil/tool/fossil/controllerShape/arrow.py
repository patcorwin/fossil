from __future__ import print_function, division, absolute_import

from pymel.core import curve, delete, nurbsPlane, xform

from . import _build_util as util


@util.commonArgs
def build():
    ctrl = nurbsPlane(axis=[0, 1, 0], u=2, d=1)[0]
    xform( ctrl.cv[2][0], ws=True, t=[0.5, 0, 0.2] )
    xform( ctrl.cv[0][0], ws=True, t=[-0.5, 0, 0.2] )

    line = curve( d=True, p=[(-0.5, 0, -0.5), (-0.5, 0, 0.2), (0, 0, 0.5), (0.5, 0, 0.2), (0.5, 0, -0.5), (-0.5, 0, -0.5)] )
    line.rename('outline')
    line.getShape().setParent( ctrl, add=True, shape=True )
    delete(line)

    return ctrl