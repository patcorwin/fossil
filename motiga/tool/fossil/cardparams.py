from __future__ import print_function, absolute_import

import contextlib
from functools import partial
import itertools

from Qt import QtWidgets
from Qt.QtCore import Qt

from pymel.core import cmds

from ... import add
from . import cardRigging


'''
class Cell(QtWidgets.QTableWidgetItem):
    
    def __init__(self, label='', checked=None):
        QtWidgets.QTableWidgetItem.__init__(self, label)
        self.setFlags( Qt.ItemIsEnabled | Qt.ItemIsSelectable )

        if checked is not None:
            self.setCheckState(Qt.Checked if checked else Qt.Unchecked)
'''


class Label(QtWidgets.QTableWidgetItem):
    
    def __init__(self, label='', checked=None):
        QtWidgets.QTableWidgetItem.__init__(self, label)
        self.setFlags( Qt.ItemIsEnabled ) # | Qt.ItemIsSelectable )

        #if checked is not None:
        #    self.setCheckState(Qt.Checked if checked else Qt.Unchecked)


class NOT_FOUND:
    pass


class CardParams(QtWidgets.QTableWidget):
    
    def __init__(self, *args, **kwargs):
        QtWidgets.QTableWidget.__init__(self, *args, **kwargs)
        
        self._disabled = False
        self._prevState = []
        
        self.currentCard = None
        self.params = []
        self.paramSceneOptions = {}
    
    def clearContents(self):
        try:
            self.cellChanged.disconnect(self.dataChange)
        except:
            pass
        QtWidgets.QTableWidget.clearContents(self)
        
    
    @contextlib.contextmanager
    def disableChangeCallback(self):
        '''
        Wrap programmatic changes to the ui to prevent it from updating the object.
        '''
        self._prevState.append( self._disabled )
        self._disabled = True
        yield
        self._disabled = self._prevState.pop()
    
    def dataChange(self, row, col):
        '''
        Callback for when data changes.
        '''
        if self._disabled or not self.params:
            return
        
        rigData = self.card.rigData
        params = rigData.setdefault('ikParams', {})
        
        #newVal = self.item(row, col).text()
        param = self.params[row]
        if param.type == cardRigging.ParamInfo.BOOL:
            params[param.kwargName] = bool(self.cellWidget(row, col).state() == Qt.Checked)
        
        elif param.type == cardRigging.ParamInfo.INT:
            try:
                params[param.kwargName] = int( self.item(row, col).text() )
            except Exception:
                with self.disableChangeCallback():
                    self.item(row, col).setText( params.get(param.kwargName, param.default))
            
        elif param.type == cardRigging.ParamInfo.FLOAT:
            try:
                params[param.kwargName] = float( self.item(row, col).text() )
            except Exception:
                with self.disableChangeCallback():
                    self.item(row, col).setText( params.get(param.kwargName, param.default))
            
        elif param.type == cardRigging.ParamInfo.ENUM:
            params[param.kwargName] = param.enum.values[self.cellWidget(row, col).currentIndex()]
            
        elif param.type == cardRigging.ParamInfo.STR:
            params[param.kwargName] = self.item(row, col).text()
            
        elif param.type == cardRigging.ParamInfo.NODE_0:
            self.card.extraNode[0] = self.paramSceneOptions[param][self.cellWidget(row, col).currentIndex()].message
            params[param.kwargName] = 'NODE_0'
        
        self.card.rigData = rigData
    
    def setInputField(self, card, row, param):
        '''
        Given a `Param`, build, and place, the correct ui element for the param's data type.
        '''
        self.params.append(param)
        
        if param.type == param.BOOL:
            checkBox = QtWidgets.QTableWidgetItem()
            state = Qt.Checked if card.rigData.get('ikParams', {}).get(param.kwargName, param.default) else Qt.Unchecked
            checkBox.setCheckState( state )
            self.setItem( row, 1, checkBox )
            
        elif param.type == param.INT:
            self.setItem( row, 1, QtWidgets.QTableWidgetItem(str(0 if not card.rigData.get('ikParams', {}).get(param.kwargName, param.default) else param.default)) )
            
        elif param.type == param.FLOAT:
            self.setItem( row, 1, QtWidgets.QTableWidgetItem(str(0.0 if not card.rigData.get('ikParams', {}).get(param.kwargName, param.default) else param.default)) )
            
        elif param.type == param.ENUM:
            dropdown = QtWidgets.QComboBox()
            dropdown.addItems(param.enum.keys())
            #dropdown.currentIndexChanged.connect( partial(self.enumChange, param) )
            #for key, val in param.enum.items():
            #    dropdown.addItem( key ).triggered.connect( partial(self.changeEnum, param.kwargName, val) )
            
            self.setCellWidget(row, 1, dropdown)
            
            try:
                enumVal = param.enum.values().index( card.rigData.get('ikParams', {}).get(param.kwargName, param.default) )
                dropdown.setCurrentIndex(enumVal)
                dropdown.currentIndexChanged.connect( partial(self.enumChange, param=param) )
            except:
                print( 'oerror with', param.kwargName, param.default, card, row )
            
        elif param.type == param.STR:
            val = card.rigData.get('ikParams', {}).get(param.kwargName, param.default)
            self.setItem( row, 1, QtWidgets.QTableWidgetItem(val) )
            
        elif param.type in (param.CURVE, param.NODE_0):  # Just accept curves, they are all I connect to
            dropdown = QtWidgets.QComboBox()
            # Get all the curve transforms under the skeletonBlueprint
            curves = cmds.listRelatives( cmds.listRelatives('skeletonBlueprint', type='nurbsCurve', f=True, ad=True), p=True, f=True)
            self.paramSceneOptions[param] = curves
            dropdown.addItems( curves )
            
            self.setCellWidget(row, 1, dropdown)
    
    def enumChange(self, index, param):
        rigData = self.card.rigData
        key, val = param.enum.items()[index]
        rigData.get('ikParams')[param.kwargName] = val
        
        self.card.rigData = rigData
    
    def addParams(self, card):
        self.card = card
        self.clearContents()
        self.params = []
        self.paramSceneOptions = {}
        
        #cardSettings = cardRigging.ParamInfo.toDict( card.rigParams )
        #cardSettings = card.rigData.get('ikParams', {})
        
        metaControl = cardRigging.availableControlTypes[card.rigData['rigCmd']]
        
        # &&& I'm looking at ik and fk args, but all the data is set to "ik", does fk have anything?
        
        totalCount = len( metaControl.ikInput ) + len(metaControl.fkInput)
        
        
        if totalCount == 0:
            self.setRowCount( 1 )
            self.setItem(0, 0, Label('No options'))
            self.setItem(0, 1, Label(''))
            return
        
        self.setRowCount( totalCount )
        
        # &&& I don't think there is a shared param #for kwargName, param in metaControl.shared.items() + metaControl.ikInput.items():
        for row, (kwargName, param) in enumerate(itertools.chain(metaControl.ikInput.items(), metaControl.fkInput.items())):
        
            #with columnLayout( p=self.controlSpecificParams, co=('both', 9)) as paramLayout:
                # Param takes multiple input types
            if isinstance( param, list ):
                
                dropdown = QtWidgets.QComboBox()
                dropdown.addItems( [p.name for p in param] )
                
                self.setCellWidget(row, 0, dropdown)
                
                value = card.rigData.get('ikKwargs', {}).get(kwargName, NOT_FOUND)
                if value is not NOT_FOUND:
                    type = cardRigging.ParamInfo.determineDataType(value)
                
                    for i, p in enumerate(param):
                        if p.type == type:
                            dropdown.setCurrentIndex(i)
                            self.setInputField(card, row, p)
                            break
                    else:
                        self.setInputField(card, row, param[0])
                
                else:
                    self.setInputField(card, row, param[0])
                
                '''
                menu = optionMenu(h=20, cc=alt.Callback(self.changeInputType, paramLayout, param, kwargName))
                for p in param:
                    menuItem( l=p.name )
                
                # Figure out which kind of input the existing data is if the card has the setting
                if kwargName in cardSettings:
                    type = cardRigging.ParamInfo.determineDataType(cardSettings[kwargName])
                
                    for p in param:
                        if p.type == type:
                            menu.setValue(p.name)
                            p.buildUI(card)
                            break
                    else:
                        p.buildUI(card)
                    
                else:
                    param[0].buildUI(card)
                '''
            # Param only takes one data type
            else:
                self.setItem(row, 0, Label(param.name))
                
                self.setInputField(card, row, param)
        
        self.cellChanged.connect(self.dataChange)
        

def update(self, card):
    
    if self.ui.cardParams.currentCard == card:
        return
    else:
        self.ui.cardParams.currentCard = card
    
    if card:
        
        self.ui.cardName.setText( add.shortName(card) )
        
        try:
            rigClass = cardRigging.availableControlTypes[ card.rigData.get('rigCmd') ]
        except Exception:
            rigClass = None
        
        if rigClass:
            if rigClass.__doc__:
                self.ui.cardDescription.setText(rigClass.__doc__)
                
    else:
        self.ui.cardName.setText( '<None selected>' )
        
        
    if card and card.rigData.get('rigCmd') in cardRigging.availableControlTypes:
        
        self.ui.cardType.setText( card.rigData['rigCmd'] )

        metaControl = cardRigging.availableControlTypes[card.rigData['rigCmd']]
        
        with self.ui.cardParams.disableChangeCallback():
            if metaControl.ik or metaControl.fk:
                self.ui.cardParams.addParams(card)
            else:
                self.ui.cardParams.clearContents()
    else:
        self.ui.cardParams.clearContents()
        self.ui.cardParams.setRowCount( 1 )
        self.ui.cardParams.setItem(0, 0, Label('No options'))
        self.ui.cardParams.setItem(0, 1, Label(''))