from __future__ import print_function, absolute_import

from cStringIO import StringIO
import importlib
import os
import sys
import time
import xml.etree.ElementTree as xml

from maya import OpenMayaUI

# I think the * imports are for the compiling in loadUiType
from PySide.QtGui import *
from PySide.QtCore import *

from PySide import QtGui
import pysideuic
from shiboken import wrapInstance

from pymel.core import *
#from pymel.core import optionVar, Callback, checkBox, frameLayout, menuItem


def mayaMainWindow():
    try:
        mayaMainWindowPtr = OpenMayaUI.MQtUtil.mainWindow()
        window = wrapInstance(long(mayaMainWindowPtr), QWidget)
    except Exception:
        print( 'No Main window found, assumed to be batch mode.' )
        return None
        
    return window


def deleteByName(name):
    for child in mayaMainWindow().children()[:]:
        if child.objectName() == name:
            child.setParent(None)
            child.close()

      
# originally named getClass
def getQtUIClass(uiFile, moduleName=None):
    '''
    Given a .ui file, compbiles it (if it's writable and newer than the .py),
    imports it and returns the actual class object
    
    .. todo:: Figure out the import moduleName
    '''

    if not moduleName:
        moduleName = os.path.basename( uiFile[:-3] )
    
    outpath = uiFile[:-2] + 'py'
    overwrite = False
    
    if os.path.exists(uiFile):
        if os.path.exists(outpath):
            if os.path.getmtime(uiFile) > os.path.getmtime(outpath) and os.access(uiFile, os.W_OK):
                overwrite = True
        else:
            overwrite = True

    if os.path.dirname(uiFile) not in sys.path:
        sys.path.append(os.path.dirname(uiFile))

    if overwrite:
        with open(outpath, 'w') as fid:
            pysideuic.compileUi(uiFile, fid, False, 4, False)
        m = importlib.import_module(moduleName)
        reload(m)

    else:
        m = importlib.import_module(moduleName)
    
    for attr in dir(m):
        cls = getattr(m, attr)
        if isinstance(cls, type):
            if cls.__module__ == moduleName:
                return cls
    
    
    '''

    pyfile = open("[path to output python file]\output.py", 'w')
    compileUi("[path to input ui file]\input.ui", pyfile, False, 4, False)
    pyfile.close()
    
    '''
    

def loadUiType(uiFile):
    '''
    Pyside lacks the "loadUiType" command, so we have to convert the ui file to py code in-memory first
    and then execute it in a special frame to retrieve the form_class.
    '''
    parsed = xml.parse(uiFile)
    widget_class = parsed.find('widget').get('class')
    form_class = parsed.find('class').text

    with open(uiFile, 'r') as f:
        o = StringIO()
        frame = {}
        
        pysideuic.compileUi(f, o, indent=0)
        pyc = compile(o.getvalue(), '<string>', 'exec')
        exec pyc in frame
        
        #Fetch the base_class and form class based on their type in the xml from designer
        form_class = frame['Ui_%s' % form_class]
        base_class = eval('QtGui.%s' % widget_class)
    return form_class, base_class


class VerticalLabel(QtGui.QWidget):
    '''
    Almost works!  'Below the line' letters like 'g' get cut off.
    '''
    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        #self.text = ''
        self.setText('')

    def paintEvent(self, event):
        painter = QPainter(self)
        #painter.setPen(Qt.black)
        painter.translate(self.textWidth, self.textHeight)
        painter.rotate(-90)
        if self.text:
            painter.drawText(0, 0, self.text)
        painter.end()
        
    def setText(self, text):
        self.text = text
        s = self.fontMetrics().size(0, text)
        
        # Rotating means the vals get swapped
        self.textWidth = s.height() + 4
        self.textHeight = s.width()
        
        self.resize(self.textWidth, self.textHeight)


class NoUpdate(object):
    '''
    Context manager to disable updating of modeling panels
    '''

    @staticmethod
    def getModelingPanels():
        return [p for p in getPanel(vis=True) if getPanel(to=p) == 'modelPanel']

    def __enter__(self):
        for panel in self.getModelingPanels():
            isolateSelect( panel, state=True )
                
    
    def __exit__(self, type, value, traceback):
        empty = selectionConnection()
        for panel in self.getModelingPanels():
            isolateSelect( panel, state=False )
            modelEditor( panel, e=True, mlc=empty )


class NoFilePrompt(object):
    '''
    Context manager to disable dialogs during file operations
    '''
    def __enter__(self):
        self.current = cmds.file( q=True, prompt=True )
        cmds.file( prompt=False )
        
    def __exit__(self, type, value, traceback):
        cmds.file( prompt=self.current )


class NoAutokey(object):
    def __enter__(self):
        self.state = autoKeyframe(q=True, state=True)
        autoKeyframe(state=False)
    
    def __exit__(self, type, value, traceback):
        autoKeyframe(state=self.state)


class RedirectOutput(object):
    def __enter__(self):
        self.tempOutput = StringIO.StringIO()
        self.origOutput = sys.stdout
        self.origErr = sys.stderr
        
        sys.stdout = self.tempOutput
        sys.stderr = self.tempOutput
        
        return self.tempOutput
    
    def __exit__(self, type, value, traceback):
        sys.stdout = self.origOutput
        sys.stderr = self.origErr


def isSuperUser():
    '''
    Quick stub for enabling advanced ui and other options.
    '''
    if os.environ['user'] == 'patc':
        return True
    return False
    

