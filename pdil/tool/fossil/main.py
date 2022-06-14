from __future__ import print_function, absolute_import

from collections import OrderedDict
import json
from functools import partial
import operator
import os
import traceback

import logging

from ...vendor import Qt


from pymel.core import Callback, cmds, hide, scriptJob, select, selected, setParent, PyNode, \
    showHidden, warning, xform, \
    button, columnLayout, deleteUI, textFieldGrp
    
import pdil
from ... import nodeApi

from . import cardparams
from ._lib2 import controllerShape
from ._lib2 import card as fossil_card # Hack to not deal with the fact that "card" is a var used all over, thusly shadowing this import
from ._core import config
from ._core import find
from ._core import skinning
from ._lib import proxyskel
from ._lib import tpose
from . import updater
from . import util

from .ui import controllerEdit
from .ui import _visGroup

from .ui import spacesTab
from .ui import startingTab

from . import cardlister


log = logging.getLogger(__name__)


RigToolUI = pdil.ui.getQtUIClass( os.path.dirname(__file__) + '/ui/rigToolUI.ui', 'pdil.tool.fossil.ui.rigToolUI')


def matchOrient():
    if len(selected()) < 2:
        return
        
    src = selected()[0]
    rot = xform(src, q=True, ws=True, ro=True)
    
    for dest in selected()[1:]:
        xform( dest, ws=True, ro=rot )


def customUp():
    if not selected():
        return
        
    arrow = selected()[0]

    if not arrow.name().count('arrow'):
        arrow = None
        
    if not util.selectedJoints():
        warning('No BPJoints were selected')
        return

    for jnt in util.selectedJoints():
        fossil_card.customUp(jnt, arrow)


def complexJson(s):
    if not s:
        return '{\n}'
    output = ['{']

    for side, info in s.items():
        output.append( '"%s": {' % (side) )
        for component, data in info.items():
            output.append( '  "%s": [' % (component) )
            for d in data:
                output.append( '    %s,' % json.dumps(d) )
            output[-1] = output[-1][:-1]  # strip off trailing comma
            output.append('  ],')
        output[-1] = output[-1][:-1]  # strip off trailing comma
        output.append('},')
    output[-1] = output[-1][:-1]  # strip off trailing comma
    output.append('}')
                
    return '\n'.join(output)


def spacesJson(s):
    if not s:
        return '{\n}'
    output = ['{']

    for side, info in s.items():
        output.append( '"%s": {' % (side) )
        
        for component, data in info.items():
            output.append( '  "%s": [' % (component) )
            for d in data['spaces']:
                output.append( '    %s,' % json.dumps(d) )
            output[-1] = output[-1][:-1]  # strip off trailing comma
            output.append('  ],')
            
        output[-1] = output[-1][:-1]  # strip off trailing comma
        output.append('},')
    output[-1] = output[-1][:-1]  # strip off trailing comma
    output.append('}')
                
    return '\n'.join(output)


def simpleJson(s):
    if not s:
        return '{\n}'
    output = ['{']

    for side, info in s.items():
        output.append( '"%s": {' % (side) )
        for component, data in info.items():
            output.append( '  "%s": %s,' % (component, json.dumps(data)) )

        output[-1] = output[-1][:-1]  # strip off trailing comma
        output.append('},')
    output[-1] = output[-1][:-1]  # strip off trailing comma
    output.append('}')
                
    return '\n'.join(output)


