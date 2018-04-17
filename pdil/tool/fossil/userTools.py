from pymel.core import ls, selected, attributeQuery, xform

from ... import core


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