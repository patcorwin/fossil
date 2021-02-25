import itertools

from pymel.core import attributeQuery, ls, PyNode, select, selected, xform

from ... import core
from ... import lib
from ...tool.fossil import space
from ...tool.fossil import controllerShape


@core.alt.name('Zero Controllers', 'Anim')
def zeroPose(useTrueZero=True):
    controllers = ls( selected(), '*.fossilCtrlType', o=True, r=True, sl=True )
    if not controllers:
        controllers = core.findNode.controllers()
        
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


@core.alt.name('Select All Controllers', 'Anim')
def selectControlers(includeSwitchers=True):
    '''
    &&& I think this should recognize if you have a controller and select all the controls on that character,
    otherwise selected all of them in the scene to make working with multiple characters easier.
    '''
    
    sel = selected()
    
    mains = set()
    
    for obj in sel:
        if obj.hasAttr( 'fossilCtrlType' ):  # &&& Need to establish the source of truth for this value
            main = space.getMainGroup(create=False, fromControl=obj)
            if main:
                mains.add(main)
        elif obj.hasAttr(core.findNode.MAIN_CONTROL_TAG):
            mains.add(obj)
                
    if not mains:
        mains = core.findNode.mainControls()
    
    allCtrlIter = itertools.chain(core.findNode.controllers(main=m) for m in mains)
    
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
    
    
@core.alt.name('Save Curves', 'Anim')
def saveCurves():
    
    filename = core.path.getTempPath('curve_transfer.ma')
    
    objs = selected()
    
    ikSwitches = {}
    
    for obj in objs:
        plug = controllerShape.getSwitcherPlug(obj)
        if plug:
            ikSwitches[ plug.rsplit('|', 1)[-1] ] = plug
        
    objs += [ PyNode( plug.split('.', 1)[0] ) for plug in ikSwitches.values() ]
    
    lib.anim.save(filename, objs=objs, forceOverwrite=True, forceKeys=False, start=None, end=None)
    

@core.alt.name('Load Curves', 'Anim')
def loadCurves():
    
    filename = core.path.getTempPath('curve_transfer.ma')
    lib.anim.load(filename, insertTime=None, alterPlug=None, bufferKeys=True, targetPool=None)
    
    
@core.alt.name('Select Bindable Joints', 'Anim')
def selectBindableJoints():
    select(cl=True)
    for card in core.findNode.allCards():
        select(card.getOutputJoints(), add=True)