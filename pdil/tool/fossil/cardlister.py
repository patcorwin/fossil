from __future__ import print_function

import contextlib
from functools import partial

from pymel.core import select, scriptJob

from ...vendor.Qt import QtWidgets, QtCore
from ...vendor.Qt.QtCore import Qt, Signal

import pdil

from ._core import find
from ._lib import proxyskel

from . import cardRigging
from . import util


class ComboBox(QtWidgets.QComboBox):
    '''
    The sole purpose of this is to prevent scrolling when the mouse is on top, only allowing if it actually has focus.
    '''
    
    def __init__(self, *args, **kwargs):
        super(ComboBox, self).__init__(*args, **kwargs)
        self.setFocusPolicy(Qt.StrongFocus)
        self.isInteracting = False

    def showPopup(self, *args, **kwargs):
        self.isInteracting = True
        super(ComboBox, self).showPopup(*args, **kwargs)

    def hidePopup(self, *args, **kwargs):
        self.isInteracting = False
        super(ComboBox, self).hidePopup(*args, **kwargs)

    def wheelEvent(self, event):
        #if self.hasFocus():
        if self.isInteracting:
            return QtWidgets.QComboBox.wheelEvent(self, event)
        else:
            event.ignore()


class CardRow(QtWidgets.QTreeWidgetItem):
    
    options = ['-'] + cardRigging.availableControlTypeNames()
    mirrorOptions = ['-', 'Yes', 'Inherited', 'Skip', 'Yes:Twin']
    sideOptions = ['-', '<', '>']

    CARD_NAME   = 0
    
    VIS_COL     = 1
    NAME_HEAD   = 3
    NAME_REPEAT = 4
    NAME_TAIL   = 5
    
    MIRROR_COL  = 6
    SIDE_COL    = 7
    
    
    def __init__(self, card):
        
        self.card = card
        rigData = card.rigData
        name = pdil.simpleName(card)
        #head, repeat, tail = util.parse(card.nameInfo.get())
        names = rigData.get( 'nameInfo', {'head': [], 'repeat': '', 'tail': []} )

        head = ' '.join(names.get('head', []))
        repeat = names.get('repeat', '')
        tail = ' '.join(names.get('tail', []))
        
        side = rigData.get('mirrorCode', '')
        
        QtWidgets.QTreeWidgetItem.__init__( self, [name, '', '', head, repeat, tail, '', side] )
        
        self.setCheckState( 1, Qt.Checked if card.visibility.get() else Qt.Unchecked )
        self.setFlags( Qt.ItemIsEnabled | Qt.ItemIsEditable | Qt.ItemIsSelectable )
    
    
    def rigTypeChanged(self, index):
        #print( self.options[index], self.card )
        with self.card.rigData as rigData:
        
            if self.options[index] == '-':
                del rigData['rigCmd']
            else:
                rigData['rigCmd'] = self.options[index]
            
        pdil.pubsub.publish('fossil rig type changed')
        
    
    def mirrorChanged(self, index):
        #print( self.mirrorOptions[index], self.card )
        #rigData = self.card.rigData
        if self.mirrorOptions[index] == '-':
            self.card.mirror = None
        
        elif self.mirrorOptions[index] == 'Yes':
            self.card.mirror = ''
            
        elif self.mirrorOptions[index] == 'Inherited':
            self.card.mirror = None
            
        elif self.mirrorOptions[index] == 'Skip':
            self.card.mirror = 'DO_NOT_MIRROR'
            
        elif self.mirrorOptions[index] == 'Yes:Twin':
            self.card.mirror = 'twin'
    
    
    def sideChanged(self, index):
        with self.card.rigData as rigData:
        
            if self.sideOptions[index] == '-':
                rigData['mirrorCode'] = ''
        
            elif self.sideOptions[index] == '<':
                rigData['mirrorCode'] = 'left'
            
            elif self.sideOptions[index] == '>':
                rigData['mirrorCode'] = 'right'
        
        self.card.setTempNames()
            
        self.treeWidget().namesChanged.emit()
    
    
    def buildControls(self):
        # Make the rig type option
        self.type = ComboBox()
        self.type.addItems( self.options )
        self.treeWidget().setItemWidget(self, 2, self.type)
        
        rigData = self.card.rigData
        
        # Set the rig type value
        cmd = rigData.get('rigCmd', '')
        if not cmd:
            cmd = '-'
        index = self.options.index(cmd) if cmd in self.options else -1
        if index > -1:
            self.type.setCurrentIndex(index)
        
        self.type.currentIndexChanged.connect( self.rigTypeChanged )
        
        # Make the mirror options
        self.mirror = ComboBox()
        self.mirror.addItems( self.mirrorOptions )
        self.treeWidget().setItemWidget(self, self.MIRROR_COL, self.mirror)
        
        if self.card.mirror is None:
            if self.card.isCardMirrored():
                self.mirror.setCurrentIndex(2)
            else:
                self.mirror.setCurrentIndex(0)
                
        elif self.card.mirror is False:
            self.mirror.setCurrentIndex(3)
        
        elif self.card.mirror == 'twin':
            self.mirror.setCurrentIndex(4)
            #self.cardMirror.setEnable(True)
        
        else:
            self.mirror.setCurrentIndex(1)
        
        self.mirror.currentIndexChanged.connect( self.mirrorChanged )
        
        # Make the side option
        self.side = ComboBox()
        self.side.addItems( self.sideOptions )
        self.treeWidget().setItemWidget(self, self.SIDE_COL, self.side)
        
        mirrorCode = rigData.get('mirrorCode', None)
        if mirrorCode == '':
            self.side.setCurrentIndex( self.sideOptions.index('-') )
            
        elif mirrorCode == 'left':
            self.side.setCurrentIndex( self.sideOptions.index('<') )
            
        elif mirrorCode == 'right':
            self.side.setCurrentIndex( self.sideOptions.index('>') )
        
        else:
            # &&& Offer to run the update script since rigData is out of date or corrupt.
            pass
        
        self.side.currentIndexChanged.connect( self.sideChanged )


