from __future__ import print_function, absolute_import
from functools import partial
import itertools

from Qt import QtWidgets, QtCore
from Qt.QtCore import Qt

from pymel.core import delete, select

from ... import add
from ... import core
from . import proxy
from . import util


class Cell(QtWidgets.QTableWidgetItem):
    
    def __init__(self, label='', checked=None):
        QtWidgets.QTableWidgetItem.__init__(self, label)
        self.setFlags( Qt.ItemIsEnabled | Qt.ItemIsSelectable )

        if checked is not None:
            self.setCheckState(Qt.Checked if checked else Qt.Unchecked)


class JointLister(QtWidgets.QTableWidget):
    
    jointListerColumnWidths = [120, 50, 120, 50, 120, 120, 50]
    
    JOINT_LISTER_NAME = 0
    JOINT_LISTER_HELPER = 1
    JOINT_LISTER_OUTPUT = 2
    JOINT_LISTER_HANDLES = 3
    JOINT_LISTER_ORIENT = 4
    JOINT_LISTER_CHILDOF = 5
                
    class FORCE_UPDATE:
        pass
    
    def setup(self):
        '''
        Since the widget is really built in the setupUi() call, some gui editing
        work must happen afterwards (adjusting the columns).  Other things could
        be done in __init__ but might as well do it all in one place.
        '''
        for i, cw in enumerate(self.jointListerColumnWidths):
            self.setColumnWidth(i, cw)
        
        self.joints = []
        
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.jointListerRightClick)
        
        self.itemClicked.connect(self.clicked)
        
        self.displayedCard = None
    
    def clicked(self, item):
        '''
        When an item is clicked, possibly do something, like change data based
        on a checkbox state.
        '''
        row = self.row(item)
        col = self.column(item)
        
        bpJoint = self.joints[row]
        
        if col == self.JOINT_LISTER_NAME:
            select(None)
            for r in self.selectedRanges():
                if r.rowCount() > 1:
                    select(self.joints[r.topRow(): r.bottomRow() + 1], add=True)
                else:
                    select(self.joints[r.topRow()], add=True)
        
        elif col == self.JOINT_LISTER_HELPER:
            # The "right" way is to make the item with the flag Qt.ItemIsUserCheckable but
            # clicking the column is much easier/user friendly
            item.setCheckState( Qt.Checked if item.checkState() == Qt.Unchecked else Qt.Unchecked )
            
            bpJoint.isHelper = item.checkState() == Qt.Checked
        
        elif col == self.JOINT_LISTER_HANDLES:
            item.setCheckState( Qt.Checked if item.checkState() == Qt.Unchecked else Qt.Unchecked )
            bpJoint.displayHandle.set( item.checkState() == Qt.Checked )
    
    def jointListerRefresh(self, card=FORCE_UPDATE):
        if self.displayedCard == card:
            return
        
        if card is self.FORCE_UPDATE:
            card = self.displayedCard
        else:
            self.displayedCard = card
        
        self.clearContents()
        self.joints = []
        
        ctr = itertools.count()
        self.setRowCount(0)
        
        if not card:
            return
        
        # Actually build the ui
        temp = card.getOutputMap(includeHelpers=True)
        names = [ n[0] for n in temp.values() ]
        names += ['<too few names>'] * ( len(card.joints) - len(names) )
        
        parentCard = card.parentCard
        
        self.setRowCount( self.rowCount() + len(names) )
        
        for i, (jnt, name) in enumerate(zip(card.joints, names)):
            self.jointListerAddRow( ctr, jnt, name, card, parentCard)
            self.joints.append(jnt)
    
    def refreshHighlight(self):
        sel = set(util.selectedJoints())
        
        for row in range(self.rowCount()):
            item = self.item(row, 0)

            if item.isSelected() != (self.joints[row] in sel):
                item.setSelected(self.joints[row] in sel)
    
    def jointListerRightClick(self, position):
        item = self.itemAt(position)
        
        row = self.row(item)
        col = self.column(item)
        
        bpJoint = self.joints[row]
        
        if col == self.JOINT_LISTER_CHILDOF:
            menu = QtWidgets.QMenu()
            menu.addAction('-Clear-').triggered.connect( partial(self.changeParent, row, bpJoint, '') )
            
            for card in sorted(core.findNode.allCards()):
                outputMap = card.getOutputMap(includeHelpers=False)
                
                if not outputMap:
                    continue
                
                subMenu = menu.addMenu( add.simpleName(card) )
                
                for bpj, names in sorted(outputMap.items()):
                    subMenu.addAction( names[0] ).triggered.connect( partial(self.changeParent, bpJoint, bpj, False, row, names[0]))
                    
                    if len(names) > 1:
                        subMenu.addAction( names[1] ).triggered.connect( partial(self.changeParent, bpJoint, bpj, True, row, names[1]))
            
            menu.exec_(self.viewport().mapToGlobal(position))
        
        elif col == self.JOINT_LISTER_ORIENT:
            menu = QtWidgets.QMenu()
            menu.addAction('-clear-').triggered.connect( partial(self.setOrientTarget, row, bpJoint, None) )
            menu.addAction('-world-').triggered.connect( partial(self.setOrientTarget, row, bpJoint, '-world-') )
            #menu.addAction('-custom-') ?????? &&& ???
            
            #joints = util.listTempJoints(includeHelpers=True)
            #for j in joints:
            #    menu.addAction(add.simpleName(j)).triggered.connect( partial(self.setOrientTarget, row, bpJoint, j) )
            
            for card in sorted(core.findNode.allCards()):
                outputMap = card.getOutputMap(includeHelpers=True)
                
                if not outputMap:
                    continue
                
                subMenu = menu.addMenu( add.simpleName(card) )
                
                for bpj, names in sorted(outputMap.items()):
                    if names[0]:
                        subMenu.addAction( names[0] ).triggered.connect( partial(self.setOrientTarget, row, bpJoint, bpj) )
                    else:
                        subMenu.addAction( add.simpleName(bpj) + ' - Helper' ).triggered.connect( partial(self.setOrientTarget, row, bpJoint, bpj) )
            
            menu.exec_(self.viewport().mapToGlobal(position))
    
    def changeParent(self, bpJoint, newParent, mirroredSide, row, text):
        info = bpJoint.info
        self.item(row, self.JOINT_LISTER_CHILDOF).setText(text)
        
        if newParent is None:
            bpJoint.setBPParent(None)
            info.setdefault('options', {})['mirroredSide'] = False
            proxy.pointer( newParent, bpJoint )
        
        elif not mirroredSide:
            bpJoint.setBPParent(newParent)
            info.setdefault('options', {})['mirroredSide'] = False
            proxy.pointer( newParent, bpJoint )
        
        else:
            bpJoint.setBPParent(None)
            info.setdefault('options', {})['mirroredSide'] = True
            proxy.pointer( newParent, bpJoint )
            
        bpJoint.info = info
    
    def setOrientTarget(self, row, bpJoint, newTarget):
        
        if newTarget is None:
            bpJoint.orientTarget = None
            self.clearCustomOrient(bpJoint)
            self.item(row, self.JOINT_LISTER_ORIENT).setText('')
        
        elif newTarget == '-world-':
            '''
            ..  todo:: Make a pass to fix the old stuff then remove the code
                rebuilding the attr if needed.
            '''
            
            # Since this used to be a message attr, rebuild it (as a string)
            if bpJoint.hasAttr('orientTargetJnt') and bpJoint.orientTargetJnt.type() == 'message':
                bpJoint.deleteAttr('orientTargetJnt')
            
            bpJoint.orientTarget = '-world-'
            #textFieldButtonGrp(field, e=True, tx='-world-')
            self.item(row, self.JOINT_LISTER_ORIENT).setText('-world-')
            self.clearCustomOrient(bpJoint)
            
        else:
            self.item(row, self.JOINT_LISTER_ORIENT).setText(add.simpleName(newTarget))
            bpJoint.orientTarget = newTarget
        
    @classmethod
    def clearCustomOrient(cls, tempJoint):
        if tempJoint.customOrient:
            if len(tempJoint.customOrient.message.listConnections()) == 1:
                delete(tempJoint.customOrient)
            else:
                tempJoint.customOrient = None
                        
    def jointListerAddRow(self, ctr, tempJoint, name, card, parentCard):
        index = ctr.next()
        
        jointName = add.shortName(tempJoint)
        self.setItem( index, self.JOINT_LISTER_NAME, Cell(jointName) )

        cb = Cell(checked=tempJoint.isHelper)
        self.setItem( index, self.JOINT_LISTER_HELPER, cb)
        
        self.setItem( index, self.JOINT_LISTER_OUTPUT, Cell(name))
        
        cb = Cell(checked=tempJoint.displayHandle.get())
        self.setItem( index, self.JOINT_LISTER_HANDLES, cb)
        
        # --- Orient ---
        orientText = ''
        if tempJoint.customOrient:
            orientText = add.shortName(tempJoint.customOrient)
        elif isinstance(tempJoint.orientTarget, basestring):
            orientText = tempJoint.orientTarget
        elif tempJoint.orientTarget:
            orientText = add.shortName(tempJoint.orientTarget)
        self.setItem( index, self.JOINT_LISTER_ORIENT, Cell(orientText))
        
        # --- parent ---
        
        if tempJoint.parent:
            # Technically this will fail if there is a helper also has a child (which is just fine, just not useful)
            outputMap = tempJoint.parent.card.getOutputMap(includeHelpers=True)
            if tempJoint.info.get('options', {}).get('mirroredSide'):
                parentName = outputMap[tempJoint.parent][1]
            else:
                parentName = outputMap[tempJoint.parent][0]
            
            if not parentName:  # This being empty means the parent is a helper
                parentName = '!helper! ' + add.simpleName(tempJoint.parent)
        
        elif tempJoint.extraNode[0]:
            outputMap = tempJoint.extraNode[0].card.getOutputMap(includeHelpers=False)
            parentName = outputMap[tempJoint.extraNode[0]][1]
        
        else:
            parentName = ''
        
        self.setItem( index, self.JOINT_LISTER_CHILDOF, Cell(parentName))