class RigTool(Qt.QtWidgets.QMainWindow):
    
    _inst = None
    
    FOSSIL_START_TAB = 'Fossil_RigTool_StartTab'
    FOSSIL_SPACE_TAB = 'Fossil_RigTool_SpacedTab'
        
    @staticmethod
    @pdil.alt.name( 'Rig Tool' )
    def run():
        return RigTool()
    
    
    def connectorDisplayToggle(self):
        
        if self.ui.actionConnectors.isChecked():
            showHidden( fossil_card.getConnectors() )
        else:
            hide( fossil_card.getConnectors() )
    
    
    def handleDisplayToggle(self):
        
        val = self.ui.actionHandles.isChecked()
        
        #cards = ls( '*.skeletonInfo', o=1 )
        for card in find.blueprintCards():
            for joint in card.joints:
                joint.displayHandle.set(val)
    
    
    def orientsToggle(self):
        if self.ui.actionCard_Orients_2.isChecked():
            showHidden( fossil_card.getArrows() )
        else:
            hide( fossil_card.getArrows() )
    
    
    def __init__(self, *args, **kwargs):
        
        self.settings = pdil.ui.Settings( 'Fossil GUI Settings',
            {
                'spineCount': 5,
                'fingerCount': 4,
                'thumb': True,
                'spineOrient': 'Vertical',
                'legType': 'Human',
                'currentTabIndex': 1,  # 1-base AFAIK THE ONLY ONE ACTUALLY NEEDED
                'panels': [75, 75, 25, 100, 75, 25],
                'rebuildMode': 'Use Current Shapes',

                'closedControlFrame': False,
                'closeDebugFrame': True,
                
                'showIndividualRestore': False,
                'showRigStateDebug': False,
                
                'runUpdaters': True,
            })
        
        objectName = 'Rig_Tool'
        # Remove any existing windows first
        pdil.ui.deleteByName(objectName)
        
        super(RigTool, self).__init__(pdil.ui.mayaMainWindow())
        
        # Not sure how else to get window's scale factor for high dpi displays
        self.scaleFactor = self.font().pixelSize() / 11.0

        self.ui = RigToolUI()
        self.ui.setupUi(self)

        self.setObjectName(objectName)
        self.setWindowTitle('Fossil')
        self.setAttribute(Qt.QtCore.Qt.WA_DeleteOnClose)  # So card deletetion script jobs clear out
        self.setWindowFlags(Qt.QtCore.Qt.Tool)  # Possibly prevents maya from covering up fossil on non-windows
        
        # Menu callbacks
        self.ui.actionReconnect_Real_Joints.triggered.connect( Callback(fossil_card.reconnectRealBones) )
        self.ui.actionMatch_Selected_Orients.triggered.connect( Callback(matchOrient) )
        
        self.ui.actionCard_Orients_2.triggered.connect( Callback(self.orientsToggle) )
        
        # &&& I think this isn't useful but I'm going to wait a while to be sure.
        #self.ui.actionConnectors.triggered.connect( Callback(self.connectorDisplayToggle) )
        self.ui.menuVisibility.removeAction(self.ui.actionConnectors)
        
        self.ui.actionHandles.triggered.connect( Callback(self.handleDisplayToggle) )
        
        self.ui.actionNaming_Rules.triggered.connect( Callback(nameRulesWindow) )
        
        self.ui.actionShow_Individual_Restores.setChecked( self.settings['showIndividualRestore'] )
        self.ui.actionShow_Card_Rig_State.setChecked( self.settings['showRigStateDebug'] )

        self.ui.actionShow_Individual_Restores.triggered.connect( Callback(self.restoreToggle) )
        self.ui.actionShow_Card_Rig_State.triggered.connect( Callback(self.rigStateToggle) )
                
        # Callback setup
        
        self.ui.makeCardBtn.clicked.connect(self.makeCard)
        self.ui.selectAllBtn.clicked.connect(self.selectAll)
        self.ui.buildBonesBtn.clicked.connect(Callback(fossil_card.buildBones))
        self.ui.deleteBonesBtn.clicked.connect( Callback(fossil_card.deleteBones) )
        self.ui.buildRigBtn.clicked.connect( fossil_card.buildRig )
        self.ui.deleteRigBtn.clicked.connect( partial(util.runOnEach, operator.methodcaller('removeRig'), 'Deleting Rig') )
        self.ui.saveModsBtn.clicked.connect( partial(util.runOnEach, operator.methodcaller('saveState'), 'Saving State') )
        self.ui.restoreModsBtn.clicked.connect( partial(util.runOnEach, operator.methodcaller('restoreState'), 'Restoring State') )
        
        
        self.ui.duplicateCardBtn.clicked.connect(self.duplicateCard)
        self.ui.mergeCardBtn.clicked.connect(self.mergeCard)
        self.ui.splitCardBtn.clicked.connect(self.splitCard)

        self.ui.addCardIkButton.clicked.connect( Callback(self.addCardIk) )
        self.ui.remCardIkButton.clicked.connect( Callback(self.removeCardIk) )

        
        self.ui.insertJointBtn.clicked.connect(self.insertJoint)
        self.ui.addTipBtn.clicked.connect(partial(self.insertJoint, True))
        self.ui.deleteJointBtn.clicked.connect(self.deleteJoint)
        
        self.ui.rebuildProxyBtn.clicked.connect( proxyskel.rebuildConnectorProxy )
        
        self.ui.customUpBtn.clicked.connect(Callback(customUp))
        
        self.ui.updateRigState.clicked.connect(self.updateField)


        self.ui.space_save.clicked.connect( partial(self.targeted_save, 'spaces') )
        self.ui.space_load.clicked.connect( partial(self.targeted_load, 'spaces') )
        self.ui.vis_save.clicked.connect( partial(self.targeted_save, 'visGroup') )
        self.ui.vis_load.clicked.connect( partial(self.targeted_load, 'visGroup') )
        self.ui.shape_save.clicked.connect( partial(self.targeted_save, 'shape') )
        self.ui.shape_local_load.clicked.connect( partial(self.targeted_load, 'shape_local') )
        self.ui.shape_world_load.clicked.connect( partial(self.targeted_load, 'shape_world') )
        self.ui.constraints_save.clicked.connect( partial(self.targeted_save, 'constraints') )
        self.ui.constraints_load.clicked.connect( partial(self.targeted_load, 'constraints') )
        self.ui.connections_save.clicked.connect( partial(self.targeted_save, 'connections') )
        self.ui.connections_load.clicked.connect( partial(self.targeted_load, 'connections') )
        self.ui.driven_save.clicked.connect( partial(self.targeted_save, 'setDriven') )
        self.ui.driven_load.clicked.connect( partial(self.targeted_load, 'setDriven') )
        self.ui.custom_save.clicked.connect( partial(self.targeted_save, 'customAttrs') )
        self.ui.custom_load.clicked.connect( partial(self.targeted_load, 'customAttrs') )
        self.ui.locked_save.clicked.connect( partial(self.targeted_save, 'lockedAttrs') )
        self.ui.locked_load.clicked.connect( partial(self.targeted_load, 'lockedAttrs') )


        def restore(key, restoreFunc):
            print('Restoring', key)
            [ c._restoreData(restoreFunc, c.rigState[key]) for c in util.selectedCards() ]

        # Individual restore commands
        for niceName, (harvestFunc, restoreFunc) in nodeApi.Card.toSave.items():
            button = getattr(self.ui, niceName + 'Restore')
            button.clicked.connect( partial(restore, niceName, restoreFunc))

        '''
        self.restoreShapes(objectSpace=shapesInObjectSpace)
        '''

        # Start Group Tab
        self.startTabLayout = Qt.QtWidgets.QVBoxLayout(self.ui.tab)
        self.startTabLayout.setObjectName( self.FOSSIL_START_TAB )
        setParent( self.FOSSIL_START_TAB )
        self.startTab = startingTab.StartLayout( self )
        
        
        # Vis Group Tab
        self.visGroupProxy = _visGroup.VisGroupLayout(self.ui)
        
        # Space Tab
        self.spaceTab = spacesTab.SpaceTab(self.ui)
        
        
        # Card Lister setup
        self.updateId = scriptJob( e=('SelectionChanged', pdil.alt.Callback(self.selectionChanged)) )
        self.ui.cardLister.setup(self.scaleFactor)
        
        self.ui.cardLister.itemSelectionChanged.connect(self.cardListerSelection)
        
        self.ui.cardLister.cardListerRefresh(force=True)
        self.ui.cardLister.updateHighlight()
        for card in find.blueprintCards():
            cardlister.cardDeleteTriggerSetup(card)
        
        
        self.ui.jointLister.setup(self.scaleFactor)
        
        self.ui.cardLister.namesChanged.connect( self.ui.jointLister.jointListerRefresh )
        
        self.ui.restoreContainer.setVisible( self.settings['showIndividualRestore'] )
        self.ui.rigStateContainer.setVisible( self.settings['showRigStateDebug'] )

        pdil.pubsub.subscribe('fossil rig type changed', self.forceCardParams)
        pdil.pubsub.subscribe('fossil card added', self.ui.cardLister.newCardAdded)
        pdil.pubsub.subscribe('fossil card deleted', self.ui.cardLister.cardListerRefresh)
        pdil.pubsub.subscribe('fossil card reparented', partial(self.ui.cardLister.cardListerRefresh, force=True))

        # Controller Edit
        self.shapeEditor = controllerEdit.ShapeEditor(self)
        
        #-
        self.show()
        
        pdil.pubsub.subscribe(pdil.pubsub.Event.MAYA_DAG_OBJECT_CREATED, self.ui.cardLister.newObjMade)
    
        self.uiActive = True
        self._uiActiveStack = []
        
        self.ui.tabWidget.setCurrentIndex(self.settings['currentTabIndex'])

        if 'geometry' in self.settings:
            pdil.ui.setGeometry( self, self.settings['geometry'] )
        
        pdil.pubsub.publish('fossil rig type changed')
        selectedCard = util.selectedCardsSoft(single=True)
        self.ui.jointLister.jointListerRefresh(selectedCard)
        self.ui.jointLister.refreshHighlight()
        
        if self.settings['runUpdaters']:
            self.runUpdatersId = scriptJob( e=('SceneOpened', updater.checkAll) )
            updater.checkAll()
        
    
    def forceCardParams(self):
        # Called rig type changes to update the params
        selectedCard = util.selectedCardsSoft(single=True)
        cardparams.update(self, selectedCard, force=True)
    
    
    @staticmethod
    def targeted_save(key):
        print( 'Saving', key )
        if key.startswith('shape'):
            for card in util.selectedCards():
                card.saveShapes()
        else:
            harvestFunc, restoreFunc = nodeApi.Card.toSave[key]
            for card in util.selectedCards():
                card._saveData(harvestFunc)
        
        
    @staticmethod
    def targeted_load(key):
        print( 'Loading', key )
        if key.startswith('shape'):
            if 'world' in key:
                for card in util.selectedCards():
                    card.restoreShapes(objectSpace=False)
            else:
                for card in util.selectedCards():
                    card.restoreShapes()
        else:
            harvestFunc, restoreFunc = nodeApi.Card.toSave[key]
            for card in util.selectedCards():
                card._restoreData(restoreFunc, card.rigState[key])

    """
    @staticmethod
    def deleteBones(cards=None):
        global _meshStorage
        if not cards:
            cards = util.selectedCards()
        
        # &&& NEED TO COLLECT CHILDREN JOINTS THAT WILL GET DELETED
        '''
        joints = []
        for card in cards:
            joints += card.getOutputJoints()
        
        joints = cmds.ls(joints) # Quickly determine if any joints actually exists
        
        if joints:
            meshes = pdil.weights.findBoundMeshes(joints)
            storeMeshes(meshes)
        '''
        #meshes = getBoundMeshes(cards)
        #if meshes:
        #    storeMeshes(meshes)
        skinning.cacheWeights(cards, _meshStorage)
        
        with pdil.ui.progressWin(title='Deleting Bones', max=len(cards)) as prog:
            for card in cards:
                card.removeBones()
                prog.update()
    """
    
    
    def noUiUpdate(self):
        self._uiActiveStack.append( self.uiActive )
        self.uiActive = False
        yield
        self.uiActive = self._uiActiveStack.pop()
                
        self.updateId = scriptJob( e=('SelectionChanged', pdil.alt.Callback(self.selectionChanged)) )
    
    
    def restoreToggle(self):
        self.settings['showIndividualRestore'] = not self.settings['showIndividualRestore']
        self.ui.restoreContainer.setVisible( self.settings['showIndividualRestore'] )
    
    
    def rigStateToggle(self):
        self.settings['showRigStateDebug'] = not self.settings['showRigStateDebug']
        self.ui.rigStateContainer.setVisible( self.settings['showRigStateDebug'] )


    def selectAll(self):
        select( find.blueprintCards() )
    
    
    def closeEvent(self, event):
        #print('------  - - -  i am closing')
        pdil.pubsub.unsubscribe(pdil.pubsub.Event.MAYA_DAG_OBJECT_CREATED, self.ui.cardLister.newObjMade)
        
        
        pdil.pubsub.unsubscribe('fossil rig type changed', self.forceCardParams)
        pdil.pubsub.unsubscribe('fossil card added', self.ui.cardLister.newCardAdded)
        pdil.pubsub.unsubscribe('fossil card deleted', self.ui.cardLister.cardListerRefresh)
        pdil.pubsub.unsubscribe('fossil card reparented', partial(self.ui.cardLister.cardListerRefresh, force=True))
        
        try:
            if self.updateId is not None:
                jid = self.updateId
                self.updateId = None
                scriptJob(kill=jid)
            
            self.spaceTab.close()
            
            self.settings['geometry'] = pdil.ui.getGeometry(self)
            self.settings['currentTabIndex'] = self.ui.tabWidget.currentIndex()
            
            if self.runUpdatersId is not None:
                jid = self.runUpdatersId
                self.updateId = None
                scriptJob(kill=jid)
            
        except Exception:
            pass
        
        # Might be overkill but I'm trying to prevent new gui parenting to the old widgets
        #self.spaceTabLayout.setObjectName( 'delete_me2' )
