from __future__ import absolute_import, division, print_function

import ast
import collections
import json

from pymel.core import confirmDialog, cmds, ls, objExists, PyNode

from pdil.vendor import six

import pdil

from ._core import find
from ._core import ids
from ._lib import space
from ._lib import visNode
from ._lib2 import controllerShape
from . import util
from . import cardRigging
from .enums import RigState


_updaters = collections.OrderedDict()


def checkAll(ask=True):
    global _updaters
    
    toUpdate = []
    
    for updater in _updaters.values():
        updater.emptyStorage()
        if updater.check():
            toUpdate.append( updater )

    if toUpdate:
        if ask:
            res = confirmDialog(
                t='Updates required',
                m='This rig needs updating, run now?\n\n' + '\n'.join([u.__name__ for u in toUpdate]),
                b=['Yes', 'No'],
            )
            if res == 'No':
                return
        
        for updater in toUpdate:
            updater.fix()
            updater.emptyStorage()
    

class RegisterUpdater(type):
    def __init__(cls, name, bases, clsdict):
        global _updaters
        
        if name != 'Updater':
            assert 'check' in clsdict, 'check() not implemented on {}.  Return `True` if fixing is needed'.format(name)
            assert 'fix' in clsdict, 'fix() not implemented on {}'.format(name)
            
            _updaters[name] = cls
        
        super(RegisterUpdater, cls).__init__(name, bases, clsdict)
    

class Updater(six.with_metaclass(RegisterUpdater)):
    pass


class SharedShape(Updater):
    ''' 2021-11-26
    shaped shape used to have 'mo_is_shared' message attr, and an additional
    (message)attr for the type, which means it's not guaranteed you can identify
    the type attribute.
    
    Now it's a string attr `sharedShapeData` with the value being the shared shape type.
    '''

    dep_sharedAttr = 'mo_is_shared'
    dep_visAttr = 'sharedShape'
    dep_kinematicAttr = 'kinematicSwitch'
        
    oldVis = set()
    oldKinematic = set()
    
    @classmethod
    def emptyStorage(cls):
        cls.oldVis = set()
        cls.oldKinematic = set()
        
    
    @classmethod
    def check(cls):
        cls.oldVis = set( ls('*.' + cls.dep_visAttr) ) # PyMel mostly is able to clear out other instances with `set`
        cls.oldKinematic = set( ls('*.' + cls.dep_kinematicAttr) )
        
        if cls.oldVis or cls.oldKinematic:
            return True
            
        return False
    
        
    @classmethod
    def fix(cls):

        for plug in cls.oldVis:
            node = plug.node()

            if node.hasAttr(cls.dep_visAttr):
                node.addAttr( pdil.shape.SHARED_SHAPE, dt='string')
                node.attr(pdil.shape.SHARED_SHAPE).set(visNode.VIS_NODE_TYPE)
                node.deleteAttr(cls.dep_visAttr)
            
            if node.hasAttr(cls.dep_sharedAttr):
                node.deleteAttr(cls.dep_sharedAttr)

        for plug in cls.oldKinematic:
            node = plug.node()

            if node.hasAttr(cls.dep_kinematicAttr):
                node.addAttr( pdil.shape.SHARED_SHAPE, dt='string')
                node.attr(pdil.shape.SHARED_SHAPE).set(controllerShape.KINEMATIC_SHARED_SHAPE_TYPE)
                node.deleteAttr(cls.dep_kinematicAttr)
            
            if node.hasAttr(cls.dep_sharedAttr):
                node.deleteAttr(cls.dep_sharedAttr)

        return None
        
        
