from maya.api import OpenMaya
from pymel.core import cmds, attributeQuery

from . import capi  # &&& Need to move this to lib since it imports a neighbor

sharedShapeTag = 'mo_is_shared'


def isValidNurbsCurve(shape):
    '''
    Pymel barfs on getting cv count on shared shape so we must use cmds
    '''
    if attributeQuery( sharedShapeTag, node=shape, ex=True ):
        return False

    return (cmds.getAttr( str(shape) + '.spans' ) and cmds.getAttr( str(shape) + '.degree' ))


def getShapes(rigController):
    '''
    Returns all nurbs shapes except the shared shapes.
    '''
    shapes = []
    for shape in rigController.getShapes():
        if not shape.name().count('sharedShape') and shape.type().count('nurb'):
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