#        self.shapeEditor.curveColorLayout.setObjectName( 'delete_me3' )
#        self.shapeEditor.surfaceColorLayout.setObjectName( 'delete_me4' )
        self.startTabLayout.setObjectName('delete_me5')
        
        event.accept()
    
    formatter = {
        'visGroup': simpleJson,
        'connections': complexJson,
        'setDriven': complexJson,
        'customAttrs': complexJson,
        'spaces': spacesJson,
        'constraints': complexJson,
        'lockedAttrs': simpleJson,
    }

    def selectionChanged(self):
        self.ui.cardLister.updateHighlight()
        
        selectedCard = util.selectedCardsSoft(single=True)
        
        cardparams.update(self, selectedCard)
        self.ui.jointLister.jointListerRefresh(selectedCard)
        self.ui.jointLister.refreshHighlight()
        self.shapeEditor.refresh()
        if self.ui.rigStateContainer.isVisible():
            if selectedCard:
                for key, data in selectedCard.rigState.items():
                    getattr(self.ui, key + 'Field').setText( self.formatter[key](data) )
                
                allInfo = ''
                for _node, side, type in selectedCard._outputs():
                    shapeInfo = pdil.factory.getStringAttr( selectedCard, 'outputShape' + side + type)
                    if shapeInfo:
                        allInfo += pdil.text.asciiDecompress(shapeInfo).decode('utf-8') + '\n\n'
                
                self.ui.shapesField.setText( allInfo )
            else:
                for key in nodeApi.Card.toSave:
                    getattr(self.ui, key + 'Field').setText( '' )
                
                self.ui.shapesField.setText('')
            


    def updateField(self):
        # Get the tab title
        label = self.ui.rigStateTab.tabText( self.ui.rigStateTab.currentIndex() )
        label = (label[0].lower() + label[1:]).replace(' ', '')

        print(label)

        text = self.ui.rigStateTab.currentWidget().children()[-1].toPlainText()

        try:
            data = json.loads(text, object_pairs_hook=OrderedDict)
        except Exception:
            pdil.ui.notify(m='Invalid json, see script editor for details')
            print( traceback.format_exc() )
            return

        selectedCard = util.selectedCardsSoft(single=True)
        rigState = selectedCard.rigState
        rigState[label] = data
        selectedCard.rigState = rigState

    def cardListerSelection(self):
        if self.ui.cardLister.uiActive:
            cards = [item.card for item in self.ui.cardLister.selectedItems()]
            select(cards)

    def makeCard(self):
        '''
        Make a new card and child it if a BPJoint is selected.
        
        .. todo::
            I think, when adding a chain, if the parent doesn't have an orient target
                already, give it its existing child.  Of course this won't quite work
                for the pelvis but whatever.
        '''
        try:
            # radius = 1
            targetParent = util.selectedJoints()[0] if util.selectedJoints() else None
            if not targetParent and selected():
                # Quick hack for if the annotation is selected instead of the
                # handle.  This is really just a pain and I should link the
                # Annotation to the real joint.
                try:
                    intendedTarget = selected()[0].t.listConnections()[0].output3D.listConnections()[0]
                    if intendedTarget.__class__.__name__ == 'BPJoint':
                        targetParent = intendedTarget
                except Exception:
                    pass
            
            count = self.ui.jointCount.value()
            name = str(self.ui.cardJointNames.text())
            
            # Auto repeat the name if only one was given
            if len(name.split()) == 1 and count > 1 and name[-1] != '*':
                name += '*'
            
            try:
                head, repeat, tail = util.parse(name)
            except Exception:
                raise Exception('Invalid characters given')
            
            if count <= 0:
                raise Exception( 'You must specify at least one joint!' )

            namedCount = len(head) + len(tail) + (1 if repeat else 0)
            
            if count < namedCount:
                raise Exception( 'Not enough joints exist to take all of the given names' )
            if count > namedCount and not repeat:
                raise Exception( 'No name was specified as repeating and too many joints were given.' )
            
            #card = skeletonTool.pdil.Card( jointCount=count, name=name, rigInfo=None, size=(4, 6) )
            newCard = fossil_card.makeCard(jointCount=count, jointNames=name, rigInfo=None, size=(4, 6), parent=targetParent )
            
            if targetParent:
                fossil_card.moveTo( newCard, targetParent )
                # Clear out 7/2022 if no issues have come up
                #skeletonTool.proxyskel.pointer( targetParent, newCard.start() )
