from __future__ import print_function, absolute_import
from functools import partial
import json
import itertools


from ...vendor.Qt import QtWidgets, QtCore
from ...vendor.Qt.QtCore import Qt

from pymel.core import delete, select, selected, PyNode

import pdil

from ._core import find
from ._lib import proxyskel
from . import util

try:
    basestring # noqa
except NameError: # python 3 compatibility
    basestring = str


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
    
    def __init__(self, *args, **kwargs):
        QtWidgets.QTableWidget.__init__(self, *args, **kwargs)
        self.displayedCard = None
        self.installEventFilter(self)
        
        pdil.pubsub.subscribe('fossil joint added', self.jointListerRefresh)
        
        
    class FORCE_UPDATE:
        pass
    
    
    def eventFilter(self, obj, event):
        ''' Allow copy/paste of joint parent and orient data
        '''
        column = self.currentColumn()
        if event.type() == QtCore.QEvent.Type.KeyPress \
                and column in (self.JOINT_LISTER_ORIENT, self.JOINT_LISTER_CHILDOF):
            
            row = self.currentRow()
            
            if event.key() == QtCore.Qt.Key_C:
                if QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ControlModifier:
                    
                    bpJoint = self.displayedCard.joints[row]
                    
                    if column == self.JOINT_LISTER_CHILDOF:
                        parent = bpJoint.parent
                        mirror = bpJoint.info.get('mirroredSide', False)
                    
                        data = {'fossil_parent': {
                            'name': parent.name(),
                            'mirroredSide': mirror,
                            'text': self.item(row, column).text()
                        } }
                        pdil.text.clipboard.set( json.dumps(data) )
                    
                    elif column == self.JOINT_LISTER_ORIENT:
                        target = self.item(row, column).text()
                        
                        data = {'fossil_orient': { 'target': target if target else None } }
                        
                        pdil.text.clipboard.set( json.dumps(data) )
                    
                    return True
                    
            elif event.key() == QtCore.Qt.Key_V:
                if QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ControlModifier:
                    bpJoint = self.displayedCard.joints[row]
                                        
                    if column == self.JOINT_LISTER_CHILDOF:
                        try:
                            data = json.loads(pdil.text.clipboard.get())
                            parent = PyNode(data['fossil_parent']['name']) if data['fossil_parent']['name'] else None
                            mirror = data['fossil_parent']['mirroredSide']
                            text = data['fossil_parent']['text']
                                                    
                        except Exception:
                            return False
                        
                        self.changeParent( bpJoint, parent, mirror, row, text)
                    
                    elif column == self.JOINT_LISTER_ORIENT:
                        try:
                            data = json.loads(pdil.text.clipboard.get())
                            newTarget = data['fossil_orient']['target']
                            
                            if newTarget not in (None, '-as card-', '-as proxy-', '-world-'):
                                newTarget = PyNode(newTarget)
                            
                        except Exception:
                            return False
                            
                        self.setOrientTarget(row, bpJoint, newTarget)
                    
                    return True
        
        '''
        if obj == self.ui.entry and event.type() == QtCore.QEvent.Type.KeyPress:
            if self.option_count:
                if event.key() == QtCore.Qt.Key_Up:
                    self.ui.options.setCurrentRow( (self.ui.options.currentRow() - 1) % self.option_count)
                    
                elif event.key() == QtCore.Qt.Key_Down:
                    self.ui.options.setCurrentRow( (self.ui.options.currentRow() + 1) % self.option_count)
                    
                elif event.key() == QtCore.Qt.Key_Return:
                    print('RUN')
        '''
        #return super(self).eventFilter(obj, event)
        return QtWidgets.QTableWidget.eventFilter(self, obj, event)
    
    
    def setup(self, scale=1.0):
        '''
        Since the widget is really built in the setupUi() call, some gui editing
        work must happen afterwards (adjusting the columns).  Other things could
        be done in __init__ but might as well do it all in one place.
        '''
        for i, cw in enumerate(self.jointListerColumnWidths):
            self.setColumnWidth(i, cw * scale)
        
        self.joints = []
        
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.jointListerRightClick)
        
        self.itemClicked.connect(self.clicked)
    
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
            #t  = pdil.debug.Timer('ChildOf')
            menu = QtWidgets.QMenu()
            menu.addAction('-Clear-').triggered.connect( partial(self.changeParent, bpJoint, None, False, row, '') )
            
            for card in sorted(find.blueprintCards()):
                outputMap = card.getOutputMap(includeHelpers=False)
                
                if not outputMap:
                    continue
                
                subMenu = menu.addMenu( pdil.simpleName(card) )
                
                for bpj, names in sorted(outputMap.items()):
                    subMenu.addAction( names[0] ).triggered.connect( partial(self.changeParent, bpJoint, bpj, False, row, names[0]))
                    
                    if len(names) > 1:
                        subMenu.addAction( names[1] ).triggered.connect( partial(self.changeParent, bpJoint, bpj, True, row, names[1]))
            #t.stop()
            #t.results()
            menu.exec_(self.viewport().mapToGlobal(position))
        
        elif col == self.JOINT_LISTER_ORIENT:
            
            menu = QtWidgets.QMenu()
            menu.addAction('-clear-').triggered.connect( partial(self.setOrientTarget, row, bpJoint, None) )
            menu.addAction('-world-').triggered.connect( partial(self.setOrientTarget, row, bpJoint, '-world-') )
            menu.addAction('-as parent-').triggered.connect( partial(self.setOrientTarget, row, bpJoint, '-as parent-') )
            menu.addAction('-as card-').triggered.connect( partial(self.setOrientTarget, row, bpJoint, '-as card-') )
            menu.addAction('-as proxy-').triggered.connect( partial(self.setOrientTarget, row, bpJoint, '-as proxy-') )
            #menu.addAction('-custom-') ?????? &&& ???
            
            #joints = util.listTempJoints(includeHelpers=True)
            #for j in joints:
            #    menu.addAction(pdil.simpleName(j)).triggered.connect( partial(self.setOrientTarget, row, bpJoint, j) )
            
            for card in sorted(find.blueprintCards()):
                outputMap = card.getOutputMap(includeHelpers=True)
                
                if not outputMap:
                    continue
                
                subMenu = menu.addMenu( pdil.simpleName(card) )
                
                for bpj, names in sorted(outputMap.items()):
                    if names[0]:
                        subMenu.addAction( names[0] ).triggered.connect( partial(self.setOrientTarget, row, bpJoint, bpj) )
                    else:
                        subMenu.addAction( pdil.simpleName(bpj) + ' - Helper' ).triggered.connect( partial(self.setOrientTarget, row, bpJoint, bpj) )
            
            menu.exec_(self.viewport().mapToGlobal(position))
    
    def changeParent(self, bpJoint, newParent, mirroredSide, row, text):
        currentSelection = selected()
        # &&& Move setting info to a param of setBPParent()
        info = bpJoint.info
        self.item(row, self.JOINT_LISTER_CHILDOF).setText(text)
        
        if newParent is None:
            bpJoint.setBPParent(None)
            info.setdefault('options', {})['mirroredSide'] = False
            proxyskel.unpoint( bpJoint )
        
        elif not mirroredSide:
            bpJoint.setBPParent(newParent)
            info.setdefault('options', {})['mirroredSide'] = False
            proxyskel.pointer( newParent, bpJoint )
        
        else:
            bpJoint.setBPParent(None)
            info.setdefault('options', {})['mirroredSide'] = True
            proxyskel.pointer( newParent, bpJoint )
            
        bpJoint.info = info
        
        if currentSelection:
            select(currentSelection)
        
    
    def setOrientTarget(self, row, bpJoint, newTarget):
        
        if newTarget is None:
            bpJoint.orientTarget = None
            self.clearCustomOrient(bpJoint)
            self.item(row, self.JOINT_LISTER_ORIENT).setText('')

        elif newTarget == '-as parent-':
            bpJoint.orientTarget = '-as parent-'
            self.clearCustomOrient(bpJoint)
            self.item(row, self.JOINT_LISTER_ORIENT).setText('-as parent-')
        
        elif newTarget == '-as card-':
            bpJoint.orientTarget = None
            bpJoint.customOrient = bpJoint.card
            self.item(row, self.JOINT_LISTER_ORIENT).setText('-as card-')
        
        elif newTarget == '-as proxy-':
            bpJoint.orientTarget = None
            bpJoint.customOrient = bpJoint
            self.item(row, self.JOINT_LISTER_ORIENT).setText('-as proxy-')
        
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
            self.item(row, self.JOINT_LISTER_ORIENT).setText(pdil.simpleName(newTarget))
            bpJoint.orientTarget = newTarget
            bpJoint.customOrient = None
        
    @classmethod
    def clearCustomOrient(cls, tempJoint):
        if tempJoint.customOrient:
            if len(tempJoint.customOrient.message.listConnections()) == 1:
                delete(tempJoint.customOrient)
            else:
                tempJoint.customOrient = None
                        
    def jointListerAddRow(self, ctr, tempJoint, name, card, parentCard):
        index = next(ctr)
        
        jointName = pdil.shortName(tempJoint)
        self.setItem( index, self.JOINT_LISTER_NAME, Cell(jointName) )

        cb = Cell(checked=tempJoint.isHelper)
        self.setItem( index, self.JOINT_LISTER_HELPER, cb)
        
        self.setItem( index, self.JOINT_LISTER_OUTPUT, Cell(name))
        
        cb = Cell(checked=tempJoint.displayHandle.get())
        self.setItem( index, self.JOINT_LISTER_HANDLES, cb)
        
        # --- Orient ---
        orientText = ''
        if tempJoint.customOrient:
            
            if tempJoint.customOrient == tempJoint.card:
                orientText = '-as card-'
            elif tempJoint.customOrient == tempJoint:
                orientText = '-as proxy-'
            else:
                orientText = 'custom:' + pdil.shortName(tempJoint.customOrient)
            
        elif isinstance(tempJoint.orientTarget, basestring):
            orientText = tempJoint.orientTarget
        elif tempJoint.orientTarget:
            orientText = pdil.shortName(tempJoint.orientTarget)
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
                parentName = '!helper! ' + pdil.simpleName(tempJoint.parent)
        
        elif tempJoint.extraNode[0]:
            outputMap = tempJoint.extraNode[0].card.getOutputMap(includeHelpers=False)
            parentName = outputMap[tempJoint.extraNode[0]][1]
        
        else:
            parentName = ''
        
        self.setItem( index, self.JOINT_LISTER_CHILDOF, Cell(parentName))