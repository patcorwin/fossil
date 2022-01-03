from __future__ import print_function, division, absolute_import

from pymel.core import curve, delete, nurbsPlane

from . import _build_util as util


@util.commonArgs
def build():
    #crv = curve( d=1, p=((0, 0, 0), (0, 0, .5)))
    #ctrl = revolve( crv, ch=False, ssw=0, esw=360, degree=3, ax=[0, 1, 0] )[0]
    
    line = curve(d=1, p=[
        (-0.5, 0, 0.5),
        (0.5, 0, 0.5),
        (0.5, 0, -0.5),
        (-0.5, 0, -0.5),
        (-0.5, 0, 0.5),
        ]  # noqa
    )

    line.rename('outline')

    ctrl = nurbsPlane( ax=[0, 1, 0], w=1, d=1, lr=1 )[0]

    line.getShape().setParent( ctrl, add=True, shape=True )
    delete(line)

    return ctrl