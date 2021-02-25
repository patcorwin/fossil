
from pymel.core import curve, joint, parentConstraint, pointConstraint, PyNode, objExists
from ... import core

from .core import config


def mainGroup(create=True, nodes=None):
    main = core.findNode.mainGroup()
    
    if main:
        return main
    
    if create:
        # Draw outer arrow shape
        main = curve( name='main', d=True, p=[(-40, 0, 20 ), (0, 0, 60 ), (40, 0, 20 ), (40, 0, -40 ), (0, 0, -20 ), (-40, 0, -40 ), (-40, 0, 20 )] )
        core.dagObj.lockScale(main)
        main.visibility.setKeyable(False)
        main.visibility.set(cb=True)
    
        core.findNode.tagAsMain(main)
        
        if True:  # Put it in a default group
            core.layer.putInLayer(main, 'Controls')
        return main
    
    return None
    
    
    
def getTrueRoot():
    ''' Returns the root joint according the 'root_name', building it if needed.
    
    &&& DUPLICATED CODE IN fossileNodes
    '''
    rootName = config._settings['root_name']
    
    trueRoot = PyNode(rootName) if objExists( rootName ) else joint(None, n=rootName)
    trueRoot.drawStyle.set(2)
    return trueRoot
    
    
def rootMotion(create=True, main=None):
    rootMotion = core.findNode.rootMotion(main)
    
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
        core.dagObj.lockScale( rootMotion )
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