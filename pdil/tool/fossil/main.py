from __future__ import print_function, absolute_import

from collections import OrderedDict
from contextlib import contextmanager
import json
from functools import partial
import operator
import os
import traceback

import logging

from ...vendor import Qt


from pymel.core import Callback, cmds, dt, getAttr, hide, objExists, scriptJob, select, selected, setParent, setAttr, PyNode, \
    showHidden, warning, xform, \
    button, columnLayout, deleteUI, textFieldGrp, \
    delete, orientConstraint, pointConstraint
    
import pdil
from ... import core
from ... import nodeApi

from . import card as fossil_card  # Hack to not deal with the fact that "card" is a var used all over, thusly shadowing this import
from . import cardlister
from . import cardparams
from . import cardRigging
from . import controllerShape
from . import moveCard
from .core import proxyskel
from .core import config
from . import tpose
from . import util
from . import node

from .ui import artistToolsTab
from .ui import controllerEdit
from .ui import _visGroup

from .ui import spacesTab
from .ui import startingTab


log = logging.getLogger(__name__)


RigToolUI = core.ui.getQtUIClass( os.path.dirname(__file__) + '/ui/rigToolUI.ui', 'pdil.tool.fossil.ui.rigToolUI')

if '_meshStorage' not in globals():
    _meshStorage = {}


def storeMeshes(meshes):
    ''' Used by build/remove joints.  Temp storage for mesh weights as the rig is rebuilt.
    &&& I think this should be replaced by skinning.py
    '''
    global _meshStorage
    _meshStorage.clear()
    
    for mesh in meshes:
        _meshStorage[mesh] = {
            'weight': core.weights.get(mesh)
            # &&& Add an entry for BPJ ids
        }


def restoreMeshes():
    ''' Used by build/remove joints.  Try to load any temp stored meshes.
    &&& I think this should be replaced by skinning.py
    '''
    global _meshStorage
    
    applied = []
    for mesh, data in _meshStorage.items():
        weights = data['weight']
        for j in weights['jointNames']:
            if not objExists(j):
                break
        else:
            # All the joints exist, so skin it
            core.weights.apply(mesh, weights)
            applied.append(mesh)
    
    for mesh in applied:
        del _meshStorage[mesh]


def matchOrient():
    if len(selected()) < 2:
        return
        
    src = selected()[0]
    rot = xform(src, q=True, ws=True, ro=True)
    
    for dest in selected()[1:]:
        xform( dest, ws=True, ro=rot )


def customUp(self):
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


@contextmanager
def nothing():
    yield


