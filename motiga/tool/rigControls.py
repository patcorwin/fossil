from pymel.core import hide, showHidden, selected, select

from .. import core


class QuickHideControls(object):
    
    controlsToHide = []
    hideMain = False
    mainShapes = None
    
    @classmethod
    def start(cls):
        temp = core.findNode.controllers()
        ctrls = temp[:-2]  # Cut out the main controller and root motion
        cls.controlsToHide = set( ctrls ).difference( selected() )
        for obj in cls.controlsToHide:
            hide(obj.getParent(), obj.getParent().getParent())
        
        main = temp[-2]
        cls.hideMain = main not in selected()
        
        if cls.hideMain:
            cls.mainShapes = core.shape.getShapes(main)
            hide(cls.mainShapes)
            print 'hide main', cls.mainShapes[0].isVisible()
            if cls.mainShapes[0].isVisible():
                plug = cls.mainShapes[0].visibility.listConnections(s=True, p=True)
                if plug:
                    plug[0].set(0)
        
    @classmethod
    def end(cls):
        for obj in cls.controlsToHide:
            showHidden(obj.getParent(), obj.getParent().getParent())
        
        cls.controlsToHide = []
    
        if cls.hideMain:
            showHidden(cls.mainShapes)
            if not cls.mainShapes[0].isVisible():
                plug = cls.mainShapes[0].visibility.listConnections(s=True, p=True)
                if plug:
                    plug[0].set(1)
    
    @staticmethod
    @core.alt.name( 'Quick Hide Controls' )
    def act():
        if not QuickHideControls.controlsToHide or all( [not o.exists() for o in QuickHideControls.controlsToHide] ):
            QuickHideControls.start()
        else:
            QuickHideControls.end()
                  
        
@core.alt.name('Select Related Controllers')
def selectRelatedControllers():
    '''
    If any controllers are selected, all siblings are also selected.
    '''
    for obj in selected():
        main = core.findNode.leadController(obj)
        if main:
            for name, ctrl in main.subControl.items():
                select(ctrl, add=True)
            select(main, add=True)
            
            
@core.alt.name('Select Children Controllers')
def selectChildrenControllers():
    '''
    If any controllers are selected, any subsequent controllers are selected.
    '''
    for obj in selected():
        main = core.findNode.leadController(obj)
        if main == obj:
            for name, ctrl in main.subControl.items():
                select(ctrl, add=True)
            select(main, add=True)
        else:
            doSelect = False
            for name, ctrl in main.subControl.items():
                if ctrl == obj:
                    doSelect = True
                if doSelect:
                    select(ctrl, add=True)