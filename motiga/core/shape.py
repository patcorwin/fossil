from pymel.core import cmds, attributeQuery

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
    
    