class Settings(object):
    '''
    Class to simplify using settings in optionVars.  All the settings are stored
    as a dict.  When the settings obj is created, any existing values will
    replace the defaults so it is easy to update.
    
    Ex:
        class SomeWindow():
            settings = Settings( "Some Window State",
                {
                    "maximized": True,
                    "advanced_mode": False,
                })
        
            def __init__(self):
                if self.settings.maximized:
                    # ...
                    
                if self.settings.advanced_mode:
                    # ...
                    
                om = optionMenu(l="Connector Type"):
                
                # This will give the option menu a change command that updates
                # the "conType" setting, as well as setting it to the current
                # "conType" value.
                self.settings.optionMenuSetup(om, 'conType')
    '''

    def __init__(self, name, info):
        object.__setattr__(self, '__name__', name )
        if name not in optionVar:
            optionVar[name] = str( info )
        else:
            existingValues = eval( optionVar[name] )
            info.update( existingValues )
            
        object.__setattr__(self, '__info__', info )

    def __getattr__(self, attr):
        return self.__info__[attr]
        
    def __setattr__(self, attr, val):
        # Updates the optionVar if something actually changed.
        update = False
        
        if attr not in self.__info__:
            self.__info__[attr] = val
            update = True
            
        elif self.__info__[attr] != val:
            self.__info__[attr] = val
            update = True
            
        if update:
            optionVar[self.__name__] = str( self.__info__ )

    # Support item interface to facilitate procedural getting/setting
    def __getitem__(self, key):
        return self.__getattr__(key)
        
    def __setitem__(self, key, value):
        self.__setattr__(key, value)

    #--------------------------------------------------------------------------
    #   The *Setup functions set the given control the specified setting value
    #   and sets the change command to update aforementioned setting.
    #
            
    #--------------------------------------------------------------------------
    def optionMenuSetup(self, _optionMenu, settingName):
        _optionMenu.setValue( self.__info__[settingName] )
        _optionMenu.changeCommand( Callback(self.optionMenuUpdate, _optionMenu, settingName) )
            
    def optionMenuUpdate(self, _optionMenu, settingName):
        setattr(self, settingName, _optionMenu.getValue() )
        
    #--------------------------------------------------------------------------
    def intFieldGrpSetup(self, field, settingName):
        field.setValue( [self.__info__[settingName], 1, 1, 1] )
        field.changeCommand( Callback(self.intFieldGrpUpdate, field, settingName) )
        
    def intFieldGrpUpdate(self, field, settingName):
        setattr(self, settingName, field.getValue()[0] )
        
    #--------------------------------------------------------------------------
    def checkBoxSetup(self, control, settingName, additionalCommand=None):
        control.setValue( self.__info__[settingName] )
        if additionalCommand:
            def compositeCommand():
                self.checkBoxUpdate(control, settingName)
                additionalCommand()
            checkBox( control, e=True, cc=Callback(compositeCommand) )
        else:
            checkBox( control, e=True, cc=Callback(self.checkBoxUpdate, control, settingName) )
        
    def checkBoxUpdate(self, control, settingName):
        setattr(self, settingName, control.getValue() )
        
    #--------------------------------------------------------------------------
    def frameLayoutSetup(self, control, settingName):
        frameLayout(
            control, e=True, cl=getattr(self, settingName),
            cc=Callback(self.frameLayoutUpdate, settingName, True),
            ec=Callback(self.frameLayoutUpdate, settingName, False)
        )
        
    def frameLayoutUpdate(self, settingName, val):
        setattr(self, settingName, val)

    #--------------------------------------------------------------------------
    def menuItemCheckboxSetup(self, control, settingName, additionalCommand=None):

        if additionalCommand:
            def compositeCommand():
                self.menuItemCheckboxUpdate(control, settingName)
                additionalCommand()
            menuItem( control, e=True, c=Callback(compositeCommand) )
        else:
            menuItem( control, e=True, c=Callback(self.menuItemCheckboxUpdate, control, settingName) )

        menuItem(control, e=True, cb=self.__info__[settingName])

    def menuItemCheckboxUpdate(self, control, settingName):
        self.__info__[settingName] = not self.__info__[settingName]
        menuItem(control, e=True, cb=self.__info__[settingName])
    
    
class NagCheck(object):
    '''
    Makes a function to easily track if a message should be disabled for a time.
    
    Used in warnOtherUsersCheckout()
    
    Ex:
    
        someCheck = lib.util.NagCheck('countTooHigh')
        
        if count > 8 and someCheck():
                
            if confirmDialog( m='The count is too high!',
                b=['Ok', 'Ok and skip this check today']) == 'Ok and skip this check today':
                someCheck.disable()
    
    '''
    
    day = 60 * 60 * 24  # Number of seconds in a day
    
    def __init__(self, timestampKey, secondsTillReset=day):
        self.timestampKey = timestampKey
        self.secondsTillReset = secondsTillReset
        if self.timestampKey in optionVar:
            self.active = bool(time.time() - optionVar[self.timestampKey] > self.secondsTillReset)
        else:
            self.active = True
        
    def __call__(self):
        if self.active:
            return True
        else:
            if time.time() - optionVar[self.timestampKey] > self.secondsTillReset:
                self.active = True
                return True
            else:
                return False
        
    def disable(self):
        self.timestampKey in optionVar
        optionVar[self.timestampKey] = time.time()
        self.active = False