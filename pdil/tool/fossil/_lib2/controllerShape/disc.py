from __future__ import print_function, division, absolute_import

from pymel.core import curve, delete, revolve

from . import _build_util as util


@util.commonArgs
def build():
    crv = curve( d=1, p=((0, 0, 0), (0, 0, .5 * 0.9)))
    ctrl = revolve( crv, ch=False, ssw=0, esw=360, degree=3, ax=[0, 1, 0] )[0]
    
    major = util.CirclePoints.major
    minor = util.CirclePoints.minor
    body = util.CirclePoints.body
    terminal = util.CirclePoints.terminal
    
    s = [-minor, 0, -major]
    e = [minor, 0, -major]
    
    hoop = [terminal, s, s] + body + [e, e, terminal, terminal, terminal]
    cross = [(0, 0, 0.5 * 0.9)]*3 + [(0, 0, 0)]*3 + [(0.5 * 0.9, 0, 0)]*3 + [(-0.5 * 0.9, 0, 0)]*3  # noqa
    
    offset = 0.001
    
    upper = [ (x, offset, z) for x, y, z in hoop + cross ]
    lower = [ (x, -offset, z) for x, y, z in hoop + cross ]
    
    line = curve( p=upper + [(0, offset, 0)] * 3 + [lower[0]] * 2 + lower )
    line.rename('outline')
    line.getShape().setParent( ctrl, add=True, shape=True )
    
    delete(line, crv)
    
    return ctrl