class CardsToRigData(Updater):
    ''' 2018-01-01
    An older version had individual attrs for rigging info, now it's all stored
    in string attr `fossilRigData` as json
    '''
    
    old = []
    
    @classmethod
    def emptyStorage(cls):
        cls.old = []
    
    @classmethod
    def check(cls):
        cls.old = [card for card in find.blueprintCards() if 'mirrorCode' not in card.rigData]
        
        return bool(cls.old)
        
    @classmethod
    def fix(cls):
        
        allIssues = {}
        
        for card in cls.old:
            print('- - - - ', card)
            issues = cls.updateToRigData(card)
            for issue_name in issues:
                allIssues.setdefault(issue_name, []).append(card)
        
        return allIssues if allIssues else None
                    
    @staticmethod
    def updateToRigData(card):
        
        if not card.hasAttr('fossilRigData'):
            card.addAttr( 'fossilRigData', dt='string' )
            card.fossilRigData.set('{}')
            card.addAttr( 'fossilRigState', dt='string' )
        
        card = PyNode(card) # Burp the interface, just in case
        
        issues = {}
        
        with card.rigData as rigData:
            # Update old attrs into rigData
            if card.hasAttr('nameInfo'):
                head, repeat, tail = util.parse(card.attr('nameInfo').get())
                rigData.update( {'nameInfo': {'head': head, 'repeat': repeat, 'tail': tail}} )
                card.deleteAttr('nameInfo')
            
            if card.hasAttr('rigCmd'):
                rigData.update( {'rigCmd': card.rigCmd.get()} )
                card.deleteAttr('rigCmd')
            
            if card.hasAttr('suffix'):
                side = card.attr('suffix').get() # Must use attr to avoid interface's .suffix
                
                if side.lower() in ('l', 'left'):
                    side = 'left'
                elif side.lower() in ('r', 'right'):
                    side = 'right'
                elif side == '':
                    pass
                else:
                    issues['side conversion'] = True
                
                if 'side conversion' not in issues:
                    rigData.update( {'mirrorCode': side} )
                    card.deleteAttr('suffix')
            
            if card.hasAttr('rigParameters'):
                d = cardRigging.ParamInfo.toDict(card.rigParams)
                
                ikParams = rigData.get('ikParams', {})
                ikParams.update(d)
                rigData.update( {'ikParams': ikParams} )
                card.deleteAttr('rigParameters')

            # Convert some of the old rig commands to the generic version
            if rigData.get('rigCmd') == 'Arm':
                ikParams = rigData.get('ikParams', {})
                #print('ik', ikParams, 'ikParams' in rigData)
                if 'name' not in ikParams:
                    ikParams['name'] = 'Arm'
                if 'endOrient' not in ikParams:
                    ikParams['endOrient'] = 'True_Zero'
                    
                rigData['rigCmd'] = 'IkChain'
                rigData['ikParams'] = ikParams

            elif rigData.get('rigCmd') == 'Leg':
                ikParams = rigData.get('ikParams', {})
                if 'name' not in ikParams:
                    ikParams['name'] = 'Leg'
                if 'endOrient' not in ikParams:
                    ikParams['endOrient'] = 'True_Zero_Foot'
                
                rigData['rigCmd'] = 'IkChain'
                rigData['ikParams'] = ikParams

            elif rigData.get('rigCmd') in ('Head', 'Neck'):
                rigData['rigCmd'] = 'TranslateChain'
            
            return issues
            
            
