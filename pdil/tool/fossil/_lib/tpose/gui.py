from __future__ import absolute_import, division, print_function

from collections import namedtuple, OrderedDict
import inspect
import json
import os

from pymel.core import Callback, confirmDialog, listRelatives, scriptJob, select, selected

import pdil
from pdil.vendor import Qt

from ... import util

from ..._core import ids
from ..._core import find

from . import adjusters
from .tpcore import updateReposers, getReposeRoots, goToBindPose

ReposerGUI = pdil.ui.getQtUIClass( os.path.dirname(os.path.dirname(os.path.dirname(__file__))) + '/ui/reposer_gui.ui', 'pdil.tool.fossil.ui.reposer_gui')


Adjust = namedtuple('Adjust', 'order card data')


class GUI(Qt.QtWidgets.QMainWindow):
    
    MAX_INPUTS = 3
    
    def __init__(self):
    
        windowName = 'tpose_edit_adjustments'
        pdil.ui.deleteByName(windowName)
                

        self.settings = pdil.ui.Settings( 'Fossil Reposer GUI Settings',
            {
                'headers': [100, 40, 80],
                #geometry is added on close
            })
        
        objectName = 'Reposer'
        pdil.ui.deleteByName(objectName)
        
        super(GUI, self).__init__(pdil.ui.mayaMainWindow())
        
        self.setAttribute(Qt.QtCore.Qt.WA_DeleteOnClose) # Ensure it deletes instead of hides.
        
        self.setObjectName(windowName)
        scriptJob(p=windowName, e=('PostSceneRead', self.sceneChange))
        scriptJob(p=windowName, e=('NewSceneOpened', self.sceneChange))
        scriptJob(p=windowName, e=('SelectionChanged', self.selectionChanged))
        
        self.ui = ReposerGUI()
        self.ui.setupUi(self)
        
        self.ui.updateAll.clicked.connect(Callback(self.updateReposersWithProgress))
        self.ui.updateSelected.clicked.connect(Callback(self.runOnSelected, self.updateReposersWithProgress))
        
        self.ui.runAll.clicked.connect( Callback(self.runAdjustementsWithProgress) )
        self.ui.runSelected.clicked.connect( Callback(self.runOnSelected, self.runAdjustementsWithProgress) )
        
        self.setObjectName(objectName)
        self.setWindowTitle('Reposer')
        
        self.listAdjustments()
        
        self.entry = {0: {}, 1: {}, 2: {}}
        
        self.ui.cardChooser.currentTextChanged.connect(self.setOptions)
        self.ui.adjustmentChooser.addItems( [''] + [k for k in adjusters.adjustCommands.keys() if k[0] != '_']  )
        self.ui.adjustmentChooser.currentTextChanged.connect(self.setOptions)
        
        self.ui.addAdjustment.clicked.connect(self.addAdjustment)

        self.ui.removeAdjustment.clicked.connect(self.removeAdjustment)
        
        self.ui.goToBind.clicked.connect(goToBindPose)

        self.setOptions()
        
        # Load position settings
        header = self.ui.aligns.horizontalHeader()
        for col, width in enumerate(self.settings['headers']):
            header.resizeSection(col, width)
        
        self.show()
        
        if 'geometry' in self.settings:
            pdil.ui.setGeometry( self, self.settings['geometry'] )


        self.ui.aligns.cellChanged.connect(self.argUpdate)
        
        self.selectionChanged()
        
    
    def selectionChanged(self):
        sel = selected()
        if sel and sel[0].name() in self.cardNames:
            self.ui.cardChooser.setCurrentText( sel[0].name() )
    
    
    def argUpdate(self, row, col):
        #print('Changed', row, col)
        
        if col == 3:
            item = self.ui.aligns.item(row, col)
            
            try:
                newJsonData = json.loads( item.text().replace("'", '"') )
            except Exception:
                print('Error parsing json, not updating')
                return
            
            with self.commands[row].card.rigData as rigData:
                for i, data in enumerate(rigData['tpose']):
                    if data['order'] == self.commands[row].order:
                        rigData['tpose'][i]['args'] = newJsonData
                        break
            
            print('Successful json edit')



    def setOptions(self, *args):
        card = self.cardNames.get( self.ui.cardChooser.currentText(), None )
        cmdName = self.ui.adjustmentChooser.currentText()
        
        for i in range(self.MAX_INPUTS):
            self.entry[i] = {}
        
        if cmdName == '':
            for i in range(self.MAX_INPUTS):
                label = getattr(self.ui, 'label%i' % i)
                label.setEnabled(False)
                label.setText('')
                entry = getattr(self.ui, 'input%i' % i)
                entry.setEnabled(False)
                entry.clear()

        else:
            cmd = adjusters.adjustCommands[cmdName]
            spec = inspect.getargspec(cmd)
            
            # First arge is auto filled in as the card, so get the rest buffered with None to clear the entry.
            args = spec.args[1:] + ([None] * self.MAX_INPUTS)
            
            for inputIndex, arg in enumerate(args[:self.MAX_INPUTS]):
                
                label = getattr(self.ui, 'label%i' % inputIndex)
                entry = getattr(self.ui, 'input%i' % inputIndex)
                entry.clear()
                
                if arg is None:
                    label.setText('')
                    label.setEnabled(False)
                    entry.setEnabled(False)
                    entry.clear()
                    
                else:
                    if 'Joint' in arg:
                        if arg in adjusters._anyJoint[cmdName]:
                            self.entry[inputIndex] = OrderedDict( sorted( [(j.name(), j) for card in find.blueprintCards() for j in card.joints if not j.isHelper] ))
                        else:
                            self.entry[inputIndex] = OrderedDict( sorted( [(j.name(), j) for j in card.joints] ))
                            
                        entry.addItems( list(self.entry[inputIndex].keys()) )

                    else:
                        entry.addItems( [str(i) for i in range(1, 40)] )
                        self.entry[inputIndex] = { str(i): i for i in range(1, 40) }
                    
                    label.setText(arg)
                    label.setEnabled(True)
                    entry.setEnabled(True)

    
    def listAdjustments(self):
        self.ui.aligns.blockSignals(True)
        
        self.ui.aligns.clearContents()
        
        cards = find.blueprintCards()
        
        self.commands = []
        unused = []
        for card in cards:
            with card.rigData as data:
                if 'tpose' in data:
                    for alignCmd in data['tpose']:
                        self.commands.append( Adjust(alignCmd['order'], card, alignCmd) )
                    
                else:
                    unused.append( card )
        
        self.ui.aligns.setRowCount( len(self.commands) )
        
        self.commands.sort()
        
        for row, (order, card, data) in enumerate(self.commands):
            self.ui.aligns.setItem(row, 0, self.TWItem(card.name()))
            #self.ui.aligns.setItem(row, 1, self.TWItem(str(order), readOnly=False))
            button = Qt.QtWidgets.QPushButton(str(order))
            button.clicked.connect( Callback(self.moveItem, order) )
            self.ui.aligns.setCellWidget(row, 1, button)
            self.ui.aligns.setItem(row, 2, self.TWItem(data['call']))
            self.ui.aligns.setItem(row, 3, self.TWItem(str(data['args']), readOnly=False))
        
        self.ui.aligns.blockSignals(False)
        
        
        self.cardNames = OrderedDict( sorted([(c.name(), c) for c in find.blueprintCards()]) )
        self.ui.cardChooser.addItems( self.cardNames.keys() )
        '''
    rigData['tpose'] = [{
        'order': 40,
        'call': 'fingerAlign',
        'args': ['self.joints[0]']
    }]  '''
    
    def moveItem(self, order):
        
        newOrder, ok = Qt.QtWidgets.QInputDialog().getInt(self,
            'Current Index: {}'.format(order),
            'New Index',
            order)
        
        if ok and newOrder != order:
            adjusters.reorder(order, newOrder)
            self.listAdjustments()


    @staticmethod
    def TWItem(label, readOnly=True):
        item = Qt.QtWidgets.QTableWidgetItem(label)
        if readOnly:
            item.setFlags( item.flags() ^ Qt.QtCore.Qt.ItemFlag.ItemIsEditable )
            
        return item


    @staticmethod
    def runOnSelected(cmd):
        cards = util.selectedCards()
        print('Run on selected', cmd, cards)
        cmd( cards )


    @staticmethod
    def updateReposersWithProgress(*args):
        
        if not args:
            count = len(find.blueprintCards()) * 2
        else:
            count = len(args[0]) * 2
        select(cl=True)
        with pdil.ui.progressWin(title='Building reposers', max=count) as prog:
            updateReposers(*args, progress=prog)

    @staticmethod
    def runAdjustementsWithProgress(*args):
        
        if not args:
            count = len(find.blueprintCards()) * 2
        else:
            count = len(args[0]) * 2
        
        with pdil.ui.progressWin(title='Running adjustments', max=count) as prog:
            adjusters.runAdjusters(*args, progress=prog)


    def addAdjustment(self):
        card = self.cardNames[ self.ui.cardChooser.currentText() ]
        command = self.ui.adjustmentChooser.currentText()
        
        if not command:
            return
        
        args = ['self']
        
        for i in range(self.MAX_INPUTS):
            if getattr( self.ui, 'label%i' % i ).text():
                valName = str(getattr(self.ui, 'input%i' % i).currentText())
                objOrValue = self.entry[i][ valName ]
                
                args.append( objOrValue )
        
        adjusters.addAdjuster(card, command, args)
        
        self.listAdjustments()
        

    def removeAdjustment(self):
        rowIndices = [modelIndex.row() for modelIndex in self.ui.aligns.selectedIndexes()]
        
        toDelete = []
        
        for i in rowIndices:
            toDelete.append( self.commands[i].card.name() + ' ' + self.commands[i].data['call'] )
        
        if confirmDialog(m='Delete these %i adjusters?\n' % len(rowIndices ) + '\n'.join(toDelete), b=['Delete', 'Cancel'] ) == 'Delete':
            for rowIndex in rowIndices:
                with self.commands[rowIndex].card.rigData as rigData:
                    #print('Rig Data', rigData)
                    for i, data in enumerate(rigData['tpose']):
                        #print('COMP', data['order'], self.commands[rowIndex].order)
                        if data['order'] == self.commands[rowIndex].order:
                            #print('Found and deleting')
                            del rigData['tpose'][i]
                            break
        
            self.listAdjustments()


    def closeEvent(self, event):
        self.settings['geometry'] = pdil.ui.getGeometry(self)

        header = self.ui.aligns.horizontalHeader()
        self.settings['headers'] = [header.sectionSize(0), header.sectionSize(1), header.sectionSize(2)]
        
        event.accept()
    
    
    def sceneChange(self):
        self.listAdjustments()

        
