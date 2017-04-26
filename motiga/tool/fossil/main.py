from __future__ import print_function, absolute_import

from functools import partial
import operator
import os
import re
import traceback

import Qt

#from pymel.core import *
from pymel.core import select, setParent, scriptJob, confirmDialog, getAttr, objExists, setAttr, Callback, selected, xform, hide, showHidden, warning, MeshVertex

from pymel.core import frameLayout, columnLayout, button, text, textScrollList, textFieldButtonGrp, rowColumnLayout, optionMenu, menuItem, intFieldGrp, checkBox, rowLayout, floatField, connectControl, layout, deleteUI


from ... import core
from ... import lib

from . import card as fossil_card  # Hack to not deal with the fact that "card" is a var used all over, thusly shadowing this import
from . import cardlister
from . import cardparams
from . import cardRigging
from . import controller
from . import moveCard
from . import proxy
from . import space
from . import util


RigToolUI = core.ui.getQtUIClass( os.path.dirname(__file__) + '/ui/rigToolUI.ui', 'motiga.tool.fossil.ui.rigToolUI')


class RigTool(Qt.QtWidgets.QMainWindow):
    
    _inst = None
    
    settings = core.ui.Settings( "Skeleton Tool Settings",
        {
            "spineCount": 4,
            "fingerCount": 4,
            "thumb": True,
            "spineOrient": "Vertical",
            "legType": "Human",
            "tabIndex": 1,  # 1-base
            'panels': [75, 75, 25, 100, 75, 25],
            'rebuildMode': 'Use Current Shapes',

            'closedControlFrame': False,
            'closeDebugFrame': True,
        })
    
    @staticmethod
    #@core.alt.name( 'Rig Tool' )
    def run():
        return RigTool()
        
    def __init__(self, *args, **kwargs):
        global settings
        
        objectName = 'Rig_Tool'
        # Remove any existing windows first
        core.ui.deleteByName(objectName)
        
        super(RigTool, self).__init__(core.ui.mayaMainWindow())
        
        self.ui = RigToolUI()
        self.ui.setupUi(self)

        self.setObjectName(objectName)
        self.setWindowTitle('Fossil')
        
        # Callback setup
        
        self.ui.makeCardBtn.clicked.connect(self.makeCard)
        self.ui.selectAllBtn.clicked.connect(self.selectAll)
        self.ui.buildBonesBtn.clicked.connect(self.buildBones)
        self.ui.deleteBonesBtn.clicked.connect( partial(util.runOnEach, operator.methodcaller('removeBones')) )
        self.ui.buildRigBtn.clicked.connect( self.buildRig )
        self.ui.deleteRigBtn.clicked.connect( partial(util.runOnEach, operator.methodcaller('removeRig')) )
        self.ui.saveModsBtn.clicked.connect( partial(util.runOnEach, operator.methodcaller('saveState')) )
        self.ui.restoreModsBtn.clicked.connect( partial(util.runOnEach, operator.methodcaller('restoreState')) )
        
        
        self.ui.duplicateCardBtn.clicked.connect(self.duplicateCard)
        self.ui.mergeCardBtn.clicked.connect(self.mergeCard)
        self.ui.splitCardBtn.clicked.connect(self.splitCard)
        
        self.ui.insertJointBtn.clicked.connect(self.insertJoint)
        self.ui.addTipBtn.clicked.connect(partial(self.insertJoint, True))
        self.ui.deleteJointBtn.clicked.connect(self.deleteJoint)
        
        # Start Group Tab
        qtLayout = Qt.QtWidgets.QVBoxLayout(self.ui.tab)
        qtLayout.setObjectName( "Mot_RigTool_StartTab" )
        setParent( "Mot_RigTool_StartTab" )
        self.startTab = StartLayout( self )
        
        # Util Group Tab
        qtLayout = Qt.QtWidgets.QVBoxLayout(self.ui.tab_2)
        qtLayout.setObjectName( "Mot_RigTool_UtilTab" )
        setParent( "Mot_RigTool_UtilTab" )
        self.utilTab = UtilLayout()
        
        # Vis Group Tab
        qtLayout = Qt.QtWidgets.QVBoxLayout(self.ui.tab_4)
        qtLayout.setObjectName( "Mot_RigTool_VisGroupTab" )
        setParent( "Mot_RigTool_VisGroupTab" )
        self.visGroupTab = VisGroupLayout()
        
        # Space Tab
        qtLayout = Qt.QtWidgets.QVBoxLayout(self.ui.tab_5)
        qtLayout.setObjectName( "Mot_RigTool_SpaceTab" )
        setParent( "Mot_RigTool_SpaceTab")
        self.spaceTab = SpaceLayout()
        
        # Card Lister setup
        self.updateId = scriptJob( e=('SelectionChanged', core.alt.Callback(self.selectionChanged)) )
        self.ui.cardLister.setup()
        
        self.ui.cardLister.itemSelectionChanged.connect(self.cardListerSelection)
        
        self.ui.cardLister.cardListerRefresh(force=True)
        self.ui.cardLister.updateHighlight()
        
        self.ui.jointLister.setup()
        
        self.show()
                
        
        
        core.pubsub.subscribe(core.pubsub.Event.MAYA_DAG_OBJECT_CREATED, self.ui.cardLister.newObjMade)
    
        self.uiActive = True
        self._uiActiveStack = []
    
    def noUiUpdate(self):
        self._uiActiveStack.append( self.uiActive )
        self.uiActive = False
        yield
        self.uiActive = self._uiActiveStack.pop()
                
        self.updateId = scriptJob( e=('SelectionChanged', core.alt.Callback(self.selectionChanged)) )

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
            switchers = [controller.getSwitcherPlug(x[0]) for x in card._outputs()]
            prevValues = [ (s, getAttr(s)) for s in switchers if s]

            card.removeRig()
            cardRigging.buildRig([card])

            if mode != 'Use Rig Info Shapes':
                card.restoreShapes()
                
            # Restore ik/fk-ness
            for switch, value in prevValues:
                if objExists(switch):
                    setAttr(switch, value)

    def closeEvent(self, event):
        core.pubsub.unsubscribe(core.pubsub.Event.MAYA_DAG_OBJECT_CREATED, self.ui.cardLister.newObjMade)
        try:
            if self.updateId is not None:
                id = self.updateId
                self.updateId = None
                scriptJob(kill=id)
        except Exception:
            pass
        event.accept()
    
    def selectionChanged(self):
        if self.ui.cardLister.uiActive:
            # This looks like it happens 100% of the time
            self.ui.cardLister.updateHighlight()
        else:
            pass
        
        selectedCard = util.selectedCardsSoft(single=True)
        
        cardparams.update(self, selectedCard)
        self.ui.jointLister.jointListerRefresh(selectedCard)
        self.ui.jointLister.refreshHighlight()
            
    def cardListerSelection(self):
        if self.ui.cardLister.uiActive:
            cards = [item.card for item in self.ui.cardLister.selectedItems()]
            select(cards)

    def visGroupUI_layout( self ):
        frameLayout(l='Visiblity Groups')
        
        columnLayout()
        text( l='Existing Groups' )
        textScrollList(nr=10)
        textFieldButtonGrp( l="Assign to Group", bl='Assign' )
        text(l='')
        button( l='Use Vis Shared Shape' )
        text(l='')
        button( l='Remove Vis Shared Shape' )
        text(l='')
        button( l='Prune Unused Vis Groups' )
        setParent("..")
        
        setParent("..")

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
        
    
            
