from __future__ import print_function, absolute_import

import contextlib
from io import StringIO
import importlib
import logging
import os
import sys
import xml.etree.ElementTree as xml

from maya import OpenMayaUI

from pymel.core import confirmDialog as confirmDialog_orig
from pymel.core import (
    autoKeyframe, deleteUI, window, showWindow, optionVar, getPanel,
    isolateSelect, modelEditor, selectionConnection, cmds, Callback,
    checkBox, frameLayout, menuItem, progressWindow

)

# I think the * imports are for the compiling in loadUiType
#from ..vendor.Qt.QtGui import *
#from ..vendor.Qt.QtCore import *
from ..vendor.Qt import QtWidgets

# Load up the correct ui compiler
try:
    import pysideuic
    PYSIDE_VERSION = 1
except ImportError:
    try:
        import pyside2uic as pysideuic
        PYSIDE_VERSION = 2
    except ImportError:
        pysideuic = None
        PYSIDE_VERSION = None

# Load up the correct shiboken*.wrapInstance
try:
    from shiboken import wrapInstance
except ImportError:
    from shiboken2 import wrapInstance


PY_2 = sys.version_info[0] == 2 # Crass checking for python 2

try: # python 3 compatibility
    long
except NameError:
    long = int # long is just an int in py3

try:
    from importlib import reload
except ImportError:
    pass


#from pymel.core import *
#from pymel.core import optionVar, Callback, checkBox, frameLayout, menuItem

__all__ = [
    'singleWindow',
    'mayaMainWindow',
    'deleteByName',
    'convertToQt',
    'getQtUIClass',
    'loadUiType',
    'NoUpdate',
    'NoFilePrompt',
    'NoAutokey',
    'RedirectOutput',
    'Settings',
    'getGeometry',
    'setGeometry',
    'autoRedistribute',
    'ProgressHelper',
    'progressWin',
    'notify',
    'disableNotify',
]

# Make a top level 'module' so ui files can refer to it directly, aka the generated py code works.
VENDORIMPORT = 'QT_PDIL_vendored'
if VENDORIMPORT not in sys.modules:
    sys.modules[VENDORIMPORT] = sys.modules['pdil.vendor.Qt']


if 'qtCompileLog' not in globals():
    qtCompileLog = logging.getLogger('pdil.qt_compile')
    qtCompileLog.setLevel(logging.WARN)


@contextlib.contextmanager
def singleWindow(name, **kwargs):
    '''
    Ensure just one window of the give `name` exists, and shows it.  Passes kwargs to standard `window()` call.
    '''
    if window(name, exists=True):
        deleteUI(name)
        
    yield window(name, **kwargs)

    showWindow()


def mayaMainWindow():
    try:
        mayaMainWindowPtr = OpenMayaUI.MQtUtil.mainWindow()
        window = wrapInstance(long(mayaMainWindowPtr), QtWidgets.QWidget)
    except Exception:
        print( 'No Main window found, assumed to be batch mode.' )
        return None
        
    return window


def deleteByName(name):
    for child in mayaMainWindow().children()[:]:
        if child.objectName() == name:
            child.setParent(None)
            child.close()


def convertToQt(lines):
    '''
    Takes the lines from a .ui file converted to a .py file, from PySide2, and
    replaces the imports to use the vendored location of Qt.py.
    '''
    subs = [
        ('from PySide2 import', 'from %s import QtCompat,' % VENDORIMPORT),
        ('QtWidgets.QApplication.translate', 'QtCompat.translate')
    ]
    
    def parse(line):
        for older, newer in subs:
            line = line.replace(older, newer)
        
        return line

    parsedLines = [parse(line) for line in lines]
    return parsedLines


