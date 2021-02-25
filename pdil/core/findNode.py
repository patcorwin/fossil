'''
These function find different nodes, but generally will NOT make any if they do not exist,
the `getNodes` does that.  This lets all the lib modules find if needed, and only
the portions that actually need to make objects can do so.
'''
from __future__ import print_function, absolute_import

import json

from pymel.core import cmds, PyNode, warning, objExists, ls, joint

from ..add import *
from .. import nodeApi


def getRoot(nodes=None, make=None):
    '''
    Returns the root bone, trying to account for case and namespaces or None if
    not found.  `make` should be either 'root' or 'weaponRoot', specifying which
    to make (always top level) if a root is not found.
    
    Can be given a list of nodes to search for the root,
    '''

    names = [ 'b_root', 'b_Root', 'Rig:b_root', 'Rig:b_Root', 'b_weaponRoot', 'Rig:b_weaponRoot' ]

    if not nodes:
        # Check if any exist top level first
        top = ls(assemblies=True)
        for name in names:
            if name in top:
                return PyNode('|' + name)
    
    # See if there is a top level obj in a namespace named b_root of any casing.
    searchNodes = nodes if nodes else ls( assemblies=True )
    nodes = [obj for obj in searchNodes if simpleName( obj ).lower() == 'b_root' or simpleName(obj).lower() == 'b_weaponroot']
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


def controllers(main=None):
    '''
    Returns all the animation controllers in the scene.
    
    ..  todo:: Add the shapes that have ik/fk switching on them
    '''
    
    ''' Timing experiments: Results, cmds + sets is WAY faster!
        s = time.time()
        controls = [c for c in listRelatives(main, ad=True, type='transform') if c.hasAttr('fossilCtrlType')]
        print( time.time() - s, 'ls(*.fossilCtrlType) ORIGINAL' )


        s = time.time()
        controls = [PyNode(c) for c in cmds.listRelatives(main.name(), ad=True, type='transform', f=1) if cmds.attributeQuery('fossilCtrlType', node=c, ex=True)]
        print( time.time() - s, 'cmds.listRelatives() list comp' )


        s = time.time()
        #controls = [c for c in listRelatives(main, ad=True, type='transform') if c.hasAttr('fossilCtrlType')]
        allControls = set(cmds.ls('*.fossilCtrlType', type='transform', r=True, o=True))
        allControls.intersection_update( cmds.listRelatives(main.name(), ad=True, type='transform') )
        controls = [PyNode(o) for o in allControls]
        print( time.time() - s, 'cmds and set filtering' )
        
        Swift Cat as main:
        0.611000061035 ls(*.fossilCtrlType) ORIGINAL
        0.123000144958 cmds.listRelatives() list comp
        0.0439999103546 cmds and set filtering

        Swift as Main:

        2.1210000515 ls(*.fossilCtrlType) ORIGINAL
        0.398999929428 cmds.listRelatives() list comp
        0.0769999027252 cmds and set filtering

    '''
    
    allControls = set( cmds.ls( '*.fossilCtrlType', o=True, r=True, l=True ) )
    
    if main:
        mainTransforms = cmds.listRelatives(main.name(), ad=True, type='transform', f=True)
        if mainTransforms:
            allControls.intersection_update( mainTransforms )
            controls = [PyNode(o) for o in allControls]
            controls.append(main)
            
            root = rootMotion(main=main)
            if root:
                controls.append(root)
                
            return controls
            
        else:
            warning("No sub controls found for {0}".format(main.name()))
    
    else:
        controls = [PyNode(o) for o in allControls]
        main = mainGroup()
        if main:
            controls.append(main)

        root = rootMotion(main=main)
        if root:
            controls.append(root)
    
        return controls
    
    return []
    
    
MAIN_CONTROL_TAG = 'fossilMainControl'


