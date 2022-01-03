from __future__ import print_function, division, absolute_import

from pymel.core import curve, cylinder, delete, sphere

from . import _build_util as util


@util.commonArgs
def build():
    defaults = {'ax': (0, 1, 0), 'ssw': 0, 'esw': 360, 'd': 3, 'ut': 0, 'tol': 0.02, 'ch': False}
    ctrl = sphere( p=(0, 0.8333333, 0), r=0.166667, s=6, nsp=4, **defaults)[0]
    cyl = cylinder( p=(0, 0.345, 0), r=.08333333, hr=8.333333, s=4, nsp=1, **defaults )[0]
    cyl.rename('tube')

    points = [
        # shaft
        [0, 0, 0],
        [0, 0.666667, 0],
        # circle
        [-0.11785101234662772, 0.71548248765337219, 0],
        [-0.166667, 0.833333, 0],
        [-0.11785101234662777, 0.95118451234662771, 0],
        [0, 1, 0],
        [0.1178510123466277, 0.95118451234662771, 0],
        [0.166667, 0.833333, 0],
        [0.11785101234662779, 0.71548248765337241, 0],
        [0, 0.666667, 0],
        # cross line
        [0.11785101234662779, 0.71548248765337241, 0],
        [-0.11785101234662777, 0.95118451234662771, 0],
        # transition
        [-0.166667, 0.833333, 0],
        # cross line
        [-0.11785101234662772, 0.71548248765337219, 0],
        [0.1178510123466277, 0.95118451234662771, 0],
    ]

    line = curve( p=points, d=1 )
    line.rename('outline')

    line.getShape().setParent( ctrl, add=True, shape=True )
    cyl.getShape().setParent( ctrl, add=True, shape=True )
    
    delete(line, cyl)

    return ctrl