class StoredSpaces(Updater):
    ''' Updates fossilRigState
    - string name instead of integer
    - idspec instead of older methods
    '''
    rigStateToUpdate = []
    
    @classmethod
    def emptyStorage(cls):
        cls.rigStateToUpdate = []
    
    @classmethod
    def _checkCard(cls, card):
        for outputName, spaces in card.rigState.get(RigState.spaces, {}).items():
            for ctrlKey, spaceList in spaces.items():
                for spaceData in spaceList:
                    if 'type' in spaceData:
                        if isinstance( spaceData['type'], int ):
                            cls.rigStateToUpdate.append(card)
                            return
                            
                    elif 'target' in spaceData:
                        if not isinstance( spaceData['target'], collections.Mapping ):
                            cls.rigStateToUpdate.append(card)
                            return
                        
                    elif 'targets' in spaceData:
                        for target in spaceData['targets']:
                            if not isinstance( target, collections.Mapping ):
                                cls.rigStateToUpdate.append(card)
                                return
    
    @classmethod
    def check(cls):
        cls.rigStateToUpdate = []
        
        for card in find.blueprintCards():
            cls._checkCard(card)
        
        return bool(cls.rigStateToUpdate)
    
    
    @classmethod
    def fix(cls):
        
        fails = []
        
        for card in cls.rigStateToUpdate:
            allSpaceData = card.rigState[ RigState.spaces ]
            
            for outputName, spaces in allSpaceData.items():
                for ctrlKey, spaceList in spaces.items():
                    for spaceData in spaceList:
                        
                        if 'type' in spaceData:
                            if isinstance( spaceData['type'], int ):
                                spaceData['type'] = SpaceTypeName.oldValues[ spaceData['type'] ]
                        
                        if 'target' in spaceData:
                            ''' Original code
                            # First try the most modern way to decoding the target
                            if isinstance(target, collections.abc.Mapping ):
                                return ids.readIdSpec(target)
                            
                            # Fallback to lame way, which assumes a tuple of (name, cardPath)
                            elif objExists(target[0]):
                                return PyNode(target[0])
                                
                            elif target[1]:
                                obj = util.fromCardPath(target[1])
                                if obj:
                                    return obj
                            '''
                            if isinstance( spaceData['target'], list ):
                                success = False
                                if len(ls(spaceData['target'][0])) == 1:
                                    spaceData['target'] = ids.getIdSpec( PyNode(spaceData['target'][0]) )
                                    success = True
                                elif spaceData['target'][1]:
                                    obj = cls.fromCardPath(spaceData['target'][1])
                                    if obj:
                                        spaceData['target'] = ids.getIdSpec( PyNode(spaceData['target'][1]) )
                                        success = True
                                
                                if not success:
                                    fails.append(card)
                                
                        elif 'targets' in spaceData:
                            for i, target in spaceData['targets']:
                                if isinstance( target, list ):
                                    success = False
                                    if objExists(target[0]):
                                        target = ids.getIdSpec( PyNode(target[0]) )
                                        success = True
                                    elif target[1]:
                                        obj = cls.fromCardPath(target[1])
                                        if obj:
                                            spaceData['target'] = ids.getIdSpec( PyNode(target[1]) )
                                            success = True
                                    
                                    if not success:
                                        fails.append(card)
    
                for ctrlKey in list(spaces):
                    spaces[ctrlKey] = collections.OrderedDict(bidir=False, spaces=spaces[ctrlKey])
            
            with card.rigState as state:
                state[RigState.spaces] = allSpaceData
                
    
    @staticmethod
    def fromCardPath(s):
        if s.startswith('updateStoredSpaces.FIND('):
            return eval(s)

    class BLANK:
        pass

    @classmethod
    def FIND(cls, name, cardId=BLANK):
        '''
        A fancier wrapper for PyNode to make it easier to find Updaters by other
        critieria.
        
        The currently only use is looking up cards by their ids but in case it needs
        to be more flexible, it can be.
        
        ..  todo::
            Use the matching library to find closest matches
            This is AT ODDS with weapon attachments!  Due to the gluing, attachments
            could come up instead.  Maybe all cards prioritizes non-attachments stuff?
        '''
        
        if cardId is not cls.BLANK:
            cards = []
            names = []
            for c in find.blueprintCards():
                data = c.rigData
                if 'id' in data and data['id'] == cardId:
                    return c
                else:
                    cards.append(c)
                
                names.append(c.name())
            
            for c in cards:
                if c.name() == name:
                    return c

        else:
            for c in find.blueprintCards():
                if c.name() == name:
                    return c


'''
- user driven also need idspec fix, maybe?
    else: # This is the old method using just name and a cardPath
        # Rebuild the constraints on it.
        for constraintType, constData in spaceInfo['extra']['main'].items():
            getattr(pdil.constraints, constraintType + 'Deserialize')(target, constData, nodeDeconv=ids.fromIdSpec)

        align = target.getParent()
        for constraintType, constData in spaceInfo['extra']['align'].items():
            getattr(pdil.constraints, constraintType + 'Deserialize')(align, constData, nodeDeconv=ids.fromIdSpec)
'''
                            
                            
""" I don't think I need this because the spaceType from int to string takes care of it
UPDATE to change from fossil old spec instead (type -> idtype)
class FossilOldSpec(Updater):
    def check():
        find cards with
"""
                            
