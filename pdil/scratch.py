

from pymel.core import delete
import pdil.tool.fossil as fossil


# from original spaces.py, obviously unfinished
def add_NEW(control, spec):
    '''
        [ { 'name': 'Parent',
        'target': ['b_Spine01', 'PyNode("SpineCard").outputCenter.fk'],
        'type': 1},
        { 'name': 'DoubleConstraint',
        'targets': [
            ['b_Spine01', 'PyNode("SpineCard").outputCenter.fk'],
            ['b_Spine02', 'PyNode("SpineCard").outputCenter.fk.subControls["2"]'],
            ]
        'type': 7}, ]
    '''
    spaceName = spec['name']
    mode = spec['type']


# from original spaces.py, named UNIFINISHED so might just be trash
def pruneUnused_UNFINISHED():
    # Need to loop through all the groups with targets
    trueTargets = []
    for target in trueTargets:
        if not target.r.listConnections(type='constraint') and target.t.listConnections(type='constraint'):
            delete(target)


# from original spaces.py, and obviously never worked or was used, probably trash
def findTargetees(obj):
    for c in ctrls:
        for spaceInfo in fossil.space.getTargetInfo(c):
            if str(obj) in str(spaceInfo.target):
                print( c, spaceInfo)


# Weight substitution that I don't think worked
def substitue(weightData, subs):
    ''' Take a dict of {'joint to get rid of': 'new joint name'}
    '''
    
    replace = {(weightData['joints'].index(newJoint), weightData['joints'].index(oldJoint)) for oldJoint, newJoint in subs.items() }
    
    newData = deepcopy(weightData)
    
    # Rebuild the weights, accounting that several joints might end up combinging into one
    for i, entry in enumerate(weightData['weights']):
        newEntry = OrderedDict()
        for jointIndex, val in entry:
            newEntry[ replace.get(jointIndex, jointIndex) ] = newEntry.get(jointIndex, 0) + val
    
        newData['weights'][i] = newEntry
    
    return newData
    
    
    
def auditSpaces():
    
    for ctrl in fossil.find.controllers():
        infos = fossil.space.getTargetInfo(ctrl)
        
        if ctrl.hasAttr( fossil.space.ENUM_ATTR ):
            print( f'\n-- {ctrl} -----------')
            for info in infos:
                print('   ', info)