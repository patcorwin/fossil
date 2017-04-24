from __future__ import print_function, absolute_import

from maya.api import OpenMaya
from pymel.core import curve, parentConstraint, pointConstraint, PyNode, scriptNode, ls

from ..add import simpleName
from .. import core


def childByName(parent, childName):
    for child in parent.listRelatives():
        if simpleName(child) == childName:
            return child
    
    return None
    
    
def mainGroup(create=True, nodes=None):
    main = core.findNode.mainGroup()
    
    if main:
        return main
    
    if create:
        # Draw outer arrow shape
        main = curve( name='main', d=True, p=[(-40, 0, 20 ), (0, 0, 60 ), (40, 0, 20 ), (40, 0, -40 ), (0, 0, -20 ), (-40, 0, -40 ), (-40, 0, 20 )] )
        core.dagObj.lockScale(main)
        main.visibility.setKeyable(False)
        main.visibility.set(cb=True)
        
        if True:  # Put it in a default group
            core.layer.putInLayer(main, 'Controls')
        return main
    
    return None
    
    
def rootMotion(create=True, main=None):
    rootMotion = core.findNode.rootMotion(main)
    
    if rootMotion:
        return rootMotion
    
    if create:
        root = core.findNode.getRoot()
        if not root:
            # Unable to make root motion since the root doesn't exist.
            return None
    
        # Draw inner arrow shape
        rootMotion = curve( name='rootMotion', d=True, p=[(-32, 0, -12), (-32, 0, 20), (0, 0, 52), (32, 0, 20), (32, 0, -12), (-32, 0, -12)] )
        rootMotion.setParent( mainGroup() )
        core.dagObj.lockScale( rootMotion )
        #skeletonTool.controller.sharedShape.use(rootMotion)
        
        try:
            parentConstraint( rootMotion, root )
        except Exception:
            target = pointConstraint( root, q=True, tl=True )[0]
            parentConstraint( rootMotion, target )
            
        root.drawStyle.set( 2 )
        
        return rootMotion
    
    return None
    
    
def animInfoNode(create=True):
    '''
    Returns the MT_AnimationInfoNode, making it if it doesn't exist.
    '''

    animNode = None
    animNodes = ls('MT_AnimationInfoNode*')
    
    if len(animNodes) == 1:
        animNode = animNodes[0]
    elif not animNodes:
        if create:
            animNode = PyNode(scriptNode(name="MT_AnimationInfoNode", scriptType=0, sourceType=1))
        else:
            return None
    else:
        print("Multiple anim nodes found, ask Pat to help figure out which one is the correct one.")
        for obj in animNodes:
            if simpleName(obj) == 'MT_AnimationInfoNode':
                return obj
        else:
            animNode = animNodes[0]

    _addSeqAttr(animNode)
    return PyNode(animNode)  # Recast to ensure SequenceNode api


_dataSequenceAttr = [
    ['seqname', 'nam', OpenMaya.MFnStringData.kString],
    ['start',   'str', OpenMaya.MFnNumericData.kInt],   # noqa e241
    ['end',     'end', OpenMaya.MFnNumericData.kInt],   # noqa e241
    ['status',  'sts', OpenMaya.MFnNumericData.kInt],   # noqa e241
    ['object',  'obj', 'message'],                      # noqa e241
    ['data',    'dat', OpenMaya.MFnStringData.kString], # noqa e241
]


def _addSeqAttr(obj):
    '''
    Add `.sequence` attribute to a Script node to enable the custom Sequence api.
    Safe to run repeatedly since it only adds required attrs.
    '''
    if not obj:
        return
    
    if not obj.hasAttr('sequence'):
        mobj = core.capi.asMObject(obj)
        cattr = OpenMaya.MFnCompoundAttribute()
        nattr = OpenMaya.MFnNumericAttribute()
        tattr = OpenMaya.MFnTypedAttribute()
        mattr = OpenMaya.MFnMessageAttribute()

        sequence = cattr.create("sequence", 'seq')
        cattr.array = True

        for long, short, type in _dataSequenceAttr:
            if type is OpenMaya.MFnStringData.kString:
                newAttr = tattr.create(long, short, type)
            elif type is OpenMaya.MFnNumericData.kInt:
                newAttr = nattr.create(long, short, type, 0)
            elif type == 'message':
                newAttr = mattr.create(long, short)

            cattr.addChild(newAttr)

        mobj.addAttribute(sequence)
        
    if not obj.hasAttr( 'animNotes' ):
        obj.addAttr( 'animNotes', dt='string' )
        obj.animNotes.set('')