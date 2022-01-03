import pdil
from .._core import ids


def findSDK(obj):
    ''' Wrapper for pdil.anim.findSetDrivenKeys(), converting the driver node into a fossil idSpec.
    '''
    return [ [destAttr, ids.getIdSpec(driverNode), driveAttr, curve]
        for destAttr, driverNode, driveAttr, curve in pdil.anim.findSetDrivenKeys(obj)]
        
        
def applySDK(obj, info):
    ''' Wrapper for pdil.anim.applySetDrivenKeys(), coverting the driver spec into a node.
    '''
    processed = [ [destAttr, ids.readIdSpec(driverSpec), driveAttr, curve]
        for destAttr, driverSpec, driveAttr, curve in info]
    
    pdil.anim.applySetDrivenKeys(obj, processed)
    
    
def restoreShape(ctrl, objectSpace=True):

    lead, key = ctrl.ownerInfo() if hasattr(ctrl, 'ownerInfo') else (ctrl, 'main')

    side, motionType = lead.getMotionKeys()
    card = lead.card
    #print(key, motionType, side, '------------------')
    card.restoreShapes(objectSpace=objectSpace, targetKeys=[key], targetSide=side, targetMotion=motionType)