"""
def cardJointBuildOrder():
    '''
    Returns the cards in the order joints should be built in.  Spaces complicate
    the rig build order, but this is probably a good 'build' order too, then
    space application comes again for all at the end.
    
    I think I can just use the cardHierarchy instead.
    '''
    
    cards = [temp[0] for temp in cardHierarchy()]
    
    return cards[1:]


def cardHierarchy():
    '''
    Returns a list of:
        [
            [ parentCardA, [<children cards of A>] ],
            [ parentCardB, [<children cards of B>] ],
            ...
        ]
    '''
    parentCards = [[None, []]]
    
    mirrored = {}
    
    # Also track parent and their children so we can lookup to add asymetrically made cards to child list
    parentCardsListed = {}
    
    for card in find.blueprintCards():
        if not card.parentCard:
            
            # Only pick up cards that are actually top level and not parented to a mirror side
            for j in card.joints:
                
                if j.info.get('options', {}).get('mirroredSide'):
                    mirrored[card] = j.extraNode[0]
                    break
            else:
                parentCards[0][1].append(card)
    
    def gatherChildren(cards):
        for card in cards:
            #ordered.append( card)
            children = card.childrenCards
            parentCards.append( [card, children] )
            parentCardsListed[card] = children
            gatherChildren(children)
            
    gatherChildren(parentCards[0][1])
    
    for card in mirrored:
        gatherChildren([card])
    
        # &&& Worried about the code sprawl due to how "parent" has changed over time.  Should .parentCard already handle this case?
        parentCard = card.parentCardJoint.card
        if parentCard:
            parentCardsListed[parentCard].append( card )
        else:
            raise Exception('How did this happen? {} has mirrored side set but no discernable parent'.format(card) )
    
    
    return parentCards
"""


def cardDeleteTriggerSetup(card):
    scriptJob( ad=(card.visibility, cardDeleted), kws=True, ro=True, p='Rig_Tool' )


def cardDeleted():
    proxyskel.postDeleteCleanup()
    pdil.pubsub.publish( 'fossil card deleted' )


