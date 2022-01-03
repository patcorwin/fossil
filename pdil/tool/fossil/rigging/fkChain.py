from collections import OrderedDict

import pdil

from . import _util as util


'''
def activateFk( fkControl ):
    ctrls = [ (int(name), ctrl) for name, ctrl in fkControl.subControl.items() ]
    ctrls = sorted(ctrls)
    ctrls = [ ctrl for name, ctrl in ctrls ]
    ctrls.insert( 0, fkControl )
        
    for ctrl in ctrls:
        target = core.constraints.getOrientConstrainee( ctrl )

        trans = xform( target, q=True, ws=True, t=True)
        rot = xform( target, q=True, ws=True, ro=True)
        
        xform( ctrl, ws=True, t=trans)
        xform( ctrl, ws=True, ro=rot)

    switchPlug = _getSwitchPlug(fkControl)
    
    if switchPlug:
        switchPlug[0].node().listConnections(p=1, s=True, d=0)[0].set(0)
'''


class activator(object):
    
    @staticmethod
    def prep(leadControl):
        
        prepData = OrderedDict()
        prepData['lead'] = pdil.constraints.getOrientConstrainee( leadControl )
        
        for name, ctrl in leadControl.subControl.items():
            prepData[name] = pdil.constraints.getOrientConstrainee( ctrl )
        
        return prepData

    
    @staticmethod
    def harvest(data):
        return { name: util.worldInfo(obj) for name, obj in data.items() }

        
    @staticmethod
    def apply(data, values, leadControl):
        
        for name in data:
            ctrl = leadControl if name == 'lead' else leadControl.subControl[name]
            util.applyWorldInfo(ctrl, values[name])
        