class SpaceTypeName(Updater):
    
    conditions = []
    matrices = []
    
    # These are the old enum values
    oldValues = {
        -1: 'EXTERNAL',
        0: 'ROTATE_TRANSLATE',
        1: 'TRANSLATE',
        2: 'ROTATE',
        3: 'ALT_ROTATE',
        4: 'POINT_ORIENT',
        5: 'DUAL_PARENT',
        6: 'DUAL_FOLLOW',
        7: 'MULTI_PARENT',
        8: 'MULTI_ORIENT',
        10: 'FREEFORM',
        11: 'USER',
        12: 'POINT_ROT',
    }
    
    @classmethod
    def emptyStorage(cls):
        cls.conditions = []
        cls.matrices = []
        
    
    @classmethod
    def check(cls):
        cls.conditions = ls( '*.spaceType', o=True, type='condition')
        cls.matrices = ls( '*.spaceName', o=True, type='fourByFourMatrix')
        return bool(cls.matrices) or bool(cls.conditions)
    
    @classmethod
    def fix(cls):
        for cond in cls.conditions:
            cond.addAttr( space.SPACE_TYPE_NAME, dt='string' )
            cond.attr( space.SPACE_TYPE_NAME ).set(
                cls.oldValues[ cond.spaceType.get() ]
            )
            cond.deleteAttr('spaceType')
            
        for matrix in cls.matrices:
            matrix.addAttr( space.SPACE_TYPE_NAME, dt='string' )
            matrix.attr( space.SPACE_TYPE_NAME ).set( matrix.spaceName.get() if matrix.spaceName.get() else '' )
            matrix.deleteAttr('spaceName')
            
        cls.conditions = []
        cls.matrices = []
            
            
            
            
            
            
            
class Constraints(Updater):
    
    update = []

    @classmethod
    def emptyStorage(cls):
        cls.update = []

    @classmethod
    def checkCard(cls, card):
        constData = card.rigState.get( RigState.constraints, {} )
        
        for side, sideData in constData.items():
            for ctrlKey, constraints in sideData.items():
                if 'align' not in constraints:
                    cls.update.append( card )
                    return

    @classmethod
    def check(cls):
        for card in find.blueprintCards():
            cls.checkCard(card)
        
        return bool(cls.update)
    
    @classmethod
    def fix(cls):
        for card in cls.update:
            constData = card.rigState.get( RigState.constraints, {} )
                
            for side, sideData in constData.items():
                for ctrlKey, constraints in sideData.items():
                    for oldKey, oldData in constraints.items():
                        '''
                        '''
                        
                        const, obj = oldKey.split()
                        
                        oldData['targets'] = [ ids.getIdSpec( fromIdSpec(t) ) for t in oldData['targets'] ]
        


""" fixed by updateConstraints()
def findConstraints(ctrl):
    align = core.dagObj.align(ctrl)

    constTypes = ['aim', 'point', 'parent', 'orient']
    res = {}
    for const in constTypes:
        ctrlConst = getattr( core.constraints, const + 'Serialize' )(ctrl, ids.toIdSpec)
        
        if align:
            alignConst = getattr( core.constraints, const + 'Serialize' )(align, ids.toIdSpec)
        else:
            alignConst = None
    
        if ctrlConst:
            res[const + ' ctrl'] = ctrlConst
            
        if alignConst:
            res[const + ' align'] = alignConst
    
    return res


def applyConstraints(ctrl, data):

    constTypes = ['aim', 'point', 'parent', 'orient']
    align = core.dagObj.align(ctrl)
    for const in constTypes:
        ctrlConst = data.get(const + ' ctrl')
        if ctrlConst:
            getattr(core.constraints, const + 'Deserialize')(ctrl, ctrlConst, ids.fromIdSpec)
        
        alignConst = data.get(const + ' align')
        if alignConst:
            getattr(core.constraints, const + 'Deserialize')(align, alignConst, ids.fromIdSpec)
"""
            
