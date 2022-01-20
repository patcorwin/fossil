from __future__ import print_function, absolute_import

from collections import OrderedDict

from pymel.core import cutKey, getAttr, xform, currentTime, setAttr, setKeyframe, orientConstraint

import pdil

from ._lib2 import controllerShape
from . import node

from . import rigging
from ._lib import space

from .rigging import _util as util


commands = {
    'DogFrontLeg': rigging.dogFrontLeg,
    'DogHindleg': rigging.dogHindLeg,
    'SplineChest': rigging.splineChest,
    #'SplineChestV2': rigging.splineChest,
    'SplineNeck': rigging.splineNeck,
    'IkChain': rigging.ikChain,
    'FkChain': rigging.fkChain
}


def _getSwitchPlug(obj):  # WTF IS THIS??
    '''
    Given the object a bind joint is constrained to, return the switching plug.
    '''

    bone = pdil.constraints.getOrientConstrainee(obj)
    constraint = orientConstraint( bone, q=True )
    
    plugs = orientConstraint(constraint, q=True, wal=True)
    targets = orientConstraint(constraint, q=True, tl=True)
    
    for plug, target in zip(plugs, targets):
        if target == obj:
            switchPlug = plug.listConnections(s=True, d=False, p=True)
            return switchPlug


def activateFk( fkControl ):
    ctrls = [ (int(name), ctrl) for name, ctrl in fkControl.subControl.items() ]
    ctrls = sorted(ctrls)
    ctrls = [ ctrl for name, ctrl in ctrls ]
    ctrls.insert( 0, fkControl )
        
    for ctrl in ctrls:
        target = pdil.constraints.getOrientConstrainee( ctrl )

        trans = xform( target, q=True, ws=True, t=True)
        rot = xform( target, q=True, ws=True, ro=True)
        
        xform( ctrl, ws=True, t=trans)
        xform( ctrl, ws=True, ro=rot)

    switchPlug = _getSwitchPlug(fkControl)
    
    if switchPlug:
        switchPlug[0].node().listConnections(p=1, s=True, d=0)[0].set(0)


def multiSwitch(objs, start, end, key=True):
    ''' Takes a list of currently active controls and changes to the other kinematic state.
    '''
    
    currentLeads = [node.leadController(obj) for obj in objs]
    pairs = { obj: obj.getOtherMotionType() for obj in currentLeads }
    
    targetLeads = [other for obj, other in pairs.items() if other]
    
    
    if start is None or end is None:
        relevantControls = []
        relevantControls += currentLeads
        for leadControl in currentLeads:
            relevantControls += [obj for name, obj in leadControl.subControl.items()]
        for leadControl in targetLeads:
            relevantControls += [obj for name, obj in leadControl.subControl.items()]
        
        times = pdil.anim.findKeyTimes(relevantControls, start, end)
        if start is None:
            start = times[0]
            
        if end is None:
            end = times[-1]
        
    animStateSwitch(targetLeads, start, end, spaces={}, key=key)


def activateIk(ikController, start=None, end=None, key=True):

    leadControl = node.leadController(ikController)
    
    if start is None or end is None:
        otherLead = leadControl.getOtherMotionType()
        
        relevantControls = leadControl + [obj for name, obj in leadControl.subControl.items()] + \
            otherLead + [obj for name, obj in otherLead.subControl.items()]
        
        times = pdil.anim.findKeyTimes(relevantControls, start, end)
        if start is None:
            start = times[0]
            
        if end is None:
            end = times[-1]
    
    animStateSwitch([leadControl], start, end, spaces={})
        

def _clearKeys(objs, toClear):
    if not toClear:
        return
        
    start = toClear[0] + 1
    end = toClear[-1]
    if start < end:
        #print('clearing', start, end)
        cutKey(objs, t=(start, end), iub=False, cl=True, shape=False)