"""
class Gui(object):
    def __init__(self):
        with pdil.ui.singleWindow('reposer'):
            #with columnLayout(adj=True):
            with formLayout() as f:
                button(l='Update All Reposers', c=Callback(self.updateReposersWithProgress, ))
                button(l='Update Selected Reposers', c=Callback(self.runOnSelected, self.updateReposersWithProgress))
                separator()
                button(l='Run All Adjusters', c=Callback(runAdjusters))
                button(l='Run Selected Adjusters', c=Callback(self.runOnSelected, runAdjusters))
                separator()
                button(l='Go To BindPose', c=Callback(goToBindPose))
                textScrollList()
    
    @staticmethod
    def runOnSelected(cmd):
        cards = util.selectedCards()
        print('Run on selected', cmd, cards)
        cmd( cards )

    @staticmethod
    def updateReposersWithProgress(*args):
        with pdil.ui.progressWin(title='Building reposers', max=len(args[0]) * 2) as prog:
            updateReposers(*args, progress=prog)
"""


def reposeDeal():
    from pymel.core import window, rowColumnLayout, text, button, checkBox, showWindow, Callback, scrollLayout
    
    roots = getReposeRoots()

    allRepose = roots[:]
    for root in roots:
        allRepose += listRelatives(root, ad=True, type='transform')

    checks = {
        'origRot': [],
        'origTrans': [],
        'prevRot': [],
        'prevTrans': [],
        'prevRotWorld': [],
        'prevTransWorld': [],
    }

    attrs = {
        'origR': [ 'origRot', 'r' ],
        'origT': [ 'origTrans', 't' ],
        'prevR': [ 'prevRot', 'r' ],
        'prevT': [ 'prevTrans', 't' ],
        'prevRW': [ 'prevRotWorld', 'prevRW' ],
        'prevTW': [ 'prevTransWorld', 'prevTW' ],
    }

    def setValues(objs, checks, column):
        
        targets = [obj for obj, check in zip(objs, checks[column]) if check.getValue()]

        setValueHelper( column, targets )
        
        '''
        print(targets)
        for target in targets:
            print(target)
            if column == 'origR':
                target.r.set( target.origR.get() )
            elif column == 'origT':
                target.t.set( target.origTrans.get() )
                
            elif column == 'prevR':
                target.r.set( target.prevRot.get() )
            elif column == 'prevT':
                target.t.set( target.prevTrans.get() )
                
            else:
                raise Exception('IMPELEMNT WORLKD')
        '''

    window()
    with scrollLayout():
        with rowColumnLayout(nc=7):
            text(l='')

            button(l='origR', c=Callback( setValues, allRepose, checks, 'origRot') )
            button(l='origT', c=Callback( setValues, allRepose, checks, 'origTrans') )

            button(l='prevR', c=Callback( setValues, allRepose, checks, 'prevRot') )
            button(l='prevT', c=Callback( setValues, allRepose, checks, 'prevTrans') )

            button(l='prevRW', c=Callback( setValues, allRepose, checks, 'prevRW') )
            button(l='prevTW', c=Callback( setValues, allRepose, checks, 'prevTW') )
            
            for obj in allRepose:
                text(l=obj.name())
                checks['origRot'].append( checkBox(l='') )
                checks['origTrans'].append( checkBox(l='') )
                
                checks['prevRot'].append( checkBox(l='', v=not obj.origRot.get() == obj.prevRot.get() ) )
                checks['prevTrans'].append( checkBox(l='', v=not obj.origTrans.get() == obj.prevTrans.get() ) )

                checks['prevRotWorld'].append( checkBox(l='') )
                checks['prevTransWorld'].append( checkBox(l='') )

    showWindow()

            