def fromIdSpec(spec):
    '''
    Given the dict from `getIds()`, returns an object if possible.
    
    ..todo:: Process card path and joint paths, (as defined in `getIds`)
    '''
    if 'cardPath' in spec:
        obj = readCardPath( spec['cardPath'] )
        if obj:
            return obj

    if 'BPJ' in spec:
        spec['BPJ']

    short = ls(spec['short'], r=True)
    if len(short) == 1:
        return short[0]
        
    longName = ls(spec['long'], r=True)
    if len(longName) == 1:
        return longName[0]
            
            
def readCardPath(cpath):
    res = ast.parse(cpath)
    
    body = res.body[0]
    
    #if isinstance(body, ast.Subscript):
    if isinstance(body.value, ast.Subscript):
        assert body.value.value.attr == 'subControl'
        cardCallRes = body.value.value.value.value
        subName = body.value.slice.value.s
        
        side = cardCallRes.attr
        motionType = body.value.value.value.attr
        cardCall = cardCallRes
        
        cardName = cardCall.value.args[0].s.rsplit('|', 1)[-1]
        
    else:
        cardCallRes = body.value
        subName = None
        
        motionType = cardCallRes.attr
        side = cardCallRes.value.attr
        cardCall = cardCallRes.value
        
        cardName = cardCall.value.args[0].s.rsplit('|', 1)[-1]

    
    if cardCall.value.keywords:
        assert cardCall.value.keywords[0].arg == 'cardId'
        cardId = cardCall.value.keywords[0].value
    else:
        cardId = None
        
    targetCard = None
    
    cards = cmds.ls( '*.fossilRigData', o=True, r=True, l=True )
    if cardId:
        for card in cards:
            data = json.loads( cmds.getAttr( card + '.fossilRigData' ) )
            if cardId == data.get('id', None):
                targetCard = PyNode(card)
                break
    
    if not targetCard:
        names = { card.rsplit('|', 1)[-1]: card for card in cards }
        if cardName in names:
            targetCard = PyNode( names[cardName] )
        else:
            shortNames = { card.rsplit('|', 1)[-1].rsplit(':', 1)[-1]: card for card in cards }
            cardShortName = cardName.rsplit(':', 1)[-1]
            if cardShortName in shortNames:
                targetCard = PyNode( shortNames[cardShortName] )

    if not targetCard:
        return None

    #mainControl = targetCard.attr(motionType)
    #print(targetCard, motionType, side)
    mainControl = getattr( getattr(targetCard, side), motionType)

    if subName:
        return mainControl.subControl[subName]
    else:
        return mainControl
            

# findSDK and applySDK updated to idSpec


class SDKListToDict(Updater):
    ''' SDK used to be an array but is now a dict and supports multiple drivers with blend weighted
    
    
    `findSetDrivenKeys` used to return a list like this:
    [
        [ <driven attr>, input_node, input_attr, dict_of_curve_data]
        [ 'length', PyNode('AAA'), 'tx', '<string of curve data>' ]
    ]
    
    Now it's a dict like this:
    {
        <driven attr>: [ [input_node, input_attr, dict_of_curve] ... ],
    }
    
    '''
    
    needsFix = {}
    
    
    @classmethod
    def emptyStorage(cls):
        cls.needsFix = {}
    
    
    @classmethod
    def check(cls):
        
        cls.needsFix = set()
        
        for card in find.blueprintCards():
            for outputName, drivenInfo in card.rigState.get(RigState.setDriven, {}).items():
                for ctrlKey, driven in drivenInfo.items():
                    if not isinstance(driven, dict):
                        cls.needsFix.setdefault( card, [] ).append(outputName, ctrlKey)

        return bool(cls.needsFix)
    
    
    @staticmethod
    def cardNeedsFix(card):
        for outputName, drivenInfo in card.rigState.get(RigState.setDriven, {}).items():
            for ctrlKey, driven in drivenInfo.items():
                if not isinstance(driven, dict):
                    return True
        
        return False
    
    
    @classmethod
    def fix(cls):
        for card, paths in cls.needsFix.items():
            with card.rigState as state:
                for outputName, ctrlKey in paths:
                    state[outputName][ctrlKey] = cls.convertToDict( state[outputName][ctrlKey] )
        
        cls.emptyStorage()
                

    @staticmethod
    def convertToDict(cls, listData):
        return { driven_attr: [input_node, input_attr, dict_of_curve_data]
        for driven_attr, input_node, input_attr, dict_of_curve_data in listData }


