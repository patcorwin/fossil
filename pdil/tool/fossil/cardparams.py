from __future__ import print_function, absolute_import

import contextlib
from functools import partial
import itertools
from textwrap import dedent

try:
    basestring
except NameError:
    basestring = str

from ...vendor.Qt import QtWidgets
from ...vendor.Qt.QtCore import Qt

from pymel.core import cmds

import pdil
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
            params[param.kwargName] = bool(self.item(row, col).checkState() == Qt.Checked)
        
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
            self.setItem( row, 1, QtWidgets.QTableWidgetItem(str(card.rigData.get('ikParams', {}).get(param.kwargName, param.default))) )
            
        elif param.type == param.FLOAT:
            self.setItem( row, 1, QtWidgets.QTableWidgetItem(str( card.rigData.get('ikParams', {}).get(param.kwargName, param.default))) )
            
        elif param.type == param.ENUM:
            
            dropdown = QtWidgets.QComboBox()
            #dropdown.addItems( param.enum.keys() )
            dropdown.addItems( [enum.value.replace('_', ' ') for enum in param.enum ] )
            
            #dropdown.currentIndexChanged.connect( partial(self.enumChange, param) )
            #for key, val in param.enum.items():
            #    dropdown.addItem( key ).triggered.connect( partial(self.changeEnum, param.kwargName, val) )
            
            self.setCellWidget(row, 1, dropdown)
            
            try:
                #enumVal = list(param.enum.values()).index( card.rigData.get('ikParams', {}).get(param.kwargName, param.default) )
                currentEnumValue = card.rigData.get('ikParams', {}).get(param.kwargName, param.default)
                
                if isinstance(currentEnumValue, basestring):
                    currentEnumValue = param.enum( currentEnumValue )
                    
                enumIndex = list(param.enum).index(currentEnumValue)
                
                dropdown.setCurrentIndex(enumIndex)
                dropdown.currentIndexChanged.connect( partial(self.enumChange, param=param) )
            except Exception as ex:
                print( '! error with', param.kwargName, param.default, card, row )
                print(ex)
            
        elif param.type == param.STR:
            val = card.rigData.get('ikParams', {}).get(param.kwargName, param.default)
            self.setItem( row, 1, QtWidgets.QTableWidgetItem(val) )
            
        elif param.type in (param.CURVE, param.NODE_0):  # Just accept curves, they are all I connect to
            dropdown = QtWidgets.QComboBox()
            # Get all the curve transforms under the skeletonBlueprint
            curves = cmds.listRelatives( cmds.listRelatives('skeletonBlueprint', type='nurbsCurve', f=True, ad=True), p=True, f=True)
            self.paramSceneOptions[param] = curves
            if curves:  # &&& This can sometimes be empty, which causes the gui to choke on the error (in 2019, but not 2016)
                dropdown.addItems( curves )  # ERROR?
            
            self.setCellWidget(row, 1, dropdown)
    
    def enumChange(self, index, param):
        rigData = self.card.rigData
        val = list(param.enum)[index]
        rigData.setdefault('ikParams', {})[param.kwargName] = val.value
        
        self.card.rigData = rigData
    
    def addParams(self, card):
        self.card = card
        self.clearContents()
        self.params = []
        self.paramSceneOptions = {}
        
        #cardSettings = cardRigging.ParamInfo.toDict( card.rigParams )
        #cardSettings = card.rigData.get('ikParams', {})
        
        metaControl = cardRigging.registeredControls[card.rigData['rigCmd']]
        
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
                
            # Param only takes one data type
            else:
                self.setItem(row, 0, Label(param.name))
                
                self.setInputField(card, row, param)
        
        self.cellChanged.connect(self.dataChange)
        

def update(self, card, force=False):
    
    if self.ui.cardParams.currentCard == card and not force:
        return
    else:
        self.ui.cardParams.currentCard = card
    
    if card:
        
        self.ui.cardName.setText( pdil.shortName(card) )
        
        try:
            rigClass = cardRigging.registeredControls[ card.rigData.get('rigCmd') ]
        except Exception:
            rigClass = None
        
        description = ''
        if rigClass:
            if rigClass.__doc__:
                description = dedent(rigClass.__doc__)
                
        self.ui.cardDescription.setText(description)
                
    else:
        self.ui.cardName.setText( '<None selected>' )
        
        
    if card and card.rigData.get('rigCmd') in cardRigging.registeredControls:
        
        self.ui.cardType.setText( card.rigData['rigCmd'] )

        metaControl = cardRigging.registeredControls[card.rigData['rigCmd']]
        
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