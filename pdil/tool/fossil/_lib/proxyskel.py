'''
Contains the utilites to build the unselectable proxy skeleton.
'''

from pymel.core import delete, joint, pointConstraint, listRelatives, group, objExists, ls, PyNode

from pdil import simpleName, shortName
import pdil

from .._core import find

_DEFAULT_PROXY_RADIUS = 0.70


def _clearLink(proxy):
    '''
    If the given proxy has a card interlink, it will be removed.
    '''
    if not proxy.hasAttr('cardLink'):
        return

    link = proxy.cardLink.listConnections()
    if link:
        delete(link)


def _recordLink(proxy, link):
    '''
    Connect the given proxy to the card interlink joint.
    '''
    if not proxy.hasAttr('cardLink'):
        proxy.addAttr('cardLink', at='message')

    link.message >> proxy.cardLink


def _delLink(proxy):
    if proxy.hasAttr('cardLink'):
        con = proxy.cardLink.listConnections()

        if con:
            delete(con)


def makeProxy(tempJoint, parent=None, radius=_DEFAULT_PROXY_RADIUS):
    tempJoint.proxy = joint(parent)
    tempJoint.proxy.radius.set(radius)
    pointConstraint( tempJoint, tempJoint.proxy )
    return tempJoint


def pointer(parent, child):
    '''
    Makes proxy joints for two TempJoints so the hierarchical relationship can be drawn.
    
    ..  todo:: I think the actual connection logic might move to BPJoint.setParent
    '''

    assert type(parent).__name__ == type(child).__name__ == 'BPJoint', 'Both must be TempJoints'

    if not parent.attr('children').isConnectedTo( child.attr('parent') ):
        parent.attr('children') >> child.attr('parent')

    proxyRadius = _DEFAULT_PROXY_RADIUS
    try:
        proxyRadius = parent.parent.proxy.radius.get()
    except:
        pass
    grp = getProxyGroup()

    if not child.proxy:
        makeProxy( child, grp, child.radius.get() * _DEFAULT_PROXY_RADIUS )

    if not parent.proxy:
        makeProxy( parent, grp, parent.radius.get() * _DEFAULT_PROXY_RADIUS )

    # If card parentage is established, manage vis
    if parent.cardCon.node() != child.cardCon.node():
        parentCardName = simpleName(parent.cardCon.node())
        childCardName = simpleName(child.cardCon.node())

        child.proxy.setParent( grp )

        linkStart = joint(grp)
        linkStart.radius.set( parent.radius.get() * proxyRadius)
        linkEnd = joint(linkStart)
        linkEnd.radius.set( child.radius.get() * proxyRadius)

        pointConstraint( parent, linkStart )
        pointConstraint( child, linkEnd )

        pdil.math.multiply( parent.cardCon.node().v, child.cardCon.node().v) >> linkStart.v

        if not child.cardCon.node().v.isConnectedTo(child.v):
            child.cardCon.node().v >> child.v

        if not child.v.isConnectedTo(child.proxy.v):
            child.v >> child.proxy.v

        _clearLink( child.proxy )
        _recordLink( child.proxy, linkStart )

        child.proxy.rename( childCardName + '_proxy' )
        linkStart.rename( parentCardName + '_' + childCardName + '_link' )

    else:
        child.proxy.setParent( parent.proxy )


def unpoint(child):
    '''
    Undoes `pointer()`, making this a 'top level' joint.
    '''

    if not child.parent or not child.proxy:
        return

    if not child.parent.proxy:
        return

    child.proxy.setParent( getProxyGroup() )
    child.v.disconnect()
    child.parent = None
    _delLink( child.proxy )


def getProxyGroup():
    for child in listRelatives(masterGroup(), type='transform' ):
        if child.name() == 'ConnectorProxy':
            return child

    grp = group(em=True, name='ConnectorProxy', p=masterGroup())
    grp.overrideEnabled.set( 1 )
    grp.overrideDisplayType.set( 2 )
    return grp


def masterGroup():
    if not objExists( '|skeletonBlueprint' ):
        
        # First search all namespaces for the toplevel blueprint and return it.
        bps = ls( 'skeletonBlueprint', r=True)

        for obj in bps:
            if not obj.getParent():
                return obj
        
        # Otherwise make it
        grp = group( em=True, n='skeletonBlueprint' )
        grp.t.lock()
        grp.r.lock()
        
        grp.addAttr('generalData', dt='string')
        grp.generalData.set('{}')
        
        try:
            pdil.layer.putInLayer(grp, 'Blueprint')
        except Exception:
            pass

    return PyNode('|skeletonBlueprint')


def relink(src, dup):
    '''
    When a card has been duplicated, relinks the parenting appropriately.

    .. todo:: Does the scaling setup duplicate properly?
    '''
    children = dup.listRelatives(type='joint')
    for i, j in enumerate(src.joints):
        for child in children:
            if shortName(child) == shortName(j):
                child.msg >> dup.attr('joints')[i].jmsg
                dup.scale >> child.inverseScale

    for prev, j in zip( dup.joints[:-1], dup.joints[1:] ):
        pointer( prev, j )

    if src.start().parent:
        pointer( src.start().parent, dup.start() )
        
        
def rebuildConnectorProxy():
    ''' Fully rebuild the proxy from scratch.
    '''
    delete( getProxyGroup() )

    for card in find.blueprintCards():
        for jnt in card.joints:
            for child in jnt.proxyChildren:
                pointer(jnt, child)
                
                
def postDeleteCleanup():
    ''' Remove orphaned proxies, for use after a card was deleted.
    '''
    
    toDelete = [jnt for jnt in getProxyGroup().listRelatives(type='joint') if isOrphaned(jnt)]
    if toDelete:
        delete(toDelete)
        
        
def isOrphaned(jnt):
    ''' Returns True if the joint, or it's child has no constraints, indicated an orphaned proxy or link.
    '''
    if not pointConstraint(jnt, q=True):
        return True
    
    for child in listRelatives(jnt, type='joint'):
        if not pointConstraint(child, q=True):
            return True
    
    return False