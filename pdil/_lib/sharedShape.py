'''
Easily manage an instanced shape so attributes can be easily accessible across
multiple objects.  Maya does have aliasAttr, but this means things are packaged
in shapes, which works well for occassionally accessed stuff.  Also, updating
is trivial since only one node is actually updated.

Objects can have multiple sharedShapes, but only one of each type.  UUIDs could
be used in the future to do more if the need arises.

```python
shape = pdil.sharedShape._makeSharedShape(someObj, 'coolShapeName', 'useless_type')

if pdil.sharedShape.find(someObj, 'useless_type'):
    print('Has shared shape')

pdil.sharedShape.remove(someObj, 'useless_type')
```


pymel used to have issues dealing with instance shaped but I need to see if this
is still true in 2020.  The old version had invalid curves, so that could have
been part of it but now valid curves are hidden and locked.
'''

from __future__ import absolute_import, print_function

from pymel.core import cmds, delete, parent, group, mel, setAttr, addAttr

from .. import _core as core


def _makeSharedShape(obj, name, shapeType):
    '''
    shapeType should be either 'sharedShape' or 'kinematicSwitch'
    
    Returns a string of the shape, ex 'Foot_L|sharedShape' (to bypass pymel warnings)
    '''
    shape = cmds.createNode( 'nurbsCurve', p=obj.longName() )
    
    # 2017 added a bunch of keyable attrs so get rid of them if possible.
    for attr in cmds.listAttr(shape, k=True):
        try:
            cmds.setAttr(shape + '.' + attr, k=False, l=True)
        except Exception as e:  # noqa
            #print( e )
            pass
        
    # Make it a valid curve so it doesn't get deleted during optimize scene
    # but lock and hide it.
    mel.eval('''setAttr "%s.cc" -type "nurbsCurve"
             1 1 0 no 3
             2 0 1
             2
             0 0 0
             0 0 0
             ;''' % shape )
    setAttr(shape + '.visibility', False, l=True)
    
    addAttr(shape, ln=core.shape.SHARED_SHAPE, dt='string')
    setAttr(shape + '.' + core.shape.SHARED_SHAPE, shapeType, type='string')
    
    cmds.rename( shape, name )
    return obj.longName() + '|' + name


def find(obj, shapeType):
    ''' If `obj` has shared shape of `shapeType`, return it or None if not found.
    '''
    shapes = cmds.listRelatives(obj.name(), type='nurbsCurve', f=True)
    if not shapes:
        return None
    
    for shape in shapes:
        if (cmds.attributeQuery(core.shape.SHARED_SHAPE, n=shape, ex=True)
        and cmds.getAttr(shape + '.' + core.shape.SHARED_SHAPE) == shapeType ):
            return shape
            
    return None


def remove(obj, shapeType):
    ''' Remove a sharedShape of `shapeType` from the given `obj`.
    '''
    
    shape = find(obj, shapeType)
    if not shape:
        return
    temp = group(em=True)
    
    # AFAIK, the only way to remove an instanced shape is 'moving' it and deleting that, deleting the shape deletes all.
    parent( shape, temp, shape=True )
    delete(temp)


def use(obj, shapeNode):
    ''' Have the given obj use the sharedShape.
    '''
    if find(obj, cmds.getAttr(shapeNode + '.' + core.shape.SHARED_SHAPE)):
        return
    
    try:
        cmds.parent( shapeNode, obj.name(), add=True, shape=True )
    except RuntimeError as ex:
        ''' cmds errors are a pain to catch and I really only want to catch if
        it's already a parent but th
        '''
        
        if ex.args != ('Maya command error',):
            raise