def reposeAdjuster():
    
    roots = getReposeRoots()

    #cards = listRelatives(r[1], ad=True, type='nurbsSurface')
    joints = {}

    entries = []
    for root in roots:
        
        entries.append( [0, [root] ] )
        
        def children(n, depth=1, card=None):
            for x in listRelatives(n, type='transform'):
                if x.type() != 'joint':
                    
                    if entries[-1][0] == depth:
                        entries[-1][1].append( x )
                    else:
                        entries.append( [depth, [x]] )
                    #print( '   ' * depth + str(x) )
                    
                    children(x, depth + 1, x)
                else:
                    joints.setdefault(card, []).append( x )
                    
                    children(x, depth, card)

        children(root, card=root)
    
    from pymel.core import window, columnLayout, button, rowLayout, text, showWindow, deleteUI, PyNode, frameLayout, scrollLayout
    from functools import partial
    
    if window('REPOSER_POSE', ex=True):
        deleteUI('REPOSER_POSE')
    
    def setRot(obj, r, *args):
        obj = PyNode(obj)
        for axis, val in zip('xyz', r):
            try:
                obj.attr( 'r' + axis ).set(val)
            except Exception:
                pass
    
    def setTrans(obj, t, *args):
        obj = PyNode(obj)
        for axis, val in zip('xyz', t):
            try:
                obj.attr( 't' + axis ).set(val)
            except Exception:
                pass
    
    window('REPOSER_POSE')
    scrollLayout()
    with columnLayout():
        
        for depth, nodes in entries:
            for n in nodes:
                #print( '   ' * depth + str(n) )
                with rowLayout(nc=3 if depth else 4):
                    text(l=(' ' * 8) * depth)
                    text(l=str(n))
                    
                    button(l='Rot', c=partial(setRot, n.name(), n.r.get()) )
                    if depth == 0:
                        button(l='Trans', c=partial(setTrans, n.name(), n.t.get()) )
                
                if n in joints:
                    with frameLayout(cll=True, cl=True, l=''):
                        with columnLayout():
                            for j in joints[n]:
                                button(l=str(j), c=partial(setRot, j.name(), j.r.get()) )
                        
    
    showWindow()
    
    for c, js in joints.items():
        print( c, '---------------' )
        print( '\n'.join( [str(j) for j in js] ) )
    
    #for x in entries:
    #    print( x )
    
    
def setValueHelper(attr, objs=None, *args):
    
    from pymel.core import selected
    
    if not objs:
        objs = selected()
    
    for obj in objs:
        if not obj.hasAttr(attr):
            continue
    
        mode = 't' if 'Trans' in attr else 'r'
        
        values = obj.attr(attr).get()
        
        for axis, val in zip('xyz', values):
            try:
                obj.attr( mode + axis ).set(val)
            except Exception:
                import traceback
                print(traceback.format_exc())

                
def reposeAdjusterSimple():
    
    from pymel.core import deleteUI, window, columnLayout, button, showWindow
    from functools import partial
    
    if window('REPOSER_POSE_SIMPLE', ex=True):
        deleteUI('REPOSER_POSE_SIMPLE')
    
    window('REPOSER_POSE_SIMPLE')
    with columnLayout():
        for attr in [
            'origRot',
            'origTrans',
            'prevRot',
            'prevTrans',
            'prevRotWorld',
            'prevTransWorld',
        ]:
            button(l=attr, c=partial(setValueHelper, attr) )
    
    showWindow()
