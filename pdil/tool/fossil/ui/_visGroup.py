from __future__ import print_function, absolute_import

import re

from pymel.core import Callback, confirmDialog, ls, select, selected, warning

import pdil

from .. import _core as core
from .._lib import visNode


class VisGroupLayout( object ):
    
    def __init__( self, ui ):
        
        self.ui = ui
        
        self.update()
        
        self.ui.visGroups.itemSelectionChanged.connect(Callback(self.selectGroup))
                
        self.ui.equipVisControl.clicked.connect(Callback(self.equip))
        self.ui.unequipVisControl.clicked.connect(Callback(self.unequip))
        self.ui.pruneVisGroups.clicked.connect(Callback(self.prune))
        
        self.ui.tagAsMain.clicked.connect(Callback(self.tagMain))
        
        self.ui.assignVisGroup.clicked.connect(Callback(self.assign))
        

    def selectGroup(self):
        self.ui.visGroupNameEntry.setText( self.ui.visGroups.currentItem().text() )
        
    def assign(self):
        sel = selected()
        name = str(self.ui.visGroupNameEntry.text())
        
        if not name:
            warning( 'You must specify a vis group' )
            return
            
        match = re.match( r'[\w0-9]*', name )
        if not match:
            warning( "The group name isn't valid" )
            return

        if match.group(0) != name:
            warning( "The group name isn't valid" )
            return
        
        level = self.ui.groupLevel.value()
        
        for obj in selected():
            visNode.connect( obj, (name, level) )
        
        self.update()
        select( sel )
            
    def equip(self):
        sel = selected()
        for obj in selected():
            pdil.sharedShape.use( obj, visNode.get() )
        select( sel )
    
    def unequip(self):
        sel = selected()
        for obj in selected():
            if pdil.sharedShape.find(obj, visNode.VIS_NODE_TYPE):
                pdil.sharedShape.remove( obj, visNode.VIS_NODE_TYPE )
        select( sel )
        
    def prune(self):
        visNode.pruneUnused()
        self.update()
        
    def update(self):
        self.ui.visGroups.clear()
        self.ui.visGroups.addItems( visNode.existingGroups() )
    
    def tagMain(self):
        
        obj = selected()[0]
        
        main = ls('*.' + core.find.FOSSIL_MAIN_CONTROL)
        if main:
            # Already tagged as main
            if main[0].node() == obj:
                return

            if confirmDialog( m='{} is already tagged, are you sure want to make {} the main?'.format(main[0].node(), obj),
                    b=['Yes', 'No'] ) == 'Yes':
                main[0].node().deleteAttr(core.find.FOSSIL_MAIN_CONTROL)
            else:
                return
        
        core.find.tagAsMain(obj)
        
        self.update()