class RigTool(Qt.QtWidgets.QMainWindow):
    
    _inst = None
    
    FOSSIL_START_TAB = 'Fossil_RigTool_StartTab'
    FOSSIL_ARTIST_TOOLS = 'Fossil_RigTool_ToolsTab'
    FOSSIL_SPACE_TAB = 'Fossil_RigTool_SpacedTab'
        
    @staticmethod
    @core.alt.name( 'Rig Tool' )
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
        for card in core.findNode.allCards():
            for joint in card.joints:
                joint.displayHandle.set(val)
    
    
    def orientsToggle(self):
        if self.ui.actionCard_Orients_2.isChecked():
            showHidden( fossil_card.getArrows() )
        else:
            hide( fossil_card.getArrows() )
    
    
    def __init__(self, *args, **kwargs):
        
        self.settings = core.ui.Settings( 'Fossil GUI Settings',
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
            })
        
        objectName = 'Rig_Tool'
        # Remove any existing windows first
        core.ui.deleteByName(objectName)
        
        super(RigTool, self).__init__(core.ui.mayaMainWindow())
        
        # Not sure how else to get window's scale factor for high dpi displays
        self.scaleFactor = self.font().pixelSize() / 11.0

        self.ui = RigToolUI()
        self.ui.setupUi(self)

        self.setObjectName(objectName)
        self.setWindowTitle('Fossil')
        
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
        self.ui.buildBonesBtn.clicked.connect(self.buildBones)
        self.ui.deleteBonesBtn.clicked.connect( self.deleteBones )
        self.ui.buildRigBtn.clicked.connect( self.buildRig )
        self.ui.deleteRigBtn.clicked.connect( partial(util.runOnEach, operator.methodcaller('removeRig'), 'Rig deleted') )
        self.ui.saveModsBtn.clicked.connect( partial(util.runOnEach, operator.methodcaller('saveState'), 'State saved') )
        self.ui.restoreModsBtn.clicked.connect( partial(util.runOnEach, operator.methodcaller('restoreState'), 'State restored') )
        
        
        self.ui.duplicateCardBtn.clicked.connect(self.duplicateCard)
        self.ui.mergeCardBtn.clicked.connect(self.mergeCard)
        self.ui.splitCardBtn.clicked.connect(self.splitCard)

        self.ui.addCardIkButton.clicked.connect( self.addCardIk )
        self.ui.remCardIkButton.clicked.connect( self.removeCardIk )

        
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
        #self.spaceTabLayout = Qt.QtWidgets.QVBoxLayout(self.ui.space_tab)
        
        #self.spaceTabLayout.setObjectName( self.FOSSIL_SPACE_TAB )
        #setParent( self.FOSSIL_SPACE_TAB)
        #self.spaceTab = spacesTab.SpaceLayout()
        self.spaceTab = spacesTab.SpaceTab(self.ui)
        
        # Shelf tab
        
        
        self.artistShelfLayout = Qt.QtWidgets.QVBoxLayout(self.ui.artist_tools)
        self.artistShelfLayout.setObjectName( self.FOSSIL_ARTIST_TOOLS )
        setParent( self.FOSSIL_ARTIST_TOOLS )
        
        artistToolsTab.toolShelf()

        
        # Card Lister setup
        self.updateId = scriptJob( e=('SelectionChanged', core.alt.Callback(self.selectionChanged)) )
        self.ui.cardLister.setup(self.scaleFactor)
        
        self.ui.cardLister.itemSelectionChanged.connect(self.cardListerSelection)
        
        self.ui.cardLister.cardListerRefresh(force=True)
        self.ui.cardLister.updateHighlight()
        
        self.ui.jointLister.setup(self.scaleFactor)
        
        self.ui.cardLister.namesChanged.connect( self.ui.jointLister.jointListerRefresh )
        
        self.ui.restoreContainer.setVisible( self.settings['showIndividualRestore'] )
        self.ui.rigStateContainer.setVisible( self.settings['showRigStateDebug'] )

        # Controller Edit
        self.shapeEditor = controllerEdit.ShapeEditor(self)
        self.show()
        
        core.pubsub.subscribe(core.pubsub.Event.MAYA_DAG_OBJECT_CREATED, self.ui.cardLister.newObjMade)
    
        self.uiActive = True
        self._uiActiveStack = []
        
        self.ui.tabWidget.setCurrentIndex(self.settings['currentTabIndex'])
        
        if 'geometry' in self.settings:
            core.ui.setGeometry( self, self.settings['geometry'] )
    
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
    
    @staticmethod
    def deleteBones(cards=None):
        if not cards:
            cards = util.selectedCards()
        
        # &&& NEED TO COLLECT CHILDREN JOINTS THAT WILL GET DELETED
        '''
        joints = []
        for card in cards:
            joints += card.getOutputJoints()
        
        joints = cmds.ls(joints) # Quickly determine if any joints actually exists
        
        if joints:
            meshes = core.weights.findBoundMeshes(joints)
            storeMeshes(meshes)
        '''
        meshes = getBoundMeshes(cards)
        if meshes:
            storeMeshes(meshes)
        
        with core.ui.progressWin(title='Deleting Bones', max=len(cards)) as prog:
            for card in cards:
                card.removeBones()
                prog.update()
    
    def noUiUpdate(self):
        self._uiActiveStack.append( self.uiActive )
        self.uiActive = False
        yield
        self.uiActive = self._uiActiveStack.pop()
                
        self.updateId = scriptJob( e=('SelectionChanged', core.alt.Callback(self.selectionChanged)) )

    def restoreToggle(self):
        self.settings['showIndividualRestore'] = not self.settings['showIndividualRestore']
        self.ui.restoreContainer.setVisible( self.settings['showIndividualRestore'] )

    def rigStateToggle(self):
        self.settings['showRigStateDebug'] = not self.settings['showRigStateDebug']
        self.ui.rigStateContainer.setVisible( self.settings['showRigStateDebug'] )


    def selectAll(self):
        select( core.findNode.allCards() )
    
    @staticmethod
    def validateBoneNames(cards):
        '''
        Returns a list of any name issues building the given cards.
        '''
        issues = []
        allJoints = { c: c.getOutputJoints() for c in core.findNode.allCards()}

        untestedCards = list(allJoints.keys())

        for current in cards:
            
            untestedCards.remove(current)

            currentJoints = set( allJoints[current] )
            if len(currentJoints) != len( allJoints[current] ):
                issues.append(current.name() + ' does not have unique internal names')
            
            if 'NOT_ENOUGH_NAMES' in currentJoints:
                issues.append( '{} does not have enough names'.format(current) )

            for otherCard in untestedCards:
                overlap = currentJoints.intersection( allJoints[otherCard] )
                if overlap:
                    issues.append( '{} and {} overlap {}'.format( current, otherCard, overlap ))

        return issues


    @staticmethod
    def getRequiredHierarchy(cards):
        hierachy = cardlister.cardHierarchy()
        parentLookup = {child: parent for parent, children in hierachy for child in children}
        
        required = set()
        
        for card in cards:
            c = card
            while c:
                if c in required:
                    break
                required.add(c)
                c = parentLookup[c]

        return [c for c, children in hierachy if c in required]


    @classmethod
    def buildBones(cls, cards=None, removeTempBind=True):
        # Might need to wrap as single undo()
        if not cards:
            cards = set(util.selectedCards())
            if not cards:
                pdil.ui.notify( m='No cards selected' )
                return

        issues = cls.validateBoneNames(cards)
        if issues:
            pdil.ui.notify(m='\n'.join(issues), t='Fix these')
            return

        cardBuildOrder = cardlister.cardJointBuildOrder()

        if tpose.reposerExists():
            log.debug('Reposer Exists')
            realJoints = []  # This is a list of the joints that are ACTUALLY built in this process
            bindPoseJoints = []  # Matches realJoints, the cards that are bound
            tempBindJoints = []  # Super set of bindPoseJoints, including the hierarchy leading up to the bindBoseJoints

            estRealJointCount = len(cmds.ls( '*.realJoint' ))

            with core.ui.progressWin(title='Build Bones', max=estRealJointCount * 3 + len(cards)) as prog:
                with tpose.matchReposer(cardBuildOrder):
                    for card in cardBuildOrder:
                        if card in cards:
                            realJoints += card.buildJoints_core(nodeApi.fossilNodes.JointMode.tpose)
                        prog.update()
                
                    # The hierarchy has to be built to determine the right bindZero, so build everything if all cards
                    # are being made, otherwise target just a few
                    if len(cardBuildOrder) == len(cards):
                        bindCardsToBuild = cardBuildOrder
                    else:
                        bindCardsToBuild = cls.getRequiredHierarchy(cards)
            
                for card in bindCardsToBuild:
                    joints = card.buildJoints_core(nodeApi.fossilNodes.JointMode.bind)
                    tempBindJoints += joints
                    if card in cards:
                        bindPoseJoints += joints

                with tpose.controlsToBindPose():
                    # Setup all the constraints first so joint order doesn't matter
                    constraints = []
                    prevTrans = []
                    for bind, real in zip(bindPoseJoints, realJoints):
                        #with core.dagObj.Solo(bind):
                        #    bind.jo.set( real.jo.get() )
                        
                        prevTrans.append(real.t.get())
                        constraints.append(
                            [orientConstraint( bind, real ), pointConstraint( bind, real )]
                        )
                        
                        real.addAttr( 'bindZero', at='double3' )
                        real.addAttr( 'bindZeroX', at='double', p='bindZero' )
                        real.addAttr( 'bindZeroY', at='double', p='bindZero' )
                        real.addAttr( 'bindZeroZ', at='double', p='bindZero' )
                        prog.update()
                        #real.addAttr( 'bindZeroTr', at='double3' )
                        #real.addAttr( 'bindZeroTrX', at='double', p='bindZeroTr' )
                        #real.addAttr( 'bindZeroTrY', at='double', p='bindZeroTr' )
                        #real.addAttr( 'bindZeroTrZ', at='double', p='bindZeroTr' )
                        
                        #real.bindZero.set( real.r.get() )
                    
                    # Harvest all the values
                    for real in realJoints:
                        real.bindZero.set( real.r.get() )
                        #real.bindZeroTr.set( real.t.get() )
                        prog.update()
                        
                    # Return the real joints back to their proper location/orientation
                    for constraint, real, trans in zip(constraints, realJoints, prevTrans):
                        delete(constraint)
                        real.r.set(0, 0, 0)
                        real.t.set(trans)
                        prog.update()

            #root = core.findNode.getRoot()
            root = node.getTrueRoot()
            topJoints = root.listRelatives(type='joint')
            
            for jnt in topJoints:
                try:
                    index = realJoints.index(jnt)
                    real = jnt
                    bind = bindPoseJoints[index]

                    real.addAttr( 'bindZeroTr', at='double3' )
                    real.addAttr( 'bindZeroTrX', at='double', p='bindZeroTr' )
                    real.addAttr( 'bindZeroTrY', at='double', p='bindZeroTr' )
                    real.addAttr( 'bindZeroTrZ', at='double', p='bindZeroTr' )

                    real.bindZeroTr.set(
                        dt.Vector(xform(bind, q=True, ws=True, t=True)) - dt.Vector(xform(real, q=True, ws=True, t=True))
                    )

                except ValueError:
                    pass
            
            if removeTempBind:
                delete( tempBindJoints )

        else:
            log.debug('No reposer')
            # Only build the selected cards, but always do it in the right order.
            for card in cardBuildOrder:
                if card in cards:
                    card.buildJoints_core(nodeApi.fossilNodes.JointMode.default)
        
        
        # &&& Going to need to change to bindpose if it exists!  Ugg, what a pain!
        #restoreMeshes()

        select(cards)
    
    @staticmethod
    def buildRig(cards=None):
        '''
        Makes the rig, saving shapes and removing the old rig if needed.
        '''
        # &&& Need to move cardJointBuildOrder to util and make selectedCards() use it.
        if not cards:
            cards = set(util.selectedCards())
        
        mode = 'Use Rig Info Shapes'
        
        if not cards:
            pdil.ui.notify( m='No cards to selected to operate on.' )
            return
        
        # &&& BUG, need to ONLY check against joints under the root, since other non-joint objects might have the same name
        
        # allJoints = ...
                
        for card in cards:
            joints = card.getOutputJoints()
            if joints:
                if len(cmds.ls(joints)) != len(joints):
                    # &&& Ideall this prompts to build joints
                    pdil.ui.notify(m='{} does not have joints built.'.format(card) )
                    raise Exception('Joints not built')
        
        a = core.debug.Timer('Overall build')
        
        
        #rootMotion = core.findNode.rootMotion(main=main)
        #if not rootMotion:
        #    rootMotion = node.rootMotion(main=main)
        #    space.addMain(rootMotion)
        #    space.addTrueWorld(rootMotion)
        
        
        cardBuildOrder = cardlister.cardJointBuildOrder()
        
        with tpose.matchReposer(cardBuildOrder) if tpose.reposerExists() else nothing():
        
            for card in cardBuildOrder:
                if card not in cards:
                    continue

                if mode == 'Use Current Shapes':
                    card.saveShapes()
                
                # If this being rebuilt, also restore the if it's in ik or fk
                switchers = [controllerShape.getSwitcherPlug(x[0]) for x in card._outputs()]
                prevValues = [ (s, getAttr(s)) for s in switchers if s]

                card.removeRig()
                cardRigging.buildRig([card])

                if mode != 'Use Rig Info Shapes':
                    card.restoreShapes()
                    
                # Restore ik/fk-ness
                for switch, value in prevValues:
                    if objExists(switch):
                        setAttr(switch, value)
                    
        tpose.markBindPose(cards)
        
        select(cards)
        a.stop()

    def closeEvent(self, event):
        #print('------  - - -  i am closing')
        core.pubsub.unsubscribe(core.pubsub.Event.MAYA_DAG_OBJECT_CREATED, self.ui.cardLister.newObjMade)
        try:
            if self.updateId is not None:
                id = self.updateId
                self.updateId = None
                scriptJob(kill=id)
            
            self.spaceTab.close()
            
            self.settings['geometry'] = core.ui.getGeometry(self)
            self.settings['currentTabIndex'] = self.ui.tabWidget.currentIndex()
            
        except Exception:
            pass
        
        # Might be overkill but I'm trying to prevent new gui parenting to the old widgets
        self.artistShelfLayout.setObjectName( 'delete_me' )
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
        'spaces': complexJson,
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
                    shapeInfo = core.factory._getStringAttr( selectedCard, 'outputShape' + side + type)
                    if shapeInfo:
                        allInfo += core.text.asciiDecompress(shapeInfo) + '\n\n'
                
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
            radius = 1
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
            print( namedCount )
            if count < namedCount:
                raise Exception( 'Not enough joints exist to take all of the given names' )
            if count > namedCount and not repeat:
                raise Exception( 'No name was specified as repeating and too many joints were given.' )
            
            #card = skeletonTool.core.Card( jointCount=count, name=name, rigInfo=None, size=(4, 6) )
            newCard = fossil_card.makeCard(jointCount=count, jointNames=name, rigInfo=None, size=(4, 6) )
            
            if targetParent:
                moveCard.to( newCard, targetParent )
                
                #skeletonTool.proxyskel.pointer( targetParent, newCard.start() )
                newCard.start().setBPParent(targetParent)
                radius = targetParent.radius.get()
            else:
                proxyskel.makeProxy(newCard.start())
                newCard.start().proxy.setParent( proxyskel.getProxyGroup() )
            
            for j in newCard.joints:
                j.radius.set(radius)
                j.proxy.radius.set(radius)
            
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
        newJoint = card.insertJoint(sel[0])
        
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
    
    def deleteJoint(self):
        sel = util.selectedJoints()
        if not sel:
            return
            
        sel[0].card.deleteJoint(sel[0])
    
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