class CardLister(QtWidgets.QTreeWidget):

    cardListerColumnWidths = [220, 30, 120, 160, 100, 100, 75, 40]
    
    namesChanged = Signal()
    
    def setup(self, scale=1.0):
        '''
        Since the widget is really built in the setupUi() call, some gui editing
        work must happen afterwards (adjusting the columns).  Other things could
        be done in __init__ but might as well do it all in one place.
        
        Args:
            scale: Compensation since table column widths are in pixels.
        '''
        for i, cw in enumerate(self.cardListerColumnWidths):
            self.setColumnWidth(i, cw * scale)
        
        self.itemClicked.connect(self.cardListerItemClicked)
        self.itemChanged.connect(self.newDataEntered)
        
        self.highlightedCards = set()
        
        self._dataChangeActive = True
        self.cardOrder = []
        self.allCards = []
        self.cardItems = {None: None}
        
        try:
            # &&& Look into how to properly do this in pyside 1
            self.header().setSectionResizeMode(CardRow.NAME_HEAD, QtWidgets.QHeaderView.Stretch)
        except:
            pass
        
        # Use disableUI context manager to prevent callbacks, and use self.uiActive in said callbacks
        self._uiStateStack = []
        self.uiActive = True
        
        # Setup the right click menu
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.cardListerRightClick)
    
    
    def cardListerRightClick(self, position):
        # item = self.itemAt(position) # Item is under the cursor but it's automatically selected so probably not needed
        
        menu = QtWidgets.QMenu()
        
        menu.addAction('Select all the controls').triggered.connect( self.selectAllControls )
        menu.addAction('Select all the joints').triggered.connect( self.selectAllJoints )
        
        menu.exec_(self.viewport().mapToGlobal(position))
    
    
    @staticmethod
    def selectAllControls():
        allControls = []
        for card in util.selectedCardsSoft():
            for ctrl, _, _ in card.getMainControls():
                allControls.append(ctrl)
                
                for key, sub in ctrl.subControl.items():
                    allControls.append(sub)
        
        select(allControls)


    @staticmethod
    def selectAllJoints():
        allJoints = []
        for card in util.selectedCardsSoft():
            allJoints += card.getRealJoints()
        
        select(allJoints)
    
    
    @contextlib.contextmanager
    def disableUI(self):
        self._uiStateStack.append( self.uiActive )
        
        self.uiActive = False
        
        yield
        
        self.uiActive = self._uiStateStack.pop()
    
    
    def newCardAdded(self, newCard):
        cardDeleteTriggerSetup(newCard)
        self.cardListerRefresh(True)
    
    
    def cardListerRefresh(self, force=False):
        
        if self.allCards == find.blueprintCards() and not force:
            #print('No Refresh A')
            return
        
        self.allCards = find.blueprintCards()
        
        cardOrder = find.cardHierarchy()
        
        # Exit if nothing has changed
        if self.cardOrder == cardOrder and not force:
            #print('No Refresh B')
            return
        
        self.cardOrder = cardOrder
        
        with self.disableUI():
            self._dataChangeActive = False
            self.clear()
            
            self.cardItems = {None: None}
            
            for parentCard, childrenCards in self.cardOrder:
                
                for childCard in childrenCards:
                    item = self.cardListerAddRow(childCard, self.cardItems[parentCard])
                    item.setExpanded(True)
                    self.cardItems[childCard] = item
            
    def updateHighlight(self):
        '''
        ..  todo::
            When subControls are easily identifiable, also check them
        '''
        with self.disableUI():
            selectedCards = set(util.selectedCardsSoft())
            selectedInUI = set(self.selectedItems())
            
            # Deselect any selected items
            self._dataChangeActive = False
            for item in selectedInUI:
                if item not in selectedCards:
                    self.setItemSelected(item, False)
            
            for card, item in self.cardItems.items():
                if card in selectedCards and card not in selectedInUI:
                    self.setItemSelected( item, True )

            
    def cardListerItemClicked(self, item, col):
        if self.uiActive:
            if CardRow.NAME_HEAD <= col <= CardRow.NAME_TAIL:
                self.editItem(item, col)
            elif col == CardRow.VIS_COL:
                if item.checkState(CardRow.VIS_COL) == Qt.Checked:
                    item.setCheckState(CardRow.VIS_COL, Qt.Unchecked)
                    item.card.visibility.set(0)
                else:
                    item.setCheckState(CardRow.VIS_COL, Qt.Checked)
                    item.card.visibility.set(1)
                
    
    def cardListerAddRow(self, card, parentItem):
        
        item = CardRow(card)
        
        if not parentItem:
            self.addTopLevelItem(item)
        else:
            parentItem.addChild(item)
               
        item.buildControls()
                    
        return item
    
    def newDataEntered(self, item, column):
        if self.uiActive:
            #print('new data', column, item)
            pass
        else:
            return
        
        if column == CardRow.CARD_NAME:
            cardName = item.text(column).strip()
            item.card.rename(cardName)
            item.setText(CardRow.CARD_NAME, item.card.shortName())
        
        if (CardRow.NAME_HEAD <= column <= CardRow.NAME_TAIL):  # or column == CardRow.SIDE_COL:
            with item.card.rigData as rigData:
                names = rigData.get( 'nameInfo', {'head': [], 'repeat': '', 'tail': []} )
                if column == 3:
                    names['head'] = item.text(column).strip().split()
                    
                elif column == 4:
                    names['repeat'] = item.text(column).strip()
                    
                elif column == 5:
                    names['tail'] = item.text(column).strip().split()
                
                elif column == CardRow.SIDE_COL:
                    rigData['mirrorCode'] = item.text(column).strip()
                    print( 'setting', rigData['mirrorCode'] )
                
                rigData['nameInfo'] = names
            
            item.card.setTempNames()
            
            self.namesChanged.emit()
            
    
    def newObjMade(self):
        
        if self.allCards == find.blueprintCards():
            #print('No new cards')
            return
        else:
            #print('New CARD!', set(find.blueprintCards()).difference(self.allCards) )
            self.cardListerRefresh(force=True)
    
    def updateNames(self, card):
        '''
        Given the card, refresh the name ui
        '''
        names = card.rigData.get( 'nameInfo', {'head': [], 'repeat': '', 'tail': []} )

        head = ' '.join(names.get('head', []))
        repeat = names.get('repeat', '')
        tail = ' '.join(names.get('tail', []))
        
        self.cardItems[card].setText(CardRow.NAME_HEAD, head)
        self.cardItems[card].setText(CardRow.NAME_REPEAT, repeat)
        self.cardItems[card].setText(CardRow.NAME_TAIL, tail)