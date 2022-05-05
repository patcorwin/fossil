from __future__ import print_function, absolute_import

from functools import partial
from operator import eq
import traceback

from pymel.core import Callback, currentTime, menuItem, PyNode, selected, setParent

#from .. import _core as core
import pdil

from .fossil import controllerShape
from .fossil import kinematicSwitch
from .fossil import node
from .fossil import space


animToolSettings = pdil.ui.Settings( 'PDILAnimTool',
    {
        'switchMode': 'current', # Options are current, range and all
        'selectControlsIncludesSwitches': False,
    }
)


def switchSpaceGroup(objs, targetSpace):
    '''
    Switches a group of objects to a target space
    '''
    
    with pdil.ui.NoUpdate(objs):
        if pdil.time.rangeIsSelected():
            switch = partial(space.switchRange, range=pdil.time.selectedTime())
            
        elif animToolSettings.switchMode == 'current':
            switch = partial(space.switchFrame)
            
        elif animToolSettings.switchMode == 'range':
            switch = partial(space.switchRange, range=pdil.time.playbackRange())
        
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
            if node.leadController(obj).fossilCtrlType.get() in ['translate', 'rotate']:
                destType = 'Ik'
            else:
                destType = 'Fk'
            
            key = True
            
            if pdil.time.rangeIsSelected():
                s, e = pdil.time.selectedTime()
            elif animToolSettings.switchMode == 'current':
                s, e = [currentTime(q=1)] * 2
                key = False
            elif animToolSettings.switchMode == 'range':
                s, e = pdil.time.playbackRange()
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
            obj_under_cursor_is_selected = (sel[0] == obj) if sel else False
            
            if len(sel) <= 1 and (obj_under_cursor_is_selected if sel else True):
                menuItem(l='Switch to ' + destType, c=pdil.alt.Callback(kinematicSwitch.multiSwitch, [obj], s, e, key=key))
                
            else:
                sel = set(sel)
                sel.add(obj)
                
                '''
                switches = {}
                
                currentLeads = []
                
                for o in sel:
                    switchPlug = controllerShape.getSwitcherPlug(o)
                    switches[ switchPlug.rsplit('|')[-1] ] = o
                    currentLeads.append()'''
                
                currentLeads = [node.leadController(o) for o in sel if controllerShape.getSwitcherPlug(o)]
                
                if len(currentLeads) == 1:
                    menuItem(l='Switch to ' + destType, c=pdil.alt.Callback(kinematicSwitch.multiSwitch, currentLeads, s, e, key=key))
                elif len(currentLeads) > 1:
                    menuItem(l='Switch mutliple', c=pdil.alt.Callback(kinematicSwitch.multiSwitch, currentLeads, s, e, key=key))
            
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
