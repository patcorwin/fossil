from maya.api import OpenMaya
from pymel.core import cmds, attributeQuery

from . import capi  # &&& Need to move this to lib since it imports a neighbor

__all__ = [
    'SHARED_SHAPE',
    'isValidNurbsCurve',
    'getNurbsShapes',
    'uniformPointsOnCurve',
]


SHARED_SHAPE = 'sharedShapeData'


def isValidNurbsCurve(shape):
    ''' Returns True if the given shape is valid as is not a sharedShape.
    '''
    if attributeQuery( SHARED_SHAPE, node=shape, ex=True ):
        return False
    
    # Pymel barfs (at least in the past) on getting cv count on shared shape so we must use cmds
    return (cmds.getAttr( str(shape) + '.spans' ) and cmds.getAttr( str(shape) + '.degree' ))


def getNurbsShapes(rigController):
    ''' Returns nurbs shapes, excluding the shared shapes.
    '''
    shapes = []
    for shape in rigController.getShapes():
        if shape.type().count('nurb'):
            if shape.type() == 'nurbsCurve' and not isValidNurbsCurve(shape):
                continue
            
            shapes.append(shape)
    return shapes
    
    
def _getPoint(crvFn, val):
    ''' Helper for `uniformPointsOnCurve`
    '''
    point = crvFn.getPointAtParam(
        crvFn.findParamFromLength(crvFn.length() * val),
        OpenMaya.MSpace.kWorld
    )
    return [point.x, point.y, point.z]


def uniformPointsOnCurve(crv, count):
    ''' Returns evenly spaced world points along the given curve.
    '''
    crvFn = OpenMaya.MFnNurbsCurve( capi.asDagPath(crv) )
    
    step = 1.0 / (count - 1)

    points = [ _getPoint(crvFn, step * i) for i in range(count) ]
        
    return points