#                newCard.start().setBPParent(targetParent)
#                radius = targetParent.radius.get()
#            else:
#                proxyskel.makeProxy(newCard.start())
#                newCard.start().proxy.setParent( proxyskel.getProxyGroup() )
            
            
#            for j in newCard.joints:
#                j.radius.set(radius)
#                j.proxy.radius.set(radius)
            
            select( newCard )
        except Exception as ex:
            print( traceback.format_exc() )
            m = str(ex) + '''\n
                All names must be valid as Maya names.
                Optionally one may end with a '*' signifying it repeats.
            
                Ex:  Chest Neck* Head HeadTip
                
                Would only be valid if the card had at least 4 joints, any above
                that would increase the Neck: Chest Neck01 Neck02 .. Neck<N> Head HeadTip
                
                Repeating can be at the start or end or no repeats at all, as long as the numbers make sense.
                '''
        
            pdil.ui.notify(t='Error', m=m)
            raise

    #-- Joints and Cards ------------------------------------------------------
    def insertJoint(self, tip=False):
        sel = util.selectedJoints()
        if not sel:
            warning('You must select the blueprint joint you want to insert after.')
            return
        
        children = sel[0].proxyChildren[:]
        
        card = sel[0].card
        newJoint = card.insertChild(sel[0])
        
        if tip:
            
            rigData = card.rigData
            
            names = rigData.get('nameInfo', {})
            
            if names.get('tail'):
                names['tail'].append( names['tail'][-1] + 'Tip' )
            else:
                names['tail'] = ['Tip']
            
            card.rigData = rigData
            
            newJoint.isHelper = True
            
            # Repoint the children back to the selected joint since the tip is for orienting
            for child in children:
                proxyskel.pointer(sel[0], child)
            
            self.ui.cardLister.updateNames(card)
            
        select( newJoint )
        pdil.pubsub.publish('fossil joint added')
    
    def deleteJoint(self):
        sel = util.selectedJoints()
        if not sel:
            return
            
        sel[0].card.deleteJoint(sel[0])
        select(cl=True)
    
    def duplicateCard(self):

        '''
        Prompts, if possible, for a new name.
        
        ..  todo:: See if it's possible to use difflib for more elaborate name
            matching.
        
        '''
        unableToRename = []
        dups = []
        sources = {}
        for card in util.selectedCards():
            d = fossil_card.duplicateCard(card)
            sources[card] = d
            dups.append(d)
            
            names = d.rigData.get('nameInfo', {})
            
            if not names:
                names['repeat'] = 'DUP'
            else:
                if 'head' in names['head']:
                    for i, name in enumerate(names['head']):
                        names['head'][i] = name + '_DUP'
                        
                if 'repeat' in names['repeat']:
                    names['repeat'] = name + '_DUP'
                    
                if 'tail' in names['tail']:
                    for i, name in enumerate(names['tail']):
                        names['tail'][i] = name + '_DUP'
            
            rigData = d.rigData
            rigData['nameInfo'] = names
            d.rigData = rigData
                
        for src, newCard in zip(sources, dups):
            if src.parentCard:
                if src.parentCard in sources:
                    index = src.parentCard.joints.index( src.parentCardJoint )

                    newParent = sources[src.parentCard].joints[index]

                    proxyskel.pointer( newParent, newCard.start())

        if unableToRename:
            pdil.ui.notify( t='Unable to rename',
                m="{0} were unable to find a common element to rename, you must do this manually".format( '\n'.join(unableToRename)) )
            select(unableToRename)
        else:
            select(dups)
        
    def mergeCard(self):
        sel = util.selectedCards()
        if len(sel) != 2:
            pdil.ui.notify(m='You can only merge two cards at a time, please select 2 cards')
            return
    
        if sel[0].parentCard == sel[1]:
            sel[1].merge(sel[0])
        elif sel[1].parentCard == sel[0]:
            sel[0].merge(sel[1])
        else:
            pdil.ui.notify(m='You can only merge cards that are related to eachother')
            return
        
    def splitCard(self):
        j = util.selectedJoints()
        if j:
            fossil_card.splitCard(j[0])
    
    def addCardIk(self):
        fossil_card.cardIk( selected()[0] )
        
    
    def removeCardIk(self):
        fossil_card.removeCardIk( selected()[0] )


