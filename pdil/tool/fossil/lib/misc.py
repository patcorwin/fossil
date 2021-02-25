from .... import lib
from ..core import ids


def findSDK(obj):
    ''' Wrapper for lib.anim.findSetDrivenKeys(), converting the driver node into a fossil idSpec.
    '''
    return [ [destAttr, ids.toIdSpec(driverNode), driveAttr, curve]
        for destAttr, driverNode, driveAttr, curve in lib.anim.findSetDrivenKeys(obj)]
        
        
def applySDK(obj, info):
    ''' Wrapper for lib.anim.applySetDrivenKeys(), coverting the driver spec into a node.
    '''
    processed = [ [destAttr, ids.fromIdSpec(driverSpec), driveAttr, curve]
        for destAttr, driverSpec, driveAttr, curve in info]
    
    lib.anim.applySetDrivenKeys(obj, processed)
    
    
def restoreShape(ctrl, objectSpace=True):

    lead, key = ctrl.ownerInfo() if hasattr(ctrl, 'ownerInfo') else (ctrl, 'main')

    motionType = lead.getMotionType().rsplit('.')[-1]
    side = lead.getSide()
    card = lead.card
    print(key, motionType, side, '------------------')
    card.restoreShapes(objectSpace=objectSpace, targetKeys=[key], targetSide=side, targetMotion=motionType)
