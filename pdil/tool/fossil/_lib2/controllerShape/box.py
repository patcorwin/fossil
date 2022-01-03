from __future__ import print_function, division, absolute_import

from pymel.core import curve, delete, revolve

from . import _build_util as util


@util.commonArgs
def build():

    p = [   [0, -0.49, 0],
        [-0.49, -0.49, 0.49],
        [-0.49, 0.49, 0.49],
        [0, 0.49, 0] ]
    temp = curve( p=p, d=1 )
    ctrl = revolve( temp, ssw=0, esw=360, d=1, ax=[0, 1, 0], s=4 )[0]

    points = [  [-0.5, 0.5, 0.5],
                [-0.5, -0.5, 0.5],
                [-0.5, -0.5, -0.5],
                [-0.5, 0.5, -0.5],
                [-0.5, 0.5, 0.5],
                [0.5, 0.5, 0.5],
                [0.5, 0.5, -0.5],
                [-0.5, 0.5, -0.5],
                [-0.5, -0.5, -0.5],
                [0.5, -0.5, -0.5],
                [0.5, 0.5, -0.5],
                [0.5, -0.5, -0.5],
                [0.5, -0.5, 0.5],
                [0.5, 0.5, 0.5],
                [0.5, -0.5, 0.5],
                [-0.5, -0.5, 0.5] ]
                    
    line = curve(p=points, d=1)
    line.rename('outline')
    
    line.getShape().setParent( ctrl, add=True, shape=True )
        
    delete(line, temp)
    
    return ctrl