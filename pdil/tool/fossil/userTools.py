import itertools

from pymel.core import attributeQuery, ls, PyNode, select, selected, xform

import pdil

from . import _core as core
from ._lib2 import controllerShape
from .enums import RigData


@pdil.alt.name('Zero Controllers', 'Anim')
def zeroPose(useTrueZero=True):
    controllers = ls( selected(), '*.' + core.config.FOSSIL_CTRL_TYPE, o=True, r=True, sl=True )
    if not controllers:
        controllers = core.find.controllers()
        
    for control in controllers:
        try:
            control.t.set(0, 0, 0)
        except Exception:
            pass
            
        try:
            if control.hasAttr( 'trueZero' ) and useTrueZero:
                xform( control, os=True, ro=control.trueZero.get() )
            else:
                try:
                    control.rx.set(0)
                except Exception:
                    pass
                try:
                    control.ry.set(0)
                except Exception:
                    pass
                try:
                    control.rz.set(0)
                except Exception:
                    pass
        except Exception:
            pass

        try:
            # Set any user defined decimal attrs to their default (like length)
            attrs = control.listAttr(ud=True, k=True, s=True)
            for attr in attrs:
                if attr.type() in ['double', 'float']:
                    val = attributeQuery(attr.attrName(), listDefault=True, node=control)[0]
                    attr.set(val)
        except Exception:
            pass
            
        try:
            control.s.set(1, 1, 1)
        except Exception:
            pass


@pdil.alt.name('Select All Controllers', 'Anim')
def selectControlers(includeSwitchers=True):
    '''
    &&& I think this should recognize if you have a controller and select all the controls on that character,
    otherwise selected all of them in the scene to make working with multiple characters easier.
    '''
    
    sel = selected()
    
    mains = set()
    
    for obj in sel:
        if obj.hasAttr( core.config.FOSSIL_CTRL_TYPE ):
            main = core.find.mainGroup(fromControl=obj)
            if main:
                mains.add(main)
        elif obj.hasAttr(core.config.FOSSIL_MAIN_CONTROL):
            mains.add(obj)
                
    if not mains:
        mains = core.find.mainGroups()
    
    allCtrlIter = itertools.chain(core.find.controllers(main=m) for m in mains)
    
    if includeSwitchers:
        ikSwitches = {}
        allCtrls = []
        
        for ctrls in allCtrlIter:
            for ctrl in ctrls:
                allCtrls.append(ctrl)
                plug = controllerShape.getSwitcherPlug(ctrl)
                if plug:
                    ikSwitches[ plug.rsplit('|', 1)[-1] ] = plug
                
        #print( '\n'.join(ikSwitches.keys()) )
        allCtrls = [plug.split('.', 1)[0] for plug in ikSwitches.values()] + allCtrls
        
    else:
        allCtrls = list(allCtrlIter)
    
    select( allCtrls )
    
    
@pdil.alt.name('Save Curves', 'Anim')
def saveCurves():
    
    filename = pdil.path.getTempPath('curve_transfer.ma')
    
    objs = selected()
    
    ikSwitches = {}
    
    for obj in objs:
        plug = controllerShape.getSwitcherPlug(obj)
        if plug:
            ikSwitches[ plug.rsplit('|', 1)[-1] ] = plug
        
    objs += [ PyNode( plug.split('.', 1)[0] ) for plug in ikSwitches.values() ]
    
    pdil.anim.save(filename, objs=objs, forceOverwrite=True, forceKeys=False, start=None, end=None)
    

@pdil.alt.name('Load Curves', 'Anim')
def loadCurves():
    
    filename = pdil.path.getTempPath('curve_transfer.ma')
    pdil.anim.load(filename, insertTime=None, alterPlug=None, bufferKeys=True, targetPool=None)
    
    
@pdil.alt.name('Select Bindable Joints', 'Anim')
def selectBindableJoints():
    select(cl=True)
    for card in core.find.blueprintCards():
        try:
            if not card.rigData.get( RigData.accessory, False ):
                select(card.getOutputJoints(), add=True)
        except Exception:
            pass