# originally named getClass
def getQtUIClass(uiFile, moduleName=None):
    '''
    Given a .ui file, compiles it (if it's writable and newer than the .py),
    imports it and returns the actual class object
    
    
    `moduleName` is the module name that the ui file will generate to be imported
    I can totally figure this out now instead of passing it in like a dingus
    
    .. todo:: Figure out the import moduleName
    '''
    
    if not moduleName:
        moduleName = os.path.basename( uiFile[:-3] )
    
    outpath = uiFile[:-2] + 'py'
    overwrite = False
    
    if os.path.exists(uiFile):
        qtCompileLog.debug('uiFile exists: ' + uiFile)
        if os.path.exists(outpath):
            qtCompileLog.debug('Compiled exists: ' + outpath)
            if os.access(uiFile, os.W_OK):
                if os.path.getmtime(uiFile) > os.path.getmtime(outpath):
                    overwrite = True
                    qtCompileLog.debug('uiFile is newer and can overwrite.  ' + uiFile)
                else:
                    qtCompileLog.debug('uiFile is older than the compiled file so will not be recompiled.  ' + uiFile)
            else:
                qtCompileLog.debug('uiFile is not writable, so will not be recompiled.  ' + uiFile)
        else:
            overwrite = True
            qtCompileLog.debug('uiFile is uncompiled so will compile.  ' + uiFile)
    else:
        qtCompileLog.debug('No ui file exists')

    if os.path.dirname(uiFile) not in sys.path:
        sys.path.append(os.path.dirname(uiFile))
    
    # pysideuic might be None so skip if it doesn't even exist.
    # Also, since convertToQt only works for pyside2, only update if that's what is available
    qtCompileLog.debug( 'Overwrite:{}   pysideuic:{}   ver:{}'.format(overwrite, pysideuic, PYSIDE_VERSION) )
    if overwrite and pysideuic and PYSIDE_VERSION == 2:
        with open(outpath, 'w') as fid:
            pysideuic.compileUi(uiFile, fid, False, 4, False)
        
        if PYSIDE_VERSION == 2:
            with open(outpath, 'r') as fid:
                lines = convertToQt(fid.readlines())
            
            with open(outpath, 'w') as fid:
                fid.write(''.join(lines))
            qtCompileLog.debug('Pyside2 compiled and written: ' + uiFile)
            
        m = importlib.import_module(moduleName)
        reload(m)

    else:
        m = importlib.import_module(moduleName)
    
    for attr in dir(m):
        cls = getattr(m, attr)
        if isinstance(cls, type):
            if cls.__module__ == moduleName:
                return cls
    
    
    r'''

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
        
        if PY_2:
            exec('''pyc in frame''')
        else:
            exec(pyc, frame)
        
        #Fetch the base_class and form class based on their type in the xml from designer
        form_class = frame['Ui_%s' % form_class]
        base_class = eval('QtGui.%s' % widget_class)
    return form_class, base_class


@contextlib.contextmanager
def NoUpdate(keepVisible=[]):
    '''
    Context manager to disable updating of modeling panels
    
    CAVEAT!  This used to be a great way to speed up stepping through the timeline
    but at some point (prior to 2019), this STOPS calculating, I'm assuming it's
    a parallel eval issue.
    
    Work around - add the things I'll be querying to the displayable.  They don't
    necessarily display but it does update properly.
    '''
    
    panels = [p for p in getPanel(vis=True) if getPanel(to=p) == 'modelPanel']
    
    for panel in panels:
        isolateSelect( panel, state=True)
        for obj in keepVisible:
            isolateSelect(panel, ado=obj)
            
    yield
    
    empty = selectionConnection()
    for panel in panels:
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

    def __contains__(self, key):
        return key in self.__info__

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
    
    
def getGeometry(qwindow):
    # Return x, y, width, height as a list which is json serializable.
    geo = qwindow.geometry()
    return [geo.x(), geo.y(), geo.width(), geo.height()]
    
    
def setGeometry(qwindow, geo):
    # Takes a list from `getGeometry()`, really for symmetry more than necessity.
    qwindow.setGeometry(*geo)


def autoRedistribute(layout):
    ''' verticalLayout/horizontalLayout helper to strecht the last item.
    '''
    children = layout.children()
    stretch = [0] * len(children)
    stretch[-1] = 1
    layout.redistribute(*stretch)


class ProgressHelper(object):
    amount = 0
    
    @classmethod
    def update(cls, increment=1, status=None):
        kwargs = {} if not status else {'status': status}
        cls.amount += increment
        progressWindow(e=True, progress=cls.amount, **kwargs )

    @staticmethod
    def isCancelled():
        return progressWindow(q=True, isCancelled=True)


@contextlib.contextmanager
def progressWin(title='', max=100, status=''):
    ''' Helper for progressWindow, passes in args
    '''
    ProgressHelper.amount = 0
    progressWindow(title=title, max=max, status=status)
    yield ProgressHelper
    progressWindow(endProgress=True)


NOTIFY_ENABLED = True


def notify(*args, **kwargs):
    ''' Wrapper for confirmDialog that returns nothing and is easily disabled for testing '''
    #global NOTIFY_ENABLED
    global _disableNotifyCount
    
    if _disableNotifyCount < 1:
        confirmDialog_orig(*args, **kwargs)
    else:
        
        if 'm' in kwargs:
            message = kwargs['m']
        elif 'message' in kwargs:
            message = kwargs['message']
        else:
            message = '<no message>'
        
        print('confirmDialog disabled with message "{}"'.format(message))


_disableNotifyCount = 0


@contextlib.contextmanager
def disableNotify():
    #global NOTIFY_ENABLED
    global _disableNotifyCount
    
    #prev = NOTIFY_ENABLED
    #NOTIFY_ENABLED = False
    
    _disableNotifyCount += 1
    
    try:
        yield
    finally:
        _disableNotifyCount -= 1
        #NOTIFY_ENABLED = prev