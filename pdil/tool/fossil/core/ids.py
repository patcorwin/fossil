import ast
import json

from pymel.core import cmds, ls, PyNode

from ....add import shortName


def cardPath(obj):
    '''
    If the object implements cardPath() (rig/anim related), return it, otherwise an empty string.
    '''

    '''
    Given a control, returns the string of plugs from the card that results in
    this control, ex: Elbow_L_Ctrl -> card('Bicep_Card').outputLeft.fk.subControl['1']
    '''
    
    if obj.__class__.__name__ == 'SubController':
        rigCtrl, key = obj.ownerInfo()
        subControl = ".subControl['{0}']".format(key)
    
    elif obj.__class__.__name__ == 'RigController':
        rigCtrl = obj
        subControl = ''

    else:
        return ''
    
    cardName = "'%s'" % rigCtrl.card.name()

    data = rigCtrl.card.rigData

    cmd = 'card({cardName}{cardId}).{motion}{subControl}'.format(
        cardName=cardName,
        cardId=", cardId='%s'" % data['id'] if 'id' in data else '',
        motion=rigCtrl.getMotionType(),
        subControl=subControl)
    
    #cmd = "FIND(%s)" % cardName + '.' + rigCtrl.getMotionType() + cmd
    
    return cmd


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
                targetCard = PyNode( shortName[cardShortName] )

    if not targetCard:
        return None

    #mainControl = targetCard.attr(motionType)
    print(targetCard, motionType, side)
    mainControl = getattr( getattr(targetCard, side), motionType)

    if subName:
        return mainControl.subControl[subName]
    else:
        return mainControl


def jointPath(obj):
    '''
    If this joint is connected to blueprint joint, return the cardPath, otherwise an emtpy string.
    
    &&& This needs to return a sensible string, be used in getIds, and consumed by the relevant functions.
    '''
    for connection in obj.message.listConnections(p=True):
        #if type(connection.node()).__name__ == 'BPJoint': # Test via string name to prevent import cycles
        if connection.node().__class__.__name__ == 'BPJoint':
            if connection.attrName() == 'realJoint':
                node = connection.node()
                return 'real:' + node.card.name() + '.' + str(node.card.joints.index(node)) + '|' + node.name()
            elif connection.attrName() == 'realJointMirror':
                return 'mirror:' + node.card.name() + '.' + str(node.card.joints.index(node)) + '|' + node.name()
    return ''
    

def toIdSpec(obj):
    '''
    Returns a dict of all the various ways to find the given object.
    '''
    
    ids = {
        'short': shortName(obj),
        'long': obj.longName(),
    }
    
    path_ = cardPath(obj)
    if path_:
        ids['cardPath'] = path_
    
    jpath = jointPath(obj)
    if jpath:
        ids['BPJ'] = jpath
    
    return ids


#getIds = toIdSpec


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


#findFromIds = fromIdSpec