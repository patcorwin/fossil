from __future__ import print_function

from pymel.core import hide, showHidden, selected, select

from .. import _core as core
from ..nodeApi import fossilNodes
from ..tool import fossil

class QuickHideControls(object):
    '''
    Toggle the visibility of the selected rig controls.
    '''
    
    controlsToHide = []
    hideMain = False
    mainShapes = None

    @staticmethod
    @core.alt.name( 'Quick Hide Controls', 'Anim')
    def act():
        if not QuickHideControls.controlsToHide or all( [not o.exists() for o in QuickHideControls.controlsToHide] ):
            QuickHideControls.start()
        else:
            QuickHideControls.end()
    
    @classmethod
    def start(cls):
        temp = fossil.find.controllers()
        ctrls = temp[:-2]  # Cut out the main controller and root motion
        
        # Artificially add the parents of the selected controls so they are hidden as a result
        selectedControls = set(selected())
        for ctrl in selected():
            if type(ctrl) in (fossilNodes.SubController, fossilNodes.RigController):
                selectedControls.update(ctrl.getAllParents())
        
        # Hide the spaces since the controls vis is locked and hidden to prevent accidentally being keyed hidden.
        cls.controlsToHide = set( ctrls ).difference( selectedControls )
        for obj in cls.controlsToHide:
            hide(obj.getParent(), obj.getParent().getParent())
        
        main = temp[-2]
        cls.hideMain = main not in selectedControls
        
        if cls.hideMain:
            cls.mainShapes = core.shape.getNurbsShapes(main)
            hide(cls.mainShapes)
            print( 'hide main', cls.mainShapes[0].isVisible() )
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
                  
        
@core.alt.name('Select Related Controllers', 'Anim')
def selectRelatedControllers():
    '''
    If any controllers are selected, all siblings are also selected.
    '''
    for obj in selected():
        main = fossil.node.leadController(obj)
        if main:
            for name, ctrl in main.subControl.items():
                select(ctrl, add=True)
            select(main, add=True)
            
            
@core.alt.name('Select Children Controllers', 'Anim')
def selectChildrenControllers():
    '''
    If any controllers are selected, any subsequent controllers are selected.
    '''
    for obj in selected():
        main = fossil.node.leadController(obj)
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