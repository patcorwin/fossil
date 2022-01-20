from __future__ import absolute_import, division, print_function

from maya.api import OpenMaya


try:
    basestring
except NameError: # python 3 compatibility
    basestring = str

__all__ = ['asMObject', 'asDagPath']


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


def asDagPath(obj):
    ''' Returns the maya.api dagPath for the given object.
    '''
    sel = OpenMaya.MSelectionList()
    sel.add(str(obj))
    return sel.getDagPath(0)