class StartLayout( object ):
    def __init__( self, settingsObj ):
        rowColumnLayout(nc=2)

        # LegType UI
        text(l='Leg Type')
        self.legType = optionMenu( l='' )
        menuItem( l='Human' )
        menuItem( l='Dogleg' )
        settingsObj.settings.optionMenuSetup(self.legType, 'legType' )
    
        # Spine Orient UI
        text(l="Spine Orientation")
        self.spineOrient = optionMenu( l='')
        menuItem('Vertical')
        menuItem('Horizontal')
        settingsObj.settings.optionMenuSetup(self.spineOrient, 'spineOrient' )
    
        text(l='Number of Spine Joints')
        self.spineCount = intFieldGrp( nf=1, v1=settingsObj.settings.spineCount )
        text(l='Number of Fingers')
        self.fingerCount = intFieldGrp( nf=1, v1=settingsObj.settings.fingerCount )
        text(l="Thumb")
        self.thumb = checkBox(l='', v=settingsObj.settings.thumb)
    
        #setParent("..")
    
        text(l='')
        text(l='')
        text(l='')
        button(l="Start", w=300, c=core.alt.Callback(self.start))
        
    def update( self ):
        pass
    
    def start( self ):
        fossil_card.bipedSetup(
            spineCount=self.spineCount.getValue()[0],
            numFingers=self.fingerCount.getValue()[0],
            legType=self.legType.getValue(),
            thumb=self.thumb.getValue(),
            spineOrient='vertical' if self.spineOrient.getValue() == 'Vertical' else 'horizontal',  # &&& Need to use enums
        )

        
