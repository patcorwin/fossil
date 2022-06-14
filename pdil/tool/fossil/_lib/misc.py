import pdil
from .._core import ids


def findSDK(obj):
    ''' Wrapper for pdil.anim.findSetDrivenKeys(), converting the driver node into a fossil idSpec.
    '''

    usingIdSpec = {}
    for destAttr, driveDatas in pdil.anim.findSetDrivenKeys(obj).items():
        usingIdSpec[destAttr] = [[ids.getIdSpec(driverNode), driveAttr, curve] for driverNode, driveAttr, curve in driveDatas]
            
    return usingIdSpec
        
        
_SDK_QUEUE = {}
        

def applySDK(obj, driven):
    ''' Wrapper for pdil.anim.applySetDrivenKeys(), coverting the driver spec into a node.
    '''
    global _SDK_QUEUE
    
    for destAttr, infos in driven.items():
        
        processedInfos = []
        
        for driverSpec, driveAttr, curveData in infos:
            try:
                driver = ids.readIdSpec(driverSpec)
            except Exception:
                driver = None

            if not driver:
                _SDK_QUEUE.setdefault(obj, {})[destAttr] = infos
                break
            
            if not driver.hasAttr(driveAttr):
                _SDK_QUEUE.setdefault(obj, {})[destAttr] = infos
                break
            
            processedInfos.append( [driver, driveAttr, curveData] )
            
        else:
            pdil.anim.applySetDrivenKeys(obj, {destAttr: processedInfos} )


def retrySDK():
    global _SDK_QUEUE
    failed = _SDK_QUEUE # Run through failed, and still failing simply get requeued
    _SDK_QUEUE = {}
    
    for obj, sdkData in failed.items():
        applySDK(obj, sdkData)


def restoreShape(ctrl, objectSpace=True):

    lead, key = ctrl.ownerInfo() if hasattr(ctrl, 'ownerInfo') else (ctrl, 'main')

    side, motionType = lead.getMotionKeys()
    card = lead.card
    #print(key, motionType, side, '------------------')
    card.restoreShapes(objectSpace=objectSpace, targetKeys=[key], targetSide=side, targetMotion=motionType)
