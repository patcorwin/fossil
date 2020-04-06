from pymel.core import ls, selected, attributeQuery, xform, select

from ... import core
from ... import lib


@core.alt.name('Zero Controllers')
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


@core.alt.name('Select All Controllers')
def selectControlers():
    '''
    &&& I think this should recognize if you have a controller and select all the controls on that character,
    otherwise selected all of them in the scene to make working with multiple characters easier.
    '''
    select( core.findNode.controllers() )
    
    
@core.alt.name('Save Curves')
def saveCurves():
    
    filename = core.path.getTempPath('curve_transfer.ma')
    lib.anim.save(filename, objs=None, forceOverwrite=True, forceKeys=False, start=None, end=None)
    

@core.alt.name('Load Curves')
def loadCurves():
    
    filename = core.path.getTempPath('curve_transfer.ma')
    lib.anim.load(filename, insertTime=None, alterPlug=None, bufferKeys=True, targetPool=None)
    
    
@core.alt.name('Select Bindable Joints')
def selectBindableJoints():
    select(cl=True)
    for card in core.findNode.allCards():
        select(card.getOutputJoints(), add=True)