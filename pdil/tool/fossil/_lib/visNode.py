from __future__ import absolute_import, division, print_function

from pymel.core import cmds, connectAttr, createNode, deleteAttr, listConnections, nodeType, getAttr, mel, PyNode, warning

import logging

import pdil

from .._core import find

VIS_NODE_TYPE = 'visnode'

log = logging.getLogger(__name__)


def get(create=True):
    ''' Returns the shared shape if it exists and makes it if it doesn't if create=True (default).
    '''
    obj = find.mainGroup()
    if not obj:
        return None
    
    shape = pdil.sharedShape.find(obj, VIS_NODE_TYPE)
    if shape:
        return shape
    
    if create:
        return pdil.sharedShape._makeSharedShape(obj, 'sharedShape', VIS_NODE_TYPE)
    else:
        return None
        
        
def getVisLevel(obj):
    ''' Returns ('name', int:level) if it's in a group, otherwise an empty tuple.
    '''
    
    zero = pdil.dagObj.zero(obj, apply=False, make=False)
    if zero:
        obj = zero
        
    visCon = listConnections(obj.visibility.name(), p=True, s=True, d=False)
    if visCon:
        node = visCon[0].node()
        attr = visCon[0].longName()  # This returns the long attr name, not the node at all, where .attrName() returns the short name.
        shape = get(create=False)
        
        level = 1
        
        if nodeType(node) == 'condition' and attr == 'outColorR':
            #con = listConnections(node + '.firstTerm', p=True, s=True, d=False)
            con = node.firstTerm.listConnections(p=True, s=True, d=False)
            
            if con:
                level = int(getAttr(node + '.secondTerm'))
                #node = shortName(con[0].node())
                attr = con[0].longName()  # longName() returns the long attribute name, not the node (technically they are the same here).
                return attr, level
        
        # Verify the shape is sharedShape via uuid (as of 2017, pymel tosses an error)
        if mel.ls(node, uuid=True)[0] == mel.ls(shape, uuid=True)[0]:
            return attr, level
        
    return ()


def connect( obj, name_level ):
    '''
    Hook the given obj's visibility to the `name` attribute on the sharedShape.
    If the attr doesn't exist, it will be made.
    
    Optionanal `level` will determine when the `obj` will become visible.  For
    example, 2 will not be visible at 1, but will at 2 and higher.
    '''
    
    name, level = name_level # Probably should just update this eventually to be 3 params
    
    orig = obj
    
    zero = pdil.dagObj.zero(obj, apply=False, make=False)
    if zero:
        obj = zero
    
    shape = get()
    
    if not shape:
        warning('Unable to add vis control, no object exists named "main" or tagged with ".fossilMainControl"')
        return
    
    log.debug('Applying vis control to {}, was given {} using {}'.format(obj, orig, shape))
    
    plug = shape + '.' + name
    if not cmds.objExists( plug ):
        cmds.addAttr( shape, ln=name, at='short', min=0, max=level, dv=1 )
        cmds.setAttr( shape + '.' + name, cb=True )
    elif cmds.getAttr( shape + '.' + name, type=True) not in ['bool', 'double', 'float', 'long', 'short']:
        warning( '{0} is not a good name for a vis group since the sharedShape has an attr already that is of the wrong type'.format(name) )
        return
    
    if cmds.addAttr(plug, q=True, max=True) < level:
        cmds.addAttr(plug, e=True, max=level)
    
    if level == 1:
        connectAttr( plug, obj.visibility.name(), f=True)
    else:
        connectAttr( getConditionNode(plug, level).outColorR, obj.visibility, f=True)
        
    obj.visibility.setKeyable(False)
    
    if not pdil.sharedShape.find(orig, VIS_NODE_TYPE):
        pdil.sharedShape.use(orig, shape)
    
    # If we have a main controller, put the container in a subgroup to make
    # the main group more organized.
    
    ''' 2021-11-25 Taking this out, I think redoing the hierarchery is probalby more confusing that having lots there.
    visGroupName = '_vis_' + name
    if isinstance(orig, nodeApi.RigController):
        if pdil.shortName(orig.container.getParent()) != visGroupName:
            orig.setGroup(visGroupName)
    '''


def getConditionNode(plug, level):
    '''
    '''
    
    conditions = PyNode(plug).listConnections(type='condition', p=True, d=True, s=False)
    for condition in conditions:
        if condition.attrName() == 'ft' and condition.node().secondTerm.get() == level:
            return condition.node()
    
    condition = createNode('condition', n=plug.split('.')[1] + '_%i' % level)
    condition.secondTerm.set(level)
    condition.operation.set(3)
    connectAttr( plug, condition.firstTerm, f=True )
    
    
    condition.colorIfTrue.set(1, 1, 1)
    condition.colorIfFalse.set(0, 0, 0)
    
    return condition


def existingGroups():
    ''' Returns a list of names, or an empty list if the visNode doesn't exist (or is empty).
    '''
    shapeNode = get(create=False)
    
    if not shapeNode:
        return []
    
    groups = cmds.listAttr( shapeNode, ud=True, s=True )
    if not groups:
        groups = []
    return groups


def pruneUnused():
    ''' Removes unused vis groups.
    '''
    shapeNode = get(create=False)
    if not shapeNode:
        return

    groups = existingGroups()
    for g in groups:
        attr = shapeNode + '.' + g
        if not listConnections(attr):
            deleteAttr(attr)


"""
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
"""


''' These feel like temp debug stuff that I don't actually need.  If I really want to keep them, maybe put in the sandbox?
def serializeAllConnections(node, toClipboard=False):
    connections = {}

    for plug in node.listAttr(ud=True, s=True, w=True):
        for node in plug.listConnections():
            if node.type() == 'condition':
                for obj in node.listConnections( s=False, d=True ):
                    data = getVisGroup(obj)
                    if data:
                        connections[obj.name()] = data
            else:
                data = getVisGroup(node)
                connections[node.name()] = data
    
    if toClipboard:
        core.text.clipboard.set( json.dumps(connections) )
    else:
        return connections
    
    
def deserializeAllConnections(connections=None):
    
    if connections is None:
        connections = json.loads( core.text.clipboard.get() )

    for obj, data in connections.items():
        if objExists(obj):
            connect(PyNode(obj), data)
'''
