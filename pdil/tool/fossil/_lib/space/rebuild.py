from __future__ import absolute_import, division, print_function

from collections import namedtuple

import pdil

from ..._core import ids
from ... import log as skelLog

from . import agnostic
from . import bidirectional
from . import common
from . import constraintBased


def serializeSpaces(control):
    ''' Returns a dict of {'bidir': True/False: 'spaces': <list of space jsons> }
    
    The list looks like this:
        [
            {   'name': 'Parent',
                'target': [<id spec>],
                'type': 'ROTATE_TRANSLATE'},
                
            {   'name': 'DoubleConstraint',
                'targets': [
                    [<id spec>],
                    [<id spec>],
                ]
                'type': 'MULTI_PARENT'},
        ]
    '''
    
    spaceInfos = []
    for spaceInfo in agnostic.getTargetInfo(control):
        if not spaceInfo.target:
            raise Exception("{0}'s space {1} doesn't have a target".format(control, spaceInfo.name))
        
        if isinstance(spaceInfo.target, tuple):
            spaceInfos.append(
                {'name': spaceInfo.name,
                 'targets': [ids.getIdSpec(t) for t in spaceInfo.target],
                 'type': spaceInfo.type,
                 'extra': spaceInfo.extra}
            )
        else:
            spaceInfos.append(
                {'name': spaceInfo.name,
                 'target': ids.getIdSpec(spaceInfo.target),
                 'type': spaceInfo.type}
            )
            if spaceInfo.extra:
                spaceInfos[-1]['extra'] = spaceInfo.extra

    return {'bidir': common.isBidirectional(control), 'spaces': spaceInfos}


if '_queued_restore' not in globals():
    _queued_restore = []
    

Delayed = namedtuple('Delayed', 'controlSpec data pruneExtra objs')


def deserializeSpaces(control, data, pruneExtra=True):
    ''' Apply spaces obtained from `serializeSpaces()` to the given control.
    
    If a spec fails, it gets queued up.

    Args:
        control: The control to receive spaces
        data: Json from serializeSpaces
        pruneExtra: If True, remove spaces not given with `data` and ensure that order
    '''
    errors = []
    
    names = common.getNames(control)
    
    def addSpaceFunction(*args, **kwargs):
        global _queued_restore
        specs = kwargs.pop('_validate')

        func = bidirectional.add if data['bidir'] else constraintBased.add

        objects = [ids.readIdSpec(s) for s in specs]
        if all(objects):
            if func(*args, **kwargs):
                return True

        _queued_restore.append( Delayed( ids.getIdSpec(args[0]), data, pruneExtra, specs) )
        return False
        
    for spaceInfo in data['spaces']:
        name = spaceInfo['name']
        
        if name in names:
            continue
        
        type = spaceInfo['type']
        
#            log.debug('Name: {}  -  Type: {}'.format(name, type))
        #print('Name: {}  -  Type: {}'.format(name, type))
        
#            log.debug( spaceInfo )

        if type == common.Mode.USER:
            # Delete the existing object if it exists.
            # I think the point of this was to clean up the previous user driven, but I'm pretty sure I mistakenly
            # was only accounting for a single one.  Now, I think there just ends up being unused spaces which
            # don't really hurt anything.
            #userGroup = getGroup(USER_TARGET)
            #if target in userGroup.listRelatives():
            #    delete(target.getParent())
                
            target = agnostic.addUserDriven(control, name)

            #tempConstData = list( spaceInfo['extra']['main'].values() )

            # Rebuild the constraints on it.
            for constraintType, constData in spaceInfo['extra']['main'].items():
                getattr(pdil.constraints, constraintType + 'Deserialize')(target, constData, nodeDeconv=ids.readIdSpec)

            align = target.getParent()
            for constraintType, constData in spaceInfo['extra']['align'].items():
                getattr(pdil.constraints, constraintType + 'Deserialize')(align, constData, nodeDeconv=ids.readIdSpec)

        elif 'target' in spaceInfo:
            target = ids.readIdSpec(spaceInfo['target'])

            #if target:
            addSpaceFunction( control, target, name, mode=type, _validate=[spaceInfo['target']])
            #else:
            #    errors.append( str(spaceInfo['target']) )

        elif type in [common.Mode.MULTI_PARENT, common.Mode.MULTI_ORIENT, common.Mode.FREEFORM]:
            targets = [ids.readIdSpec(t) for t in spaceInfo['targets']]
            addSpaceFunction( control, targets, name, mode=type, rotateTarget=spaceInfo['extra'],
                              _validate=spaceInfo['targets'] )
        else:
            target1 = ids.readIdSpec(spaceInfo['targets'][0])
            target2 = ids.readIdSpec(spaceInfo['targets'][1])
            
            #if target1 and target2:
            addSpaceFunction( control, target1, name, mode=type, rotateTarget=target2,
                              _validate=spaceInfo['targets'] )
            #else:
            #    errors.append( 'MultiTarget:' + ' '.joint(spaceInfo['targets'])  )
    
    if pruneExtra:
        validNames = [si['name'] for si in data['spaces']]
        for name in set(names).difference(validNames):
            agnostic.remove(control, name)

        if set( common.getNames(control) ) == set(validNames):
            agnostic.reorder(control, validNames)
    
    if errors:
        skelLog.msg(
            'Error with spaces on ' + str(control) + ' missing Targets:\n    '
            + '\n    '.join(errors)
        )


def attemptDelayedSpaces():
    ''' Trys to rebuild spacess that failed earlier.
    '''

    global _queued_restore

    restored = []

    for info in _queued_restore:

        control = ids.readIdSpec(info.controlSpec)
        if control:
            for obj in info.objs:
                if not ids.readIdSpec(obj):
                    break
            else:
                deserializeSpaces(control, info.data, pruneExtra=info.pruneExtra)
                restored.append(info)

    for info in restored:
        _queued_restore.remove(info)