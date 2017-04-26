'''
Utility collection

Example usage:
    # Put a controller in a group
    sharedShape.connect( someControler, 'footIk' )
    
    # Give the controller access to the sharedShape
    sharedShape.use( someControler )
    
Many commands are done via cmds.* since pymel throws warnings about falling
back to MFnDagNode when casting a curve with no cvs.
'''
from __future__ import absolute_import, print_function

from pymel.core import cmds, objExists, delete, parent, warning, connectAttr, group, listConnections, deleteAttr, mel, setAttr, addAttr

from ..add import shortName
from .. import core
from .. import nodeApi


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
    setAttr(shape + '.visibility', False, l=True)  # noqa
    addAttr(shape, ln=core.shape.sharedShapeTag, at='message')
    
    cmds.addAttr( shape, ln=shapeType, at='message' )
    cmds.rename( shape, name )
    return obj.longName() + '|' + name


def find(obj):
    '''
    If there is a shared shape, returns it.  If not, returns None.
    '''
    shapes = cmds.listRelatives(obj.name(), type='nurbsCurve', f=True)
    if not shapes:
        return None
    
    for shape in shapes:
        if objExists( shape + '.sharedShape' ):
            return shape
    return None


def get(create=True):
    '''
    Returns the shared shape if it exists and makes it if it doesn't if create=True (default).
    '''
    obj = core.findNode.mainGroup()
    if not obj:
        return None
    
    shape = find(obj)
    if shape:
        return shape
    
    if create:
        return _makeSharedShape(obj, 'sharedShape', 'sharedShape')
    else:
        return None

    '''
    shape = cmds.createNode( 'nurbsCurve', p=obj.longName() )
    cmds.addAttr( shape, ln='sharedShape', at='message' )
    cmds.rename( shape, 'sharedShape' )
    return obj.longName() + '|sharedShape'
    '''


def connect( obj, name ):
    '''
    Hook the given obj's visibility to the `name` attribute on the sharedShape.
    If the attr doesn't exist, it will be made.
    '''
    
    orig = obj
    
    zero = core.dagObj.zero(obj, apply=False, make=False)
    if zero:
        obj = zero
    
    shape = get()
    plug = shape + '.' + name
    if not cmds.objExists( plug ):
        cmds.addAttr( shape, ln=name, at='short', min=0, max=1, dv=1 )
        cmds.setAttr( shape + '.' + name, cb=True )
    elif cmds.getAttr( shape + '.' + name, type=True) not in ['bool', 'double', 'float', 'long', 'short']:
        warning( '{0} is not a good name for a vis group since the sharedShape has an attr already that is of the wrong type'.format(name) )
        return
    
    connectAttr( plug, obj.visibility.name(), f=True)
    obj.visibility.setKeyable(False)
    
    # If we have a main controller, put the container in a subgroup to make
    # the main group more organized.
    
    visGroupName = '_vis_' + name
    
    if isinstance(orig, nodeApi.RigController):
        if shortName(orig.container.getParent()) != visGroupName:
            orig.setGroup(visGroupName)


def getVisGroup(obj):
    zero = core.dagObj.zero(obj, apply=False, make=False)
    if zero:
        obj = zero
        
    visCon = cmds.listConnections(obj.visibility.name(), p=True, s=True, d=False)
    if visCon:
        node, attr = visCon[0].rsplit('|')[-1].split('.')
        shape = get(create=False)
        if shape and shape.endswith('|' + node):
            return attr
    
    return ''


def remove(obj):
    '''
    Remove a sharedShape from a control.
    '''
    
    shape = find(obj)
    if not shape:
        return
    temp = group(em=True)
    parent( shape, temp, shape=True )
    delete(temp)


def use(obj):
    '''
    Have the given obj use the sharedShape
    '''
    cmds.parent( get(), obj.name(), add=True, shape=True )


def existingGroups():
    '''
    .. todo::
        make a real check for if main exists
    '''
    if not objExists('|main'):
        return []

    shape = get()
    groups = cmds.listAttr( shape, ud=True, s=True )
    if not groups:
        groups = []
    return groups


def pruneUnused():
    if not objExists('|main'):
        return

    shape = get()

    groups = existingGroups()
    for g in groups:
        attr = shape + '.' + g
        if not listConnections(attr):
            deleteAttr(attr)


def reorderAll():
    '''
    Make sure all the shared shapes come last.
    '''
    
    ''' Doesn't look I finished reorder(), which probably would just delete and re-add the attr
    shape = cls.get(create=False)

    if shape:
        for inst in listRelatives(shape, ap=True):
            reorder(find(inst), b=True)
    '''
    pass