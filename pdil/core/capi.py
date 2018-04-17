from maya.api import OpenMaya
import maya.OpenMaya


def asMObject(node):
    '''
    Return API 2.0 dependency node from the given pynode or string.
    '''

    _list = OpenMaya.MSelectionList()
    if isinstance(node, basestring):
        _list.add( node )
    else:
        _list.add( node.name() )
    return OpenMaya.MFnDependencyNode( _list.getDependNode( 0 ) )


def asMObjectOld( otherMobject ):
    '''
    tries to cast the given obj to an mobject - it can be string
    Taken from zoo.
    '''
    if isinstance( otherMobject, basestring ):
        sel = maya.OpenMaya.MSelectionList()
        sel.add( otherMobject )
        
        if '.' in otherMobject:
            plug = maya.OpenMaya.MPlug()
            sel.getPlug( 0, plug )
            tmp = plug.asMObject()
            tmp.__MPlug__ = plug
        else:
            tmp = maya.OpenMaya.MObject()
            sel.getDependNode( 0, tmp )

        return tmp

    if isinstance( otherMobject, (maya.OpenMaya.MObject, maya.OpenMaya.MObjectHandle) ):
        return otherMobject