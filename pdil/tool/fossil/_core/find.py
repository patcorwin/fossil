'''
These only find the node(s) if it exists, other functions might wrap creation if not found.
'''
from __future__ import print_function, absolute_import

import json

from pymel.core import attributeQuery, cmds, PyNode, warning, objExists, ls

from pdil import simpleName
from . import config


def rootBone(nodes=None):
    '''
    Returns the root bone, trying to account for case and namespaces or None if
    not found.  `make` should be either 'root' or 'weaponRoot', specifying which
    to make (always top level) if a root is not found.
    
    Can be given a list of nodes to search for the root,
    '''

    names = [config._settings['root_name']]

    if not nodes:
        # Check if any exist top level first
        top = ls(assemblies=True)
        for name in names:
            if name in top:
                return PyNode('|' + name)
    
    # See if there is a top level obj in a namespace named b_root of any casing.
    searchNodes = nodes if nodes else ls( assemblies=True )
    nodes = [obj for obj in searchNodes if simpleName( obj ).lower() in names]
    if len(nodes) == 1:
        return nodes[0]

    # Then check if any exist at all (which will fail if several exist in separate groups).
    for name in names:
        if objExists( name ):
            return PyNode( name )

    return None


def controllers(main=None):
    '''
    Returns all the animation controllers in the scene.
    
    ..  todo:: Add the shapes that have ik/fk switching on them
    '''
    
    allControls = set( cmds.ls( '*.' + config.FOSSIL_CTRL_TYPE, o=True, r=True, l=True ) )
    
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


def mainGroup(nodePool=None, fromControl=None):
    ''' Returns the main group, intended for building the rig where a single main group is assumed, unless nodePool is used.
    
    Args:
        nodePool: A list of possible nodes (like the results of importing/referencing)
        fromControl: Find the mainGroup in the hierarchy of this control
        
    TODO: At some point, (2023?) remove all the 'main' name assumptions and only use the attribute.
    '''
    
    if fromControl:
        path = fromControl.fullPath().split('|')[1:]
        for i, name in enumerate(path):
            if attributeQuery( config.FOSSIL_MAIN_CONTROL, ex=True, node=name ):
                return PyNode('|' + '|'.join( path[:i + 1] ))

    if nodePool:
        for n in nodePool:
            if n.hasAttr(config.FOSSIL_MAIN_CONTROL) or simpleName(n) == 'main':
                return n
    
    if objExists('|main'):
        return PyNode('|main')
    else:
        # A pymel bug is sometimes returning duplicate nodes
        main = list(set([ obj for obj in ls( 'main', r=True) if not obj.getParent() ]))
        if len(main) == 1:
            return main[0]
    
    # No "main" ojbect was found, looking for tags
    plugs = ls('*.' + config.FOSSIL_MAIN_CONTROL)
    if plugs:
        return plugs[0].node()
    
    return None


def mainGroups():
    ''' Returns all main groups, intended for animation tools to manage multiple characters.
    '''
    return ls( '*.' + config.FOSSIL_MAIN_CONTROL, o=True, r=True )


def rootMotion(main=None):
    ''' Returns the root motion, if main is specified, search that node.
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
    

def blueprintCards(skeletonBlueprint=None):
    ''' Return all the cards, optionally taking a specific skeletonBlueprint.
    '''
    
    targetCards = set(
        cmds.ls( '*.skeletonInfo', o=True, r=True, l=True )
        + cmds.ls( '*.fossilRigData', o=True, r=True, l=True )
    )
    
    if skeletonBlueprint:
        targetCards.intersection_update( cmds.listRelatives(skeletonBlueprint.name(), ad=True, type='transform', f=True) )
    
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


def cardJointBuildOrder():
    '''
    Returns the cards in the order joints should be built in.  Spaces complicate
    the rig build order, but this is probably a good 'build' order too, then
    space application comes again for all at the end.
    
    I think I can just use the cardHierarchy instead.
    '''
    
    cards = [temp[0] for temp in cardHierarchy()]
    
    return cards[1:]


def cardHierarchy():
    '''
    Returns a list of:
        [
            [ parentCardA, [<children cards of A>] ],
            [ parentCardB, [<children cards of B>] ],
            ...
        ]
    '''
    parentCards = [[None, []]]
    
    mirrored = {}
    
    # Also track parent and their children so we can lookup to add asymetrically made cards to child list
    parentCardsListed = {}
    
    for card in blueprintCards():
        if not card.parentCard:
            
            # Only pick up cards that are actually top level and not parented to a mirror side
            for j in card.joints:
                
                if j.info.get('options', {}).get('mirroredSide'):
                    mirrored[card] = j.extraNode[0]
                    break
            else:
                parentCards[0][1].append(card)
    
    def gatherChildren(cards):
        for card in cards:
            #ordered.append( card)
            children = card.childrenCards
            parentCards.append( [card, children] )
            parentCardsListed[card] = children
            gatherChildren(children)
            
    gatherChildren(parentCards[0][1])
    
    for card in mirrored:
        gatherChildren([card])
    
        # &&& Worried about the code sprawl due to how "parent" has changed over time.  Should .parentCard already handle this case?
        parentCard = card.parentCardJoint.card
        if parentCard:
            parentCardsListed[parentCard].append( card )
        else:
            raise Exception('How did this happen? {} has mirrored side set but no discernable parent'.format(card) )
    
    
    return parentCards