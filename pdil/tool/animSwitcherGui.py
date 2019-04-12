from __future__ import print_function

import traceback

from pymel.core import formLayout, window, deleteUI, tabLayout, radioButtonGrp, scrollLayout, columnLayout, frameLayout, \
    text, rowColumnLayout, button, Callback, cmds, showWindow, currentTime

from .. import core
from .fossil import controllerShape, kinematicSwitch

class Gui(object):
    name = 'AnimationTool'
    
    settings = core.ui.Settings(
        "Space Switching Settings",
        {
            'key': True,
            'mode': 'range',
            
            'ikfkCollapsed': False,
            'spaceCollapsed': False,
            'zeroMainCollapsed': False,
            
            'activeTab': 1,
            
            # Zero Main Axes
            'tx0': True,
            'ty0': True,
            'tz0': True,
            'rx0': True,
            'ry0': True,
            'rz0': True,
        })
    
    # Valid modes for what times to operate on
    MODES = ['frame', 'range', 'all', 'selected']
    
    
    @staticmethod
    @core.alt.name( 'Anim Switch GUI' )
    def run():
        return Gui()
    
    def __init__(self):
        if window(self.name, ex=True):
            deleteUI(self.name)
            
        window(self.name)
        
        ass = formLayout()
        
        with tabLayout() as tab:
            tabLayout(tab, e=True, sc=lambda *args: setattr(self.settings, 'activeTab', tab.getSelectTabIndex()))
            with formLayout() as switcher:
            
                def setMode(modeName):
                    self.settings.mode = modeName
            
                self.rangeInput = radioButtonGrp(nrb=4, la4=[m.title() for m in self.MODES],
                    on1=Callback(setMode, self.MODES[0]),  # noqa e128
                    on2=Callback(setMode, self.MODES[1]),
                    on3=Callback(setMode, self.MODES[2]),
                    on4=Callback(setMode, self.MODES[3]),
                    )
                
                self.rangeInput.setSelect( self.MODES.index(self.settings.mode) + 1 )
            
                with scrollLayout() as utilities:
                    with columnLayout(adj=True):
                        
                        # Fk / Ik Switching
                        with frameLayout(l='Ik/Fk Switching', cll=True) as ikFkFrame:
                            self.settings.frameLayoutSetup(ikFkFrame, 'ikfkCollapsed')
                            with rowColumnLayout(nc=3, cw=[(1, 200), (2, 50), (3, 50)] ):
                                for card in core.findNode.allCards():
                                    for side in ['Center', 'Left', 'Right']:
                                        try:
                                            ik = card.getSide(side).ik
                                            fk = card.getSide(side).fk
                                            
                                            if ik and fk:
                                                text(l=ik.shortName())
                                                button(l='Ik', c=Callback(self.doIkFkSwitch, fk, True))
                                                button( l='Fk', c=Callback(self.doIkFkSwitch, ik, False) )
                                            
                                        except Exception:
                                            print( traceback.format_exc() )
                        
                        """
                        # Space Switching
                        with frameLayout(l='Space Switching', cll=True) as spaceFrame:
                            self.settings.frameLayoutSetup(spaceFrame, 'spaceCollapsed')
                            with columnLayout() as self.main:
                                with rowColumnLayout( nc=2 ):
                                    
                                    button( l='Switch', c=Callback(self.switch) )
                                
                                text(l='Control')
                                self.targets = textScrollList(h=200)
                                scriptJob( e=('SelectionChanged', Callback(self.update)), p=self.main )
                                
                                text(l='')
                                
                                self.presetFileChooser = optionMenu(l='Presets', cc=Callback(self.loadSpace))
                                self.presetFiles = []
                                for folder in spacePresets.SpacePresets.folders:
                                    folder = os.path.expandvars(folder)
                                    
                                    if not os.path.exists(folder):
                                        continue
                                    
                                    for f in os.listdir(folder):
                                        if f.lower().endswith('.json'):
                                            cmds.menuItem(l=f[:-5])
                                            self.presetFiles.append( folder + '/' + f )
                                    
                                self.spacePresetList = textScrollList(h=100)
                                button(l='Apply', c=Callback(self.applySpacePreset))
                                
                                self.update()
                        """
                        
                        """
                        # Main zeroing
                        with frameLayout(l='Zero Main Controller', cll=True) as zeroFrame:
                            self.settings.frameLayoutSetup(zeroFrame, 'zeroMainCollapsed')
                            with rowColumnLayout(nc=3):
                                with gridLayout(nrc=(2, 3)):
                                    toggles = []
                                    for attr in [t + a for t in 'tr' for a in 'xyz']:
                                        toggles.append( checkBox(l=attr) )
                                        self.settings.checkBoxSetup(toggles[-1], attr + '0')
                                    
                                    def setVal(val):
                                        for check in toggles:
                                            check.setValue(val)
                                        for attr in [t + a for t in 'tr' for a in 'xyz']:
                                            self.settings[attr + '0'] = val
                                        
                                with columnLayout(adj=True):
                                    button(l='All', c=Callback(setVal, True))
                                    button(l='Clear', c=Callback(setVal, False))

                                with columnLayout(adj=True):
                                    button(l='Apply', c=Callback(self.zeroMain))
                        """
                
                formLayout(switcher, e=True,
                    af=[  # noqa e128
                        (self.rangeInput, 'left', 0),
                        (self.rangeInput, 'top', 0),
                        (self.rangeInput, 'right', 0),
                        
                        (utilities, 'left', 0),
                        (utilities, 'bottom', 0),
                        (utilities, 'right', 0),
                        ],
                    
                    ac=(utilities, 'top', 0, self.rangeInput),
                )
            
            """
            with formLayout() as spaceTab:
                space = spacePresets.SpacePresets()
                
                formLayout(spaceTab, e=True,
                    af=[
                        (space.mainForm, 'top', 0),
                        (space.mainForm, 'bottom', 0),
                    ]
                )
                
                #button(save, e=True, c=Callback(space.save))
                #button(load, e=True, c=Callback(space.load))
            """
            
        #tabLayout(tab, e=True, tl=[(switcher, 'Switching'), (spaceTab, 'Spaces')] )
        tabLayout(tab, e=True, tl=[(switcher, 'Switching')] )
        
        tabLayout(tab, e=True, sti=self.settings.activeTab)
        
        formLayout(ass, e=True,
            af=[  # noqa e128
                (tab, 'top', 0),
                (tab, 'left', 0),
                (tab, 'right', 0),
                (tab, 'bottom', 0),
            ]
        )
        
        showWindow()

    def doIkFkSwitch(self, obj, isIk):
        mode, start, end = self.processRange()
        #ikFkSwitch(obj, start, end)
        print(mode, start, end)
        plug = controllerShape.getSwitcherPlug(obj)
        if isIk and cmds.getAttr(plug) == 1.0:
            print('Already IK, skipping')
            return
        
        elif not isIk and cmds.getAttr(plug) == 0.0:
            print('Already FK, skipping')
            return
        
        kinematicSwitch.ikFkSwitch(obj, start, end)
        print('doing switch')
        
    """
    def zeroMain(self):
                
        mode, start, end = self.processRange()
        print( mode, start, end )
        
        skip = []
        for axis in [t + a for t in 'tr' for a in 'xyz']:
            if not getattr(self.settings, axis + '0'):
                skip.append(axis)
        
        if mode != 0:
            allTimes = set()
            timeList = {}
            
            unkeyed = {}
            
            controllers = [c for c in core.findNode.controllers() if nodeType(c) == 'transform']
            
            # Determine the times each controller has keys
            for ctrl in controllers:
                keyTimes = lib.anim.getKeyTimes(ctrl)
                
                if mode != 2:
                    keyTimes = [t for t in keyTimes if start <= t <= end]
                
                if keyTimes:
                    timeList[ctrl] = keyTimes
                    allTimes.update(timeList[ctrl])
                else:
                    unkeyed[ctrl] = (ctrl.t.get(), ctrl.r.get())
            
            print( sorted(allTimes) )
            
            with nested(core.time.PreserveCurrentTime(), core.ui.NoAutokey(), core.ui.NoUpdate()):
                # Go through all the times resetting main
                for t in sorted(allTimes):
                    currentTime(t)
                    resetMain(skip)
                    
                    for ctrl, times in timeList.items():
                        if t in timeList[ctrl]:
                            setKeyframe(ctrl.t, ctrl.r)
                
                for ctrl, (trans, rot) in unkeyed.items():
                    for i, axis in enumerate('xyz'):
                        try:
                            ctrl.attr('t' + axis).set( trans[i] )
                        except:
                            pass
                        try:
                            ctrl.attr('r' + axis).set( rot[i] )
                        except:
                            pass
        else:
            resetMain()
    """

    """
    def applySpacePreset(self):
        if not self.presetMaster:
            return
            
        sel = self.spacePresetList.getSelectItem()
        if not sel:
            return
        
        mode, start, end = self.processRange()
        print( 'Applying preset %s to range %i:%i' % (sel[0], start, end), mode )
        spacePresets.apply(self.presetMaster[sel[0]], self.MODES[mode])

    def loadSpace(self):
        filename = self.presetFiles[self.presetFileChooser.getSelect() - 1]
        self.presetMaster = spacePresets.load(filename)
        
        self.spacePresetList.removeAll()
        for name in sorted(self.presetMaster):
            self.spacePresetList.append(name)
    """

    def processRange(self):
        mode = self.rangeInput.getSelect() - 1  # RadioCollections are 1-based
        if mode == 0:
            start, end = [currentTime()] * 2
            
        elif mode == 1:
            start, end = core.time.playbackRange()
        
        elif mode == 2:
            start, end = [None] * 2
        
        elif mode == 3:
            if not core.time.rangeIsSelected():
                start, end = [currentTime()] * 2
            else:
                start, end = core.time.selectedTime()
            
        return mode, start, end
        
    """
    def switch(self):
        '''
        ..  todo::
            * Possibly change display to ONLY show names that all controls contain.
        '''
        #start, end = self.start.getValue(), self.end.getValue()
        mode, start, end = self.processRange()
        
        selection = selected()
        if not selection:
            return
        
        with lib.misc.NoUpdate():
            for sel in selection:
                if self.targets.getSelectItem():
                    
                    targetSpace = self.targets.getSelectItem()[0]
                    if targetSpace not in skeletonTool.space.getNames( sel ):
                        warning( "{0} does not have space {1}, skipping".format( sel, targetSpace ) )
                        continue
                    
                    if mode != 0:
                        skeletonTool.space.switchRange( sel, targetSpace, (start, end) )
                    else:
                        skeletonTool.space.switchToSpace( sel, targetSpace )
        
    def update(self):
        self.targets.removeAll()
        
        sel = selected(type='transform')
        if sel:
            sel = sel[0]
            names = skeletonTool.space.getNames(sel)
            if names:
                for name in names:
                    self.targets.append(name)
            else:
                pass
                """