"""
def pdil.anim.applySetDrivenKeys_old(ctrl, infos):
    '''
    Create the setDrivenKeys on the ctrl with the specially formatted string
    list from `findSetDrivenKeys`.
    '''
    
    for info in infos:
        drivenAttr, driveNode, driveAttr, data = info
        
        cutKey(ctrl.attr(drivenAttr), cl=True)
        
        #keyData = [KeyData(*d) for d in data]
        
        if isinstance(data, list):
            setDrivenKeyframe( ctrl, at=[drivenAttr], v=-.14,
                currentDriver=driveNode.attr(driveAttr), driverValue=[data[0]['time']] )
        else:
            setDrivenKeyframe( ctrl, at=[drivenAttr], v=-.14,
                currentDriver=driveNode.attr(driveAttr), driverValue=[data['keys'][0]['time']] )
                
        dataToCurve(data, ctrl.attr(drivenAttr) )



def pdil.anim.findSetDrivenKeys_old(obj):
    '''
    Return a list of strings specially formatted with setDrivenKey data.
    
    ex: AAA.tx drives obj.length, so the return would be:
    [
        [ 'length', PyNode('AAA'), 'tx', '<string of curve data>' ]
    ]
    
    return = [
        ('obj attr name', <Input pynode>, 'input attr name' , 'str representing curve'),
        ...
    ]
    '''
    sdkCurves = obj.listConnections(s=True, d=False, type=SKD_CURVE_TYPES)
    
    curveInfos = []

    for sdkCurve in sdkCurves:
        input = sdkCurve.input.listConnections(p=1, scn=True)[0]
        dest = sdkCurve.output.listConnections(p=1, scn=True)[0].attrName()
        
        curveInfos.append( [dest, input.node(), input.attrName(), curveToData(sdkCurve)] )
    
    return curveInfos


def fossil.misc.applySDK_old(obj, info):
    ''' Wrapper for pdil.anim.applySetDrivenKeys(), coverting the driver spec into a node.
    '''
    #processed = [ [destAttr, ids.readIdSpec(driverSpec), driveAttr, curve]
    #    for destAttr, driverSpec, driveAttr, curve in info]
    global _SDK_QUEUE
    
    for destAttr, driverSpec, driveAttr, curve in info:
        try:
            driver = ids.readIdSpec(driverSpec)
        except Exception:
            driver = None
        
        if not driver:
            _SDK_QUEUE.append( [obj, destAttr, driverSpec, driveAttr, curve] )
            continue
        
        if not driver.hasAttr(driveAttr):
            _SDK_QUEUE.append( [obj, destAttr, driverSpec, driveAttr, curve] )
            continue
    
        pdil.anim.applySetDrivenKeys(obj, [[destAttr, driver, driveAttr, curve]])
    

def fossil.misc.retrySDK_old():
    global _SDK_QUEUE
    failed = _SDK_QUEUE # Run through failed, and still failing simply get requeued
    _SDK_QUEUE = []
    
    for obj, destAttr, driverSpec, driveAttr, curve in failed:
        applySDK(obj, [[destAttr, driverSpec, driveAttr, curve]])
    
    
def fossil.misc.findSDK_old(obj):
    ''' Wrapper for pdil.anim.findSetDrivenKeys(), converting the driver node into a fossil idSpec.
    '''
    
    driven = pdil.anim.findSetDrivenKeys(obj)
    
    for infos in driven.values():
        for info in infos:
            info[0] = ids.getIdSpec(info[0])
    
    return driven
        

"""