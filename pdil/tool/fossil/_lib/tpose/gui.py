from __future__ import absolute_import, division, print_function

from collections import OrderedDict
import inspect
import os

from pymel.core import Callback, listRelatives

import pdil
from pdil.vendor import Qt

from ... import util

from ..._core import ids
from ..._core import find

from . import adjusters
from .tpcore import updateReposers, getReposeRoots

ReposerGUI = pdil.ui.getQtUIClass( os.path.dirname(os.path.dirname(os.path.dirname(__file__))) + '/ui/reposer_gui.ui', 'pdil.tool.fossil.ui.reposer_gui')


class GUI(Qt.QtWidgets.QMainWindow):
    
    def __init__(self):
    
        self.settings = pdil.ui.Settings( 'Fossil Reposer GUI Settings',
            {
                'headers': [100, 40, 80],
                #geometry is added on close
            })
        
        objectName = 'Reposer'
        pdil.ui.deleteByName(objectName)
        
        super(GUI, self).__init__(pdil.ui.mayaMainWindow())
        
        self.ui = ReposerGUI()
        self.ui.setupUi(self)
        
        self.ui.updateAll.clicked.connect(Callback(self.updateReposersWithProgress))
        self.ui.updateSelected.clicked.connect(Callback(self.runOnSelected, self.updateReposersWithProgress))
        
        self.ui.runAll.clicked.connect( Callback(self.runAdjustementsWithProgress) )
        self.ui.runSelected.clicked.connect( Callback(self.runOnSelected, self.runAdjustementsWithProgress) )
        
        self.setObjectName(objectName)
        self.setWindowTitle('Reposer')
        
        self.listAdjustments()
        
        self.cardNames = OrderedDict( sorted([(c.name(), c) for c in find.blueprintCards()]) )
        self.entry = {0: {}, 1: {}, 2: {}}
        
        self.ui.cardChooser.addItems( self.cardNames.keys() )
        self.ui.cardChooser.currentTextChanged.connect(self.setOptions)
        self.ui.adjustmentChooser.addItems( [''] + [k for k in adjusters.adjustCommands.keys() if k[0] != '_']  )
        self.ui.adjustmentChooser.currentTextChanged.connect(self.setOptions)
        
        self.ui.addAdjustment.clicked.connect(self.addAdjustment)

        self.setOptions()
        
        # Load position settings
        header = self.ui.aligns.horizontalHeader()
        for col, width in enumerate(self.settings['headers']):
            header.resizeSection(col, width)
        
        self.show()
        
        if 'geometry' in self.settings:
            pdil.ui.setGeometry( self, self.settings['geometry'] )


    def setOptions(self, *args):
        card = self.cardNames[self.ui.cardChooser.currentText()]
        cmdName = self.ui.adjustmentChooser.currentText()
        
        for i in range(3):
            self.entry[i] = {}
        
        if cmdName == '':
            for i in range(3):
                label = getattr(self.ui, 'label%i' % i)
                label.setEnabled(False)
                label.setText('')
                entry = getattr(self.ui, 'input%i' % i)
                entry.setEnabled(False)
                entry.clear()

        else:
            cmd = adjusters.adjustCommands[cmdName]
            spec = inspect.getargspec(cmd)

            for i, arg in enumerate(spec.args):
                
                label = getattr(self.ui, 'label%i' % i)
                entry = getattr(self.ui, 'input%i' % i)
                entry.clear()
                
                if 'Card' in arg and i == 0:
                    label.setText('card')
                    entry.addItems(['self'])
                    label.setEnabled(False)
                    entry.setEnabled(False)
                    continue
                
                
                elif 'Joint' in arg:
                    if i == 0:
                        self.entry[i] = OrderedDict( sorted( [(j.name(), j) for j in card.joints] ))
                    else:
                        self.entry[i] = OrderedDict( sorted( [(j.name(), j) for card in find.blueprintCards() for j in card.joints if not j.isHelper] ))
                    entry.addItems( self.entry[i].keys() )
                
                else:
                    entry.addItems( [str(i) for i in range(1, 40)] )
                
                label.setText(arg)
                label.setEnabled(True)
                entry.setEnabled(True)
                
            for post_i in range(i + 1, 3):
                label = getattr(self.ui, 'label%i' % post_i)
                label.setText('')
                label.setEnabled(False)
                
                entry = getattr(self.ui, 'input%i' % post_i)
                entry.setEnabled(False)
                entry.clear()

    
    def listAdjustments(self):
        self.ui.aligns.clearContents()
        
        cards = find.blueprintCards()
        
        commands = []
        unused = []
        for card in cards:
            with card.rigData as data:
                if 'tpose' in data:
                    for alignCmd in data['tpose']:
                        commands.append( [alignCmd['order'], card, alignCmd] )
                    
                else:
                    unused.append( card )
        
        self.ui.aligns.setRowCount( len(commands) )
        
        commands.sort()
        
        for row, (order, card, data) in enumerate(commands):
            self.ui.aligns.setItem(row, 0, Qt.QtWidgets.QTableWidgetItem(card.name()))
            self.ui.aligns.setItem(row, 1, Qt.QtWidgets.QTableWidgetItem(str(order)))
            self.ui.aligns.setItem(row, 2, Qt.QtWidgets.QTableWidgetItem(data['call']))
            self.ui.aligns.setItem(row, 3, Qt.QtWidgets.QTableWidgetItem(str(data['args'])))
                
        '''
    rigData['tpose'] = [{
        'order': 40,
        'call': 'fingerAlign',
        'args': ['self.joints[0]']
    }]  '''



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
        
        args = []
        
        for i in range(3):
            if getattr( self.ui, 'label%i' % i ).text():
                val = getattr(self.ui, 'input%i' % i).text()
                if val == 'self':
                    args.append( val )
                else:
                    obj = self.entry[i][ val ]
                    
                    spec = ids.getIdSpec(obj)
                    
                    if spec['type'] == 'fossil_card':
                        args.append( 'id:' + spec['id'] )
                        
                    elif spec['type'] == 'fossil_bpj':
                        args.append( 'id:' + spec['card']['id'] + '.joint[%i]' % spec['index'] )
        
        
        # Find the next `order` number
        order = 0
        for _card in find.blueprintCards():

            for adjuster in _card.rigData.get('tpose', []):
                order = max(order, adjuster['order'])
        order += 1
        
        
        with card.rigData as data:
            adjusters = data['tpose'].getdefault([])
            
            adjusters.append(
                OrderedDict([
                    ('args', args),
                    ('call', command),
                    ('order', order),
                ])
            )
        

    def closeEvent(self, event):
        self.settings['geometry'] = pdil.ui.getGeometry(self)

        header = self.ui.aligns.horizontalHeader()
        self.settings['headers'] = [header.sectionSize(0), header.sectionSize(1), header.sectionSize(2)]
        
        event.accept()
        
        
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
