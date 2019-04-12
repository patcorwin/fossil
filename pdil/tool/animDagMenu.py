from __future__ import print_function, absolute_import

from functools import partial
from operator import eq
import traceback

from pymel.core import Callback, cmds, currentTime, menuItem, PyNode, selected, setParent

from .. import core
from .. import lib
from ..melOverrides import dagMenuProc

from .fossil import controllerShape
from .fossil import kinematicSwitch
from .fossil import space


animToolSettings = core.ui.Settings( 'PDILAnimTool',
    {
        'switchMode': 'current', # Options are current, range and all
        'selectControlsIncludesSwitches': False,
    }
)


def switchSpaceGroup(objs, targetSpace):
    '''
    Switches a group of objects to a target space
    '''
    
    with core.ui.NoUpdate():
        if core.time.rangeIsSelected():
            switch = partial(space.switchRange, range=core.time.selectedTime())
            
        elif animToolSettings.switchMode == 'current':
            switch = partial(space.switchFrame)
            
        elif animToolSettings.switchMode == 'range':
            switch = partial(space.switchRange, range=core.time.playbackRange())
        
        elif animToolSettings.switchMode == 'all':
            switch = partial(space.switchRange, range=(None, None) )
        
        for obj in objs:
            switch(obj, targetSpace)


def animationSwitchMenu(objName):
    '''
    Called from dagMenuProc() so it's wrapped to catch any error.
    '''

    try:
        obj = PyNode(objName)
        
        plug = controllerShape.getSwitcherPlug(obj)
        
        spaces = space.getNames(obj)
        
        #-------
        # Mode
        #-------
        if plug or spaces:
            
            def setMode(mode):
                animToolSettings.switchMode = mode

            menuItem(l='Mode: Current Frame',  c=Callback(setMode, 'current'), cb=eq(animToolSettings.switchMode, 'current') )  # noqa e241
            menuItem(l='Mode: Playback Range', c=Callback(setMode, 'range'), cb=eq(animToolSettings.switchMode, 'range') )  # noqa e241
            menuItem(l='Mode: All',            c=Callback(setMode, 'all'), cb=eq(animToolSettings.switchMode, 'all') )  # noqa e241
            
        #-------
        # Ik/Fk
        #-------
        if plug:
            if cmds.getAttr(obj + '.fossilCtrlType') in ['translate', 'rotate']:
                destType = 'Ik'
            else:
                destType = 'Fk'
                
            if core.time.rangeIsSelected():
                s, e = core.time.selectedTime()
            elif animToolSettings.switchMode == 'current':
                s, e = [currentTime(q=1)] * 2
            elif animToolSettings.switchMode == 'range':
                s, e = core.time.playbackRange()
            elif animToolSettings.switchMode == 'all':
                s, e = None, None
            
            '''
            The dag menu can be triggered:
            * Object is selected but right click is on nothing
            * Object is selected but right click is on another object
            * Nothing is selected right clicking over an object
            
            Therefore it's a bunch of work to figure out if several things should be considered or not.
            '''
            sel = selected()
            if len(sel) <= 1 and (sel[0] == obj if sel else True):
                menuItem(l='Switch to ' + destType, c=core.alt.Callback(kinematicSwitch.ikFkSwitch, obj, s, e))
                
            else:
                sel = set(sel)
                sel.add(obj)
                
                switches = {}
                
                for o in sel:
                    switchPlug = controllerShape.getSwitcherPlug(o)
                    switches[ switchPlug.rsplit('|')[-1] ] = o
                
                if len(switches) == 1:
                    menuItem(l='Switch to ' + destType, c=core.alt.Callback(kinematicSwitch.ikFkSwitch, obj, s, e))
                else:
                    menuItem(l='Switch mutliple', c=core.alt.Callback(kinematicSwitch.multiSwitch, switches.values(), s, e))
            
        #-------
        # Spaces
        #-------
        if spaces:
            objsToSwitch = [obj]
            # Check if other selected objects have spaces to possibly swich to.
            sel = selected()
            if obj not in sel:
                sel.append(obj)
            
            if len(sel) > 1:
                allSpaces = []
                for o in sel:
                    tempSpaces = space.getNames(o)
                    if tempSpaces:
                        allSpaces.append(tempSpaces)
                        
                if len(allSpaces) > 1:
                    objsToSwitch = sel
                    spaces = set(allSpaces[0]).intersection( allSpaces[1] )
                    
                    for t in allSpaces[2:]:
                        spaces.intersection_update(t)
                        
            if spaces:
                menuItem(l='Switch space from %s to' % obj.space.get(asString=True), sm=True)
                for _space in sorted(spaces):
                    menuItem(l=_space, c=Callback(switchSpaceGroup, objsToSwitch, _space))
                setParent('..', m=True)
        
        #-------
        # Main
        #-------
        """
        if lib.dagObj.simpleName(obj) == 'main':
            isMain = True
            if objExists(CONSTRAINT_SET_NAME):
                if PyNode(CONSTRAINT_SET_NAME).elements():
                    menuItem(l='Main Control Re-Lock', c=Callback(relockMain))
                else:
                    menuItem(l='Main Control Unlock', c=Callback(unlockMain))
            else:
                menuItem(l='Main Control Unlock', c=Callback(unlockMain))
                
            menuItem(l='Main Zero', sm=True)
            menuItem(l='All')
            for attr in [trans + axis for trans in 'tr' for axis in 'xyz']:
                skip = [trans + axis for trans in 'tr' for axis in 'xyz']
                skip.remove(attr)
                menuItem(l='Zero ' + attr, c=Callback(resetMain, skip))
            setParent('..', m=True)
                
        else:
            isMain = False
        
        # Divider, if needed
        """
        if plug or spaces:
            menuItem(d=True)
            
    except Exception:
        print( traceback.format_exc() )


#print('-' * 5, 'About to run dag menu overrides')
dagMenuProc.override_dagMenuProc()
dagMenuProc.registerMenu(animationSwitchMenu)
#print('-' * 5, 'Overrides complete')