def nameRulesWindow():
    
    with core.ui.singleWindow('nameRulesWindow', t='Choose what is displayed to indicate the side of the joints and controllers.') as win:
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
        cards = core.findNode.allCards()
    
    allJoints = []
    for card in cards:
        for joint in card.joints:
            if joint.real:
                allJoints.append(joint.real)
            if joint.realMirror:
                allJoints.append(joint.realMirror)

    meshes = core.weights.findBoundMeshes(allJoints)
    return meshes


def fullRebuild(weights=None):
    ''' Detached any bound meshes and rebuild everything, including the tpose if it exists.
    '''
    
    cards = core.findNode.allCards()
    
    with core.ui.progressWin(title='Full Rebuild', max=len(cards) * 4 + 9 ) as pr:
        pr.update(status='Searching for bound meshes')
        
        if not weights:
            meshes = getBoundMeshes(cards)
            if meshes:
                pr.update(status='Storing weights')
                storeMeshes(meshes)
        
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
            delete(reposers)
            pr.update(status='New reposer')
            tpose.generateReposer(cards)
            pr.update(status='Run adjusters')
            tpose.runAdjusters()
        
        pr.update(status='Build Bones')
        RigTool.buildBones(cards)
        
        pr.update(status='Build Rig')
        RigTool.buildRig(cards)
        
        pr.update(status='Restore State')
        for card in cards:
            pr.update()
            card.restoreState()
        
        if reposers:
            tpose.goToBindPose()
        
        if not weights:
            restoreMeshes()
        else:
            for obj, data in weights.items():
                obj = PyNode(obj)
                core.weights.apply(obj, data['weight'])