"""
def accessoryFixup(newJoints, card):
    ''' Place the topmost joints in a separate group so they aren't exported.
    '''
    
    if not newJoints: # CtrlGroup doesn't make joints so just leave
        return
    
    newJoints = set(newJoints)
    
    if card.rigData.get('accessory'):
        
        # Freeform and mirrored joints have several the need parent fixup
        for jnt in newJoints:
            parent = jnt.getParent()
            if parent not in newJoints:
                jnt.setParent( node.accessoryGroup() )
                
                jnt.addAttr('fossilAccessoryInfo', dt='string')
                jnt.fossilAccessoryInfo.set( json.dumps( {'parent': parent.longName()} ) )
"""

def nameRulesWindow():
    
    with pdil.ui.singleWindow('nameRulesWindow', t='Choose what is displayed to indicate the side of the joints and controllers.') as win:
        with columnLayout(adj=True):
            jl = textFieldGrp('jointLeft', l='Joint Left Side', tx=config._settings['joint_left'] )
            jr = textFieldGrp('jointRight', l='Joint Right Side', tx=config._settings['joint_right'] )

            cl = textFieldGrp('controlLeft', l='Control Left Side', tx=config._settings['control_left'] )
            cr = textFieldGrp('controlRight', l='Control Right Side', tx=config._settings['control_right'] )
        
            root = textFieldGrp('root', l='Root Joint Name', tx=config._settings['root_name'] )
            prefixField = textFieldGrp('jointPrefix', l='Joint Prefix', tx=config._settings['joint_prefix'] )
            
            def setNames():
                jlText = jl.getText().strip()
                jrText = jr.getText().strip()
                
                clText = cl.getText().strip()
                crText = cr.getText().strip()
                
                rootName = root.getText().strip()
                
                if jlText == jrText or clText == crText:
                    pdil.ui.notify(m='The left and right sides must be different\n(but the control and joint text for the same side can be the same)')
                    return
                
                if not clText or not crText or not jlText or not jrText or not rootName:
                    pdil.ui.notify(m='You cannot leave any side empty and root must have a name')
                    return
                
                config._settings['joint_left'] = jlText
                config._settings['joint_right'] = jrText
                
                config._settings['control_left'] = clText
                config._settings['control_right'] = crText
                
                config.JOINT_SIDE_CODE_MAP['left'] = jlText
                config.JOINT_SIDE_CODE_MAP['right'] = jrText
                
                config.CONTROL_SIDE_CODE_MAP['left'] = clText
                config.CONTROL_SIDE_CODE_MAP['right'] = crText
                
                config._settings['root_name'] = rootName
                config._settings['joint_prefix'] = prefixField.getText().strip()
                
                
                deleteUI(win)
            
            button(l='Apply', c=Callback(setNames))
    
    return win, setNames


