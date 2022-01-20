from __future__ import absolute_import, division, print_function
from pymel.core import curve, group, hide, joint, ls, objExists, parentConstraint, pointConstraint, PyNode

import pdil

from ._core import config
from ._core import find


def mainGroup(create=True, nodes=None):
    main = find.mainGroup()
    
    if main:
        return main
    
    if create:
        # Draw outer arrow shape
        main = curve( name='main', d=True, p=[(-40, 0, 20 ), (0, 0, 60 ), (40, 0, 20 ), (40, 0, -40 ), (0, 0, -20 ), (-40, 0, -40 ), (-40, 0, 20 )] )
        pdil.dagObj.lock(main, 's')
        main.visibility.setKeyable(False)
        main.visibility.set(cb=True)
    
        tagAsMain(main)
        
        if True:  # Put it in a default group
            pdil.layer.putInLayer(main, 'Controls')
        return main
    
    return None


def tagAsMain(obj):
    ''' Adds markup to identify the given object as the main control group.
    '''
    obj.addAttr(config.FOSSIL_MAIN_CONTROL, at='message')
    
    
def getTrueRoot(make=True):
    ''' Returns the root joint according the 'root_name', building it if needed.
    
    &&& DUPLICATED CODE IN fossileNodes
    '''
    rootName = config._settings['root_name']
    
    trueRoot = PyNode(rootName) if objExists( rootName ) else None
    
    if trueRoot:
        return trueRoot
    
    if make:
        trueRoot = joint(None, n=rootName)
        trueRoot.drawStyle.set(2)
        return trueRoot
    return None
    
    
def findRoot(nodes=None, make=None):
    ''' &&& IS THIS USED?
    Returns the root bone, trying to account for case and namespaces or None if
    not found.  `make` should be either 'root' or 'weaponRoot', specifying which
    to make (always top level) if a root is not found.
    
    Can be given a list of nodes to search for the root,
    '''

    names = [ config._settings['root_name'] ] # There might future ways of identifying root nodes

    if not nodes:
        # Check if any exist top level first
        top = ls(assemblies=True)
        for name in names:
            if name in top:
                return PyNode('|' + name)
    
    # See if there is a top level obj in a namespace named b_root of any casing.
    searchNodes = nodes if nodes else ls( assemblies=True )
    nodes = [obj for obj in searchNodes
        if any( [pdil.simpleName( obj ).lower() == name for name in names] )
    ]
    if len(nodes) == 1:
        return nodes[0]

    # Then check if any exist at all (which will fail if several exist in separate groups).
    for name in names:
        if objExists( name ):
            return PyNode( name )

    if make:
        return joint(None, n='b_' + make)
    
    else:
        return None
    
    
def rootMotion(create=True, main=None):
    rootMotion = find.rootMotion(main)
    
    if rootMotion:
        return rootMotion
    
    if create:
        root = getTrueRoot()
        if not root:
            # Unable to make root motion since the root doesn't exist.
            return None
    
        # Draw inner arrow shape
        rootMotion = curve( name='rootMotion', d=True, p=[(-32, 0, -12), (-32, 0, 20), (0, 0, 52), (32, 0, 20), (32, 0, -12), (-32, 0, -12)] )
        rootMotion.setParent( mainGroup() )
        pdil.dagObj.lock( rootMotion, 's' )
        #skeletonTool.controller.sharedShape.use(rootMotion)
        
        rootMotion.addAttr( 'fossilCtrlType', dt='string' )
        rootMotion.attr( 'fossilCtrlType' ).set( 'translate' )
        
        try:
            parentConstraint( rootMotion, root )
        except Exception:
            target = pointConstraint( root, q=True, tl=True )[0]
            parentConstraint( rootMotion, target )
            
        root.drawStyle.set( 2 )
        
        return rootMotion
    
    return None
    
    
def accessoryGroup():
    main = mainGroup()
    
    for child in main.listRelatives():
        if child.name() == 'accessory':
            grp = child
            break
    else:
        grp = group(n='accessory', em=True)
        grp.setParent(main)
        hide(grp)
        
    return grp


def leadController(obj):
    ''' Returns the lead controller (possibly itself) when given a fossil controller.
    '''
    if obj.__class__.__name__ == 'RigController' and obj.__class__.__module__ == 'pdil.nodeApi.fossilNodes':
        return obj
    else:
        objs = [ other for other in obj.message.listConnections()
            if other.__class__.__name__ == 'RigController' and other.__class__.__module__ == 'pdil.nodeApi.fossilNodes']
            
        if objs:
            return objs[0]
    
    return None