class UtilLayout( object ):
    def __init__( self ):
        columnLayout()
        button(l="Match Selected Orients", c=Callback(matchOrient), w=200)
        button(l="Custom Up", c=Callback(customUp), w=200)
    
        rowLayout(nc=2)
        button(l="Hide Orients", w=200, c=Callback(hideOrients))
        button(l="Show Orients", w=200, c=Callback(showOrients))
        setParent("..")
    
        rowLayout(nc=2)
        button(l="Hide Connectors", w=200, c=Callback(connectorDisplayToggle, False))
        button(l="Show Connectors", w=200, c=Callback(connectorDisplayToggle, True))
        setParent("..")
    
        rowLayout(nc=2)
        button(l="Hide Handles", w=200, c=Callback(handleDisplayToggle, False))
        button(l="Show Handles", w=200, c=Callback(handleDisplayToggle, True))
        setParent("..")
    
        button(l="Reconnect Real Bones", w=200, c=Callback(fossil_card.reconnectRealBones))
        button(l="Ensure Cards have Output Attrs", w=200)

        
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


def hideOrients():
    hide( fossil_card.getArrows() )


def showOrients():
    showHidden( fossil_card.getArrows() )


def connectorDisplayToggle(val):
    if val:
        showHidden( fossil_card.getConnectors() )
    else:
        hide( fossil_card.getConnectors() )


def handleDisplayToggle( val ):
    #cards = ls( '*.skeletonInfo', o=1 )
    for card in core.findNode.allCards():
        for joint in card.joints:
            joint.displayHandle.set(val)


def addCardOutputs():
    # Make sure the cards
    for card in core.findNode.allCards():
        fossil_card._addOutputControls( card )


class VisGroupLayout( object ):
    def __init__( self ):
        frameLayout(l='Visiblity Groups')

        columnLayout()
        text( l='Existing Groups' )
        self.current = textScrollList(nr=10, sc=core.alt.Callback(self.selectGroup))
        self.groupName = textFieldButtonGrp( l="Assign to Group", bl='Assign' )
        text(l='')
        button( l='Use Vis Shared Shape', c=Callback(self.use) )
        text(l='')
        button( l='Remove Vis Shared Shape', c=Callback(self.remove) )
        text(l='')
        button( l='Prune Unused Vis Groups', c=Callback(self.prune) )
        setParent("..")
    
        setParent("..")
        
        self.update()
        
    def selectGroup( self ):
        self.groupName.setText( self.current.getSelectItem()[0] )
        
    def assignGroup(self):
        name = self.groupName.getText()
        
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
            
        for obj in selected():
            lib.sharedShape.connect( obj, name )
            
    def use(self):
        sel = selected()
        for obj in selected():
            lib.sharedShape.use( obj )
        select( sel )
    
    def remove(self):
        sel = selected()
        for obj in selected():
            if lib.sharedShape.find(obj):
                lib.sharedShape.remove( obj )
        select( sel )
        
    def prune(self):
        lib.sharedShape.pruneUnused()
        
    def update( self ):
        self.current.removeAll()
        for name in lib.sharedShape.existingGroups():
            self.current.append( name )


