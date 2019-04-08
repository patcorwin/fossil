from __future__ import print_function, absolute_import

import re

from pymel.core import Callback, confirmDialog, ls, select, selected, warning

from .... import core
from .... import lib


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
            
        match = re.match( '[\w0-9]*', name )
        if not match:
            warning( "The group name isn't valid" )
            return

        if match.group(0) != name:
            warning( "The group name isn't valid" )
            return
        
        level = self.ui.groupLevel.value()
        
        for obj in selected():
            lib.sharedShape.connect( obj, (name, level) )
        
        self.update()
        select( sel )
            
    def equip(self):
        sel = selected()
        for obj in selected():
            lib.sharedShape.use( obj )
        select( sel )
    
    def unequip(self):
        sel = selected()
        for obj in selected():
            if lib.sharedShape.find(obj):
                lib.sharedShape.remove( obj )
        select( sel )
        
    def prune(self):
        lib.sharedShape.pruneUnused()
        self.update()
        
    def update(self):
        self.ui.visGroups.clear()
        self.ui.visGroups.addItems( lib.sharedShape.existingGroups() )
    
    def tagMain(self):
        
        obj = selected()[0]
        
        main = ls('*.' + core.findNode.MAIN_CONTROL_TAG)
        if main:
            # Already tagged as main
            if main[0].node() == obj:
                return

            if confirmDialog( m='{} is already tagged, are you sure want to make {} the main?'.format(main[0].node(), obj),
                    b=['Yes', 'No'] ) == 'Yes':
                main[0].node().deleteAttr(core.findNode.MAIN_CONTROL_TAG)
            else:
                return
        
        core.findNode.tagAsMain(obj)
        
        self.update()