def mainGroup(nodePool=None):
    '''
    Returns the main group containing the rig, named "main", or an object tagged as the main.
    
    todo: This logic should mainly go into `mainControls`, and this just returns the first.
    '''
    
    if nodePool:
        for n in nodePool:
            if simpleName(n) == 'main' or n.hasAttr(MAIN_CONTROL_TAG):
                return n
    
    if objExists('|main'):
        return PyNode('|main')
    else:
        # A pymel bug is sometimes returning duplicate nodes
        main = list(set([ obj for obj in ls( 'main', r=True) if not obj.getParent() ]))
        if len(main) == 1:
            return main[0]
    
    # No "main" ojbect was found, looking for tags
    plugs = ls('*.' + MAIN_CONTROL_TAG)
    if plugs:
        return plugs[0].node()
    
    return None


def mainControls():
    '''
    Returns all the main controls in the scene, ake the main of each character.
    
    todo: see mainGroup, take most of the logic.
    '''
    return ls( '*.' + MAIN_CONTROL_TAG, o=True, r=True )


def tagAsMain(obj):
    obj.addAttr(MAIN_CONTROL_TAG, at='message')

        
def leadController(obj):
    '''
    Given a controller, return the main RigController (possibly itself) or
    None if not found.
    
    ..  todo::
        This needs to be merged with the same one in skeletonTool.rig
    '''
    # &&& Replace this with actual node class references when nodeApi is moved
    if isinstance(obj, nodeApi.RigController):
        return obj
    else:
        objs = [ o for o in obj.message.listConnections() if isinstance(o, nodeApi.RigController) ]

        if objs:
            return objs[0]
    
    return None
        
        
def rootMotion(main=None):
    '''
    Returns the root motion, optionally making one if it doesn't exist.

    If main is specified, search its descendents.
    '''
    
    ''' Timing test with Swift as main, re and split are about equal and 200x faster!
        re and split were almost identical, even on the whole scene.
    
        s = time.time()
        #oldGetRootMotion(main)
        for child in listRelatives(main, ad=True, type='transform'):
        #for child in ls(type='transform'):
            if lib.dagObj.simpleName( child ) == 'rootMotion':
                break
                #return child
        print( time.time() - s, 'orig')

        s = time.time()
        for child in cmds.listRelatives(main.name(), ad=True, type='transform'):
        #for child in cmds.ls(type='transform'):
            if child.rsplit('|',1)[-1].rsplit(':', 1)[-1] == 'rootMotion':
                #print( child)
                break
        print( time.time() - s, 'split')

        s = time.time()
        simpleName = re.compile( '\w+$' )
        for child in cmds.listRelatives(main.name(), ad=True, type='transform'):
        #for child in cmds.ls(type='transform'):
            if simpleName.search(child).group(0) == 'rootMotion':
                #print( child)
                break
        print( time.time() - s, 're')
    '''
    
    if main:
                
        children = cmds.listRelatives(main.name(), ad=True, type='transform', f=True)
        if children:   # cmds returns None instead of emtpy list
            for child in children:
                if child.rsplit('|', 1)[-1].rsplit(':', 1)[-1] == 'rootMotion':
                    return PyNode(child)
                
        return None

    if objExists( 'rootMotion' ):
        return PyNode( 'rootMotion' )
    else:
        rms = ls( 'rootMotion', r=True )
        if len(rms) == 1:
            return rms[0]
    
    return None
    

def allCards(main=None):
    '''
    Return all the cards, optionally taking a specific skeletonBlueprint.
    '''
    
    # Use cmds for speed (swift takes 0.20 with pymel but 0.04 with cmds)
    targetCards = set(
        cmds.ls( '*.skeletonInfo', o=True, r=True, l=True ) +
        cmds.ls( '*.fossilRigData', o=True, r=True, l=True )
    )
    
    if main:
        targetCards.intersection_update( cmds.listRelatives(main.name(), ad=True, type='transform', f=True) )
    
    def order(obj):
        try:
            return cmds.getAttr(obj + '.buildOrder')
        except Exception:
            pass
    
        try:
            return json.loads(cmds.getAttr(obj + '.fossilRigData')).get('buildOrder', 10)
        except Exception:
            pass
    
        return 10
    
    return [PyNode(c) for c in sorted(targetCards, key=order)]
    
    
def mainBlueprint():
    bps = ls( 'skeletonBlueprint', r=1)

    for obj in bps:
        if not obj.getParent():
            return obj