class SpaceLayout( object ):
    def __init__( self ):
        columnLayout()
        self.targets = textScrollList(nr=20, sc=Callback(self.targetSelected))
    
        rowColumnLayout(nc=2)
        button( l='   ^   ', c=Callback(self.moveUp))
        button( l='   v   ', c=Callback(self.moveDown))
        setParent("..")
    
        self.name = textFieldButtonGrp(l='Custom Name', bl='Update Existing')
        button( l="Add", c=Callback(self.addSpace, space.Mode.ROTATE_TRANSLATE) )
        button( l="Add (Trans Only)", c=Callback(self.addSpace, space.Mode.TRANSLATE) )
        button( l="Add ( No Rot )", c=Callback(self.addSpace, "#NOROT") )
        button( l="Add (No Trans)", c=Callback(self.addSpace, space.ROTATE) )
        button( l="Split Targets (pos then rot)", c=Callback(self.addSpace, space.Mode.ALT_ROTATE) )
        button( l="Multi/Vert targets", c=Callback(self.addMultiSpace) )
        button( l="Multi Orient", c=Callback(self.addMultiOrientSpace) )
        text(l='')
        button( l="Add Parent", c=Callback(self.addSpace, '#PARENT') )
        button( l="Add World", c=Callback(self.addSpace, '#WORLD') )
        button( l="Add True World", c=Callback(self.addSpace, '#TRUEWORLD') )
        button( l="Add External World (For attachments)", c=Callback(self.addSpace, '#EXTERNALWORLD') )
        button( l="Remove", c=Callback(self.remove) )
        
        self.update()
        scriptJob( e=('SelectionChanged', Callback(self.update)), p=self.name )

    def targetSelected(self):
        sel = selected()
        targetIndex = self.targets.getSelectIndexedItem()
        if not targetIndex:
            return
        
        i = targetIndex[0] - 1
        
        targets = space.getTargetInfo(sel[0])
        targetConstraints = space._targetInfoConstraints[:]
        
        self.clearMultiTarget()
        if targets[i].type in [space.Mode.MULTI_PARENT, space.Mode.MULTI_ORIENT]:
            
            with rowColumnLayout( nc=2, p=self.mulitUI ):
                state = space.serializeSpaces( sel[0] )[i]
                
                weights = targetConstraints[i].getWeightAliasList()
                
                for t_i, (target, val) in enumerate(zip(state['targets'], state['extra'])):
                    text(l=target[0])  # target is a pair, name and cardpath
                    f = floatField(v=val, min=0, max=1)
                    connectControl( f, weights[t_i])
                    
    def moveUp(self):
        sel = textScrollList( self.targets, q=True, sii=True)
        if not sel:
            return
        
        index = sel[0] - 1
        
        if index == 0:
            return
            
        space.swap(selected()[0], index, index - 1)
        
        self.update()
        textScrollList(self.targets, e=True, sii=index)  # tsl is 1-based
        
    def moveDown(self):
        sel = textScrollList( self.targets, q=True, sii=True)
        if not sel:
            return
        
        index = sel[0] - 1
        
        if index == len(space.getNames(selected()[0])) - 1:
            return
            
        space.swap(selected()[0], index, index + 1)
        self.update()
        textScrollList(self.targets, e=True, sii=index + 2)  # tsl is 1-based

    def addSpace(self, mode):
        sel = selected()
        
        if mode == '#WORLD':
            space.addWorld( sel[0] )
        elif mode == '#TRUEWORLD':
            space.addTrueWorld( sel[0] )
        elif mode == '#EXTERNALWORLD':
            space.addExternalWorld( sel[0] )
        elif mode == '#PARENT':
            
            if sel[0].motigaCtrlType.get() in ['translate', 'rotate']:

                bindBone = core.constraints.getOrientConstrainee(sel[0])
                parent = bindBone.getParent()

                space.add( sel[0], parent, 'parent', space.Mode.ROTATE_TRANSLATE )
        
        elif mode == '#NOROT':
            space.add( sel[0], sel[1], self.name.getText(), space.Mode.ALT_ROTATE )

        elif mode == space.Mode.ALT_ROTATE:
            if len(sel) != 3:
                warning('You must have 2 targets selected')
                return
            
            space.add(sel[0], sel[1], self.name.getText(), mode, rotateTarget=sel[2])

        else:
            if len(sel) < 2:
                return
            space.add( sel[0], sel[1], self.name.getText(), mode )
        select(sel)
        
    def addMultiSpace(self):
        sel = selected()
        if isinstance(sel[1], MeshVertex):
            space.rivetSpace(sel[0], sel[1], self.name.getText())
        else:
            space.add(sel[0], sel[1:], self.name.getText(), space.Mode.MULTI_PARENT)
            
    def addMultiOrientSpace(self):
        sel = selected()
        space.add(sel[0], sel[1:], self.name.getText(), space.Mode.MULTI_ORIENT)
        
    def remove(self):
        spaces = self.targets.getSelectItem()
        
        for obj in selected():
            for _space in spaces:
                if _space in space.getNames(obj):
                    space.remove( obj, _space )
                    
        self.update()
        
    def update(self):
        self.targets.removeAll()
        
        sel = selected(type='transform')
        #self.clearMultiTarget()
        if sel:
            sel = sel[0]
            names = space.getNames(sel)
            if names:
                for name in names:
                    self.targets.append(name)
                    
    def clearMultiTarget(self):
        children = layout(self.mulitUI, q=True, ca=True)
        if children:
            deleteUI(children)