def animStateSwitch(leads, start, end, spaces={}, dense=False, key=True):
    ''' Kinematic and space switch over time as efficiently as possible.
    
    Args:
        leads: The lead controllers that will be activated
        start: Start frame
        end: End frame
        
        ??? SPACES ???
        
        dense: Key at each frame, basically baking the animation
        
    '''
    harvestTimes = OrderedDict()
    prep = {}
    harvestFunc = {}
    applyFunc = {}
    controls = {}
    allTimes = set()
    targets = {}
    
    controlsWithSpaces = list(spaces.keys())
    
    spaceOnlyData  = {}
    spaceOnlyTimes = {}
    spaceOnlyTargetValues = {}
    
    for lead in leads:
        
        other = lead.getOtherMotionType()
        if other:
            others = [obj for name, obj in other.subControl.items()] + [other]
                
        switcher = controllerShape.getSwitcherPlug(lead)
        print('switcher', switcher, lead)
        target = 0 if lead.getMotionKeys()[1] == 'fk' else 1
        opposite = (target + 1) % 2
        #print('Target=', target, '   Opposite=', opposite)
        
        targets[switcher] = target
        
        times = pdil.anim.findKeyTimes(others, start, end) if (not dense and other) else range(int(start), int(end + 1), 1)
        
        # If there are no `times`, we might be switching outside of currently keyed range so force keys to start and end.
        if not times:
            times = [start] if start == end else [start, end]
        
        # Unless switching a single frame, ignore the frames that are already at the target mode
        if len(times) != 1:
            times = [t for t in times if getAttr(switcher, t=t) != target ]
        
        controls[lead] = [obj for name, obj in lead.subControl.items()] + [lead]
        
        if times:
            harvestTimes[lead] = times
            
            #print(lead, times, controls[lead])
            
            if target == 1:
                activator = commands[ lead.card.rigData['rigCmd'] ].activator
            else:
                activator = commands[ 'FkChain' ].activator
            
            prep[lead] = activator.prep(lead)
            harvestFunc[lead] = activator.harvest
            applyFunc[lead] = activator.apply
            
            allTimes.update(times)
            
            if switcher: # Only clear keys if switching is possible
                toClear = []
                            
                for t in times:
                    if getAttr(switcher, t=t) == opposite:
                        toClear.append(t)
                    else:
                        _clearKeys(controls[lead], toClear)
                        toClear = []
                        
                _clearKeys(controls[lead], toClear) # Clears the final span
        
        # Check if a control will be switched to so we can just pre-change its space
        for ctrl in controlsWithSpaces[:]:
            if ctrl in controls[lead]:
                val = space.getNames(ctrl).index( spaces[ctrl] )
                spaceTimes = pdil.anim.findKeyTimes(ctrl.space, start, end, customAttrs=['space'])
                spaceTimes = [t for t in spaceTimes if getAttr(ctrl.space, t=t) != val ]
                
                requiredTimes = set(spaceTimes).difference( times )
                if requiredTimes:
                    allTimes.update(requiredTimes)
                    spaceOnlyData[ctrl]  = {}
                    spaceOnlyTimes[ctrl] = {}
                
                controlsWithSpaces.remove(ctrl)
        
    #print(controlsWithSpaces, 'controlsWithSpaces')
    # controlsWithSpaces are not in any kinematic switch
    for ctrl in controlsWithSpaces:
        val = space.getNames(ctrl).index( spaces[ctrl] )
        #pairs = keyframe(ctrl.space, q=True, t=(start, end), iub=True, tc=True, vc=True)
        #if pairs[0][0] != start:
        #    pairs.insert( [start, getAttr(ctrl.space, t=start) ] )
        #if pairs[-1][0] != end:
        #    pairs.append( [end, getAttr(ctrl.space, t=end) ] )
        times = pdil.anim.findKeyTimes(ctrl.space, start, end, customAttrs=['space'])
        times = [t for t in times if getAttr(ctrl.space, t=t) != val ]
        if times:
            allTimes.update(times)
            spaceOnlyData[ctrl] = {}
            spaceOnlyTimes[ctrl] = times
            spaceOnlyTargetValues[ctrl] = val
    
        #print( 'spaceOnlyTimes[ctrl]', spaceOnlyTimes[ctrl] )
    
    
    harvestValues = { lead: {} for lead in prep }
    allTimes = sorted(allTimes)
    #print('allTime', len(allTimes))
    #print('AllTimes', allTimes[0], allTimes[-1], prep.keys())
    # Harvest all the data first, so nothing is inadvertently altered
    for t in allTimes:
        currentTime(t)
        for lead, times in harvestTimes.items():
            if t in times:
                harvestValues[lead][t] = harvestFunc[lead]( prep[lead] )

        for ctrl, times in spaceOnlyTimes.items():
            if t in times:
                spaceOnlyData[ctrl][t] = util.worldInfo(ctrl)
        

    # Apply that results of the harvesting
    for t in allTimes:
        currentTime(t)
        for lead, times in harvestTimes.items():
            if t in times:
                applyFunc[lead]( prep[lead], harvestValues[lead][t], lead )
                if key:
                    setKeyframe( controls[lead], shape=False )
        
        
        for ctrl, times in spaceOnlyTimes.items():
            if t in times:
                ctrl.space.set( spaceOnlyTargetValues[ctrl] )
                util.applyWorldInfo(ctrl, spaceOnlyData[ctrl][t])
                if key:
                    setKeyframe( ctrl, shape=False )
                

    for switcher, target in targets.items():
        if not switcher:
            continue
            
        cutKey(switcher, t=(start, end))
        if key:
            setKeyframe(switcher, t=start, v=target)
            setKeyframe(switcher, t=end, v=target)
        else:
            setAttr(switcher, target)