def getBoundMeshes(cards=None):
    ''' Returns the meshes bound to the joints made by the rig.
    
    Defaults to using all cards but specific cards can be specified.
    '''
    if not cards:
        cards = find.blueprintCards()
    
    allJoints = []
    for card in cards:
        for joint in card.joints:
            if joint.real:
                allJoints.append(joint.real)
            if joint.realMirror:
                allJoints.append(joint.realMirror)

    meshes = pdil.weights.findBoundMeshes(allJoints)
    return meshes


def fullRebuild(weights=None):
    ''' Detached any bound meshes and rebuild everything, including the tpose if it exists.
    '''
    
    cards = find.blueprintCards()
    
    meshStorage = {}
    
    with pdil.ui.progressWin(title='Full Rebuild', max=len(cards) * 4 + 9 ) as pr:
        pr.update(status='Searching for bound meshes')
        
        if not weights:
            meshes = getBoundMeshes(cards)
            if meshes:
                pr.update(status='Storing weights')
                #storeMeshes(meshes)
                skinning.cacheWeights(cards, meshStorage)
        
        pr.update(status='Saving states')
        for card in cards:
            pr.update()
            card.saveState()
        
        pr.update(status='Removing Rig')
        for card in cards:
            pr.update()
            card.removeRig()
        
        pr.update(status='Removing Bones')
        for card in cards:
            pr.update()
            card.removeBones()
        
        #
        reposers = tpose.getReposeRoots()
        if reposers:
            #delete(reposers)
            pr.update(status='New reposer')
            tpose.updateReposers(cards)
            pr.update(status='Run adjusters')
            tpose.runAdjusters()
        
        pr.update(status='Build Bones')
        fossil_card.buildBones(cards)
        
        pr.update(status='Build Rig')
        fossil_card.buildRig(cards)
        
        pr.update(status='Restore State')
        for card in cards:
            pr.update()
            card.restoreState()
        
        if reposers:
            tpose.goToBindPose()
        
        if not weights:
            skinning.cacheWeights(cards, meshStorage)
        else:
            for obj, data in weights.items():
                obj = PyNode(obj)
                pdil.weights.apply(obj, data['weight'])
                

def fitControlsToMesh(cards, meshes):
    ''' Scale all the controls to be slightly larger than the nearest mesh portion.
    '''
    
    cmds_xform = cmds.xform # Make the fastest version possible
    
    allPositions = []
    for mesh in meshes:
        # String queries are super fast, about 7x faster than PyMel
        vertCmd = str(mesh) + '.vtx[{}]'
        allPositions += [cmds_xform( vertCmd.format(i), q=1, t=1, ws=1 ) for i in range(len(mesh.vtx))]
    
    for card in cards:
        for ctrl, side, _type in card.getMainControls():
            radius = controllerShape.determineRadius(allPositions, pdil.dagObj.getPos(ctrl))
            currentRadius = controllerShape.getControllerRadius(ctrl)
            controllerShape.scaleAllCVs(ctrl, radius / currentRadius )
            
            for key, subCtrl in ctrl.subControl.items():
                radius = controllerShape.determineRadius(allPositions, pdil.dagObj.getPos(subCtrl))
                currentRadius = controllerShape.getControllerRadius(subCtrl)
                controllerShape.scaleAllCVs(subCtrl, radius / currentRadius)
                