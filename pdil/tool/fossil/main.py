from __future__ import print_function, absolute_import

from functools import partial
import operator
import os
import traceback

from ...vendor import Qt


from pymel.core import Callback, confirmDialog, getAttr, hide, objExists, scriptJob, select, selected, setParent, setAttr, \
    showHidden, warning, xform, \
    button, columnLayout, deleteUI, showWindow, textFieldGrp, window
    

from ... import core

from . import card as fossil_card  # Hack to not deal with the fact that "card" is a var used all over, thusly shadowing this import
from . import cardlister
from . import cardparams
from . import cardRigging
from . import controllerShape
from . import moveCard
from . import proxy
from . import settings
from . import util

from .ui import artistToolsTab
from .ui import controllerEdit
from .ui import _visGroup

from .ui import spacesTab
from .ui import startingTab


RigToolUI = core.ui.getQtUIClass( os.path.dirname(__file__) + '/ui/rigToolUI.ui', 'pdil.tool.fossil.ui.rigToolUI')


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
        
        self.settings = core.ui.Settings( 'Skeleton Tool Settings',
            {
                #'spineCount': 5,
                #'fingerCount': 4,
                #'thumb': True,
                #'spineOrient': 'Vertical',
                #'legType': 'Human',
                'currentTabIndex': 1,  # 1-base
                #'panels': [75, 75, 25, 100, 75, 25],
                #'rebuildMode': 'Use Current Shapes',

                #'closedControlFrame': False,
                #'closeDebugFrame': True,
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
        
        self.ui.actionNaming_Rules.triggered.connect( Callback(self.nameRulesWindow) )
        
        
        '''
        button(l="Custom Up", c=Callback(customUp), w=200)
    
        '''
        
        
        # Callback setup
        
        self.ui.makeCardBtn.clicked.connect(self.makeCard)
        self.ui.selectAllBtn.clicked.connect(self.selectAll)
        self.ui.buildBonesBtn.clicked.connect(self.buildBones)
        self.ui.deleteBonesBtn.clicked.connect( partial(util.runOnEach, operator.methodcaller('removeBones'), 'Bones deleted') )
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
        
        self.ui.rebuildProxyBtn.clicked.connect( proxy.rebuildConnectorProxy )
        
        self.ui.customUpBtn.clicked.connect(Callback(customUp))
        
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
        
        # Controller Edit
        self.shapeEditor = controllerEdit.ShapeEditor(self)
        self.show()
        
        core.pubsub.subscribe(core.pubsub.Event.MAYA_DAG_OBJECT_CREATED, self.ui.cardLister.newObjMade)
    
        self.uiActive = True
        self._uiActiveStack = []
        
        self.ui.tabWidget.setCurrentIndex(self.settings['currentTabIndex'])
        
        if 'geometry' in self.settings:
            core.ui.setGeometry( self, self.settings['geometry'] )
    
    def noUiUpdate(self):
        self._uiActiveStack.append( self.uiActive )
        self.uiActive = False
        yield
        self.uiActive = self._uiActiveStack.pop()
                
        self.updateId = scriptJob( e=('SelectionChanged', core.alt.Callback(self.selectionChanged)) )

    def nameRulesWindow(self):
        
        win = window(t='Choose what is displayed to indicate the side of the joints and controllers.')
        with columnLayout(adj=True):
            jl = textFieldGrp(l='Joint Left Side', tx=self.settings['joint_left'] )
            jr = textFieldGrp(l='Joint Right Side', tx=self.settings['joint_right'] )

            cl = textFieldGrp(l='Control Left Side', tx=self.settings['control_left'] )
            cr = textFieldGrp(l='Control Right Side', tx=self.settings['control_right'] )
        
            def setSides():
                jlText = jl.getText().strip()
                jrText = jr.getText().strip()
                
                clText = cl.getText().strip()
                crText = cr.getText().strip()
                
                if jlText == jrText or clText == crText:
                    confirmDialog(m='The left and right sides must be different\n(but the control and joint text for the same side can be the same)')
                    return
                
                if not clText or not crText or not jlText or not jrText:
                    confirmDialog(m='You cannot leave any side empty.')
                    return
                
                self.settings['joint_left'] = jlText
                self.settings['joint_right'] = jrText
                
                self.settings['control_left'] = clText
                self.settings['control_right'] = crText
                
                settings.JOINT_SIDE_CODE_MAP['left'] = jlText
                settings.JOINT_SIDE_CODE_MAP['right'] = jrText
                
                settings.CONTROL_SIDE_CODE_MAP['left'] = clText
                settings.CONTROL_SIDE_CODE_MAP['right'] = crText
                
                
                deleteUI(win)
            
            button(l='Apply', c=Callback(setSides))
        
        showWindow()


    def selectAll(self):
        select( core.findNode.allCards() )
    
    @staticmethod
    def buildBones():
        sel = set(util.selectedCards())
        if not sel:
            confirmDialog( m='No cards selected' )
            return
        
        # Only build the selected cards, but always do it in the right order.
        for card in cardlister.cardJointBuildOrder():
            if card in sel:
                card.buildJoints()
        select(sel)
    
    @staticmethod
    def buildRig():
        '''
        Makes the rig, saving shapes and removing the old rig if needed.
        '''
        cards = util.selectedCards()
        
        mode = 'Use Rig Info Shapes'
        
        if not cards:
            confirmDialog( m='No cards to selected to operate on.' )
            return
        
        
        for card in cards:
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
        select(cards)

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
    
    def selectionChanged(self):
        self.ui.cardLister.updateHighlight()
        
        selectedCard = util.selectedCardsSoft(single=True)
        
        cardparams.update(self, selectedCard)
        self.ui.jointLister.jointListerRefresh(selectedCard)
        self.ui.jointLister.refreshHighlight()
        self.shapeEditor.refresh()
            
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
                
                #skeletonTool.proxy.pointer( targetParent, newCard.start() )
                newCard.start().setBPParent(targetParent)
                radius = targetParent.radius.get()
            else:
                proxy.makeProxy(newCard.start())
                newCard.start().proxy.setParent( proxy.getProxyGroup() )
            
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
        
            confirmDialog(t='Error', m=m)
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
                proxy.pointer(sel[0], child)
            
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

                    proxy.pointer( newParent, newCard.start())

        if unableToRename:
            confirmDialog( t='Unable to rename',
                m="{0} were unable to find a common element to rename, you must do this manually".format( '\n'.join(unableToRename)) )
            select(unableToRename)
        else:
            select(dups)
        
    def mergeCard(self):
        sel = util.selectedCards()
        if len(sel) != 2:
            confirmDialog(m='You can only merge two cards at a time, please select 2 cards')
            return
    
        if sel[0].parentCard == sel[1]:
            sel[1].merge(sel[0])
        elif sel[1].parentCard == sel[0]:
            sel[0].merge(sel[1])
        else:
            confirmDialog(m='You can only merge cards that are related to eachother')
            return
        
    def splitCard(self):
        j = util.selectedJoints()
        if j:
            fossil_card.splitCard(j[0])
    
    def addCardIk(self):
        fossil_card.cardIk( selected()[0] )
        
    
    def removeCardIk(self):
        fossil_card.removeCardIk( selected()[0] )
