'''
Definitions of custom PyMel node types.
'''
from __future__ import print_function, absolute_import

import collections
import itertools
import json
import re
import traceback

from maya.api import OpenMaya

import pymel.api
#from pymel.core import *
from pymel.core import cmds, select, objExists, PyNode, ls, nt, listRelatives, joint, hasAttr, removeMultiInstance, xform, mirrorJoint, delete, warning, dt, connectAttr, pointConstraint, parentConstraint, group, getAttr

from ..add import simpleName, shortName, meters
from .. import core
from .. import lib


from ..tool.fossil import cardRigging
from ..tool.fossil import controller
from ..tool.fossil import rig
from ..tool.fossil import log
from ..tool.fossil import proxy
from ..tool.fossil import settings
from ..tool.fossil import space
from ..tool.fossil import util

from . import registerNodeType


def findConstraints(ctrl):
    align = core.dagObj.align(ctrl)

    '''
    ctrlAim = core.constraints.aimSerialize(ctrl)
    alignAim = core.constraints.aimSerialize(align)

    res = {}
    if ctrlAim:
        res['main'] = ctrlAim
    if alignAim:
        res['align'] = alignAim

    return res
    '''
    constTypes = ['aim', 'point', 'parent', 'orient']
    res = {}
    for const in constTypes:
        ctrlConst = getattr( core.constraints, const + 'Serialize' )(ctrl)
        
        if align:
            alignConst = getattr( core.constraints, const + 'Serialize' )(align)
        else:
            alignConst = None
    
        if ctrlConst:
            res[const + ' ctrl'] = ctrlConst
            
        if alignConst:
            res[const + ' align'] = alignConst
    
    return res


def applyConstraints(ctrl, data):
    '''
    if 'main' in data:
        core.constraints.aimDeserialize(ctrl, data['main'])

    if 'align' in data:
        align = core.dagObj.align(ctrl)
        core.constraints.aimDeserialize(align, data['align'])
    '''
    print( ctrl, data, 'DATA' )

    constTypes = ['aim', 'point', 'parent', 'orient']
    align = core.dagObj.align(ctrl)
    for const in constTypes:
        ctrlConst = data.get(const + ' ctrl')
        if ctrlConst:
            getattr(core.constraints, const + 'Deserialize')(ctrl, ctrlConst)
        
        alignConst = data.get(const + ' align')
        if alignConst:
            getattr(core.constraints, const + 'Deserialize')(align, alignConst)


def findSDK(ctrl):
    align = core.dagObj.align(ctrl)
    
    data = {
        'main': lib.anim.findSetDrivenKeys(ctrl),
        'align': lib.anim.findSetDrivenKeys( align ) if align else []
    }
    
    if data['main'] or data['align']:
        return data
    else:
        return {}


def applySDK(ctrl, info):
    lib.anim.applySetDrivenKeys(ctrl, info['main'])
    lib.anim.applySetDrivenKeys(core.dagObj.align(ctrl), info['align'])
    

def getLinks(ctrl):
    links = []
    for attr in ctrl.listAttr(k=True) + [ctrl.t, ctrl.r, ctrl.s]:
        cons = attr.listConnections(s=True, d=False, p=True, type='transform')
        if cons:
            links.append( [cons[0].name(), attr.attrName()] )
    
    return links


def setLinks(ctrl, info):
    for src, destAttr in info:
        if objExists(src) and ctrl.hasAttr(destAttr):
            PyNode(src) >> ctrl.attr(destAttr)


def findLockedAttrs(ctrl):
    locked = []
    for attr in [t + a for t in 'tr' for a in 'xyz']:
        if ctrl.attr(attr).isLocked():
            locked.append(attr)
    return locked


def lockAttrs(ctrl, info):
    for attr in info:
        ctrl.attr(attr).lock()


def addExtraRigAttr(obj):
    if obj.hasAttr('extraRigNodes'):
        return

    mobj = core.capi.asMObject(obj)
    cattr = OpenMaya.MFnCompoundAttribute()
    mattr = OpenMaya.MFnMessageAttribute()

    extraNodes = cattr.create("extraRigNodes", 'ern')
    cattr.array = True

    link = mattr.create( 'link', 'lnk' )
    cattr.addChild(link)

    mobj.addAttribute(extraNodes)


def getMirror(name, tempJoint=None):
    '''
    Since mirroring can take extra substitutions, must do more work to determine mirror.
    
    
    ..  todo::
        * Have a more robust mirror tool
        * I might want to have some utility that collects mirror errors that
            is resetable.  I'm not sure how useful it will be, though.
    '''
    
    original = name
    
    if tempJoint:
        mirrorNode = util.isMirrored(tempJoint)
    
        if mirrorNode and isinstance( mirrorNode, Card ):
            # &&& This is super lame, overloading mirror with either a substitution scheme or 'twin'
            if mirrorNode.mirror and mirrorNode.mirror != 'twin':
                # &&& Need to wrap parsing into
                subst = util.strToPairs(mirrorNode.mirror)
                pair = util.identifySubst( name, subst )
                if pair:
                    name = name.replace( pair[0], pair[1] )
                
    for side, mirrorPairs in util._suffixSubstTable.items():
        if name.endswith( side ):
            mirror = name[:-2] + mirrorPairs[1]
            mirrors = ls(mirror)
            if len(mirrors) == 1:
                return PyNode(mirrors[0])
            if len(mirrors) > 1:
                for child in listRelatives( tempJoint.parent.realMirror ):
                    for m in mirrors:
                        if shortName(child) == shortName(m):
                            return m
            
    if name.count( '|' ):
        short = name.rsplit( '|', 1 )[-1]
        
        for side, mirrorPairs in util._suffixSubstTable.items():
            if short.endswith( '_' + side ):
                mirror = short[:-2] + mirrorPairs[1]
                if objExists(mirror):
                    return PyNode(mirror)
            
    # In case the extra subst was the only difference...
    if original != name:
        if objExists(name):
            return PyNode(name)
            
    return None


def _createTempJoint():
    '''
    Makes the special `TempJoint` used by the the Card.
    '''
    
    newJoint = joint()
    newJoint.tx.lock()
    
    newJoint.addAttr( 'parent', at='message' )
    newJoint.addAttr( 'children', at='message' )
    newJoint.addAttr( 'realJoint', at='message' )
    
    mObj = core.capi.asMObject(newJoint)
    mAttr = OpenMaya.MFnMessageAttribute()
    link = mAttr.create( 'realJointExtra', 'rje' )
    mAttr.array = True
    mObj.addAttribute(link)
    
    # Recast to provide proper interface.
    return PyNode(newJoint)


class NodeListProxy(object):
    '''
    Provides primitive list-like access to obj.extraRigNodes.
    Assign None to clear an entry.
    '''
    def __init__(self, obj):
        self.obj = obj

    def __setitem__(self, index, val):
        if val:
            addExtraRigAttr(self.obj)
            val.message >> self.obj.extraRigNodes[index].link
        else:
            if hasAttr( self.obj, 'extraRigNodes' ):
                removeMultiInstance( self.obj.extraRigNodes[index], b=True)
    
    def __getitem__(self, index):
        if not self.obj.hasAttr( 'extraRigNodes' ):
            return None
        
        for plug in self.obj.extraRigNodes:
            if plug.index() == index:
                con = plug.link.listConnections()
                if con:
                    return con[0]
                return None
                
        return None
    
    def __iter__(self):
        for i in self.obj.extraRigNodes.getArrayIndices():
            yield self[i]


class OutputControls(object):
    
    FK = 0
    IK = 1
    
    def __init__(self, obj, side):
        self.obj = obj
        self.side = side
        self.plug = self.obj.attr( 'output' + self.side )
    
    @property
    def ik(self):
        for p in self.plug:
            if p.attr( 'out' + self.side + 'Type' ).get() == self.IK:
                try:
                    return p.attr( 'outputLink' + self.side ).listConnections()[0]
                except Exception:
                    # If the output once existed but no longer does, we end up here
                    return None
        return None
        
    @ik.setter
    def ik(self, ctrl):
        for p in self.plug:
            if p.attr( 'out' + self.side + 'Type' ).get() == self.IK:
                ctrl.message >> p.attr( 'outputLink' + self.side )
                break
        else:
            index = sorted(self.plug.getArrayIndices())[-1] + 1 if self.plug.numElements() else 0
            ctrl.message >> self.plug[index].attr( 'outputLink' + self.side )
            self.plug[index].attr( 'out' + self.side + 'Type').set(self.IK)

    @property
    def fk(self):
        for p in self.plug:
            if p.attr( 'out' + self.side + 'Type' ).get() == self.FK:
                try:
                    return p.attr( 'outputLink' + self.side ).listConnections()[0]
                except Exception:
                    # If the output once existed but no longer does, we end up here
                    return None
        return None
        
    @fk.setter
    def fk(self, ctrl):
        for p in self.plug:
            if p.attr( 'out' + self.side + 'Type' ).get() == self.FK:
                ctrl.message >> p.attr( 'outputLink' + self.side )
                break
        else:
            index = sorted(self.plug.getArrayIndices())[-1] + 1 if self.plug.numElements() else 0
            ctrl.message >> self.plug[index].attr( 'outputLink' + self.side )
            self.plug[index].attr( 'out' + self.side + 'Type').set(self.FK)
        
    def __bool__(self):
        return bool(self.ik or self.fk)
    __nonzero__ = __bool__
    
    def __eq__(self, other):
        return self.obj == other.obj and self.side == other.side


# Rig types that don't actually produce joints
HELPER_CARDS = ('Group',)


def deprecatedSuffixSetter(obj, value):
    rigData = obj.rigData
    rigData['mirrorCode'] = value
    obj.rigData = rigData


def deprecatedRigCommandSetter(obj, value):
    rigData = obj.rigData
    rigData['rigCmd'] = value
    obj.rigData = rigData


def deprecated_nameInfo_get(obj):
    nameInfo = obj.rigData.get('nameInfo', {} )
    
    head = ' '.join(nameInfo.get('head', []))
    repeat = nameInfo.get('repeat', '')
    if repeat:
        repeat += '*'
    tail = ' '.join(nameInfo.get('tail', []))
    
    return (head + ' ' + repeat + ' ' + tail).strip()

    
def deprecated_nameInfo_set(obj, value):
    head, repeat, tail = util.parse(value)
    rigData = obj.rigData
    rigData['nameInfo'] = {'head': head, 'repeat': repeat, 'tail': tail}
    obj.rigData = rigData


class Card(nt.Transform):
    
    version = 1  # Look at updateRigState for a history of what has been updated.
    
    VIS_STORAGE = 'MoVisGroup'
    SPACE_STORAGE = 'spaces'
    SPACES_STORAGE = 'MoSpaces'
    LINK_STORAGE = 'MoCtrlLink'
    SDK_STORAGE = 'MoSDK'
    CUSTOM_ATTR_STORAGE = 'MoCustomAttr'
    
    parentCardLink = core.factory.SingleStringConnectionAccess('moParentCardLink')
    
    def updateRigState(self):
        state = self.rigState
        version = state.get('version', 0)
        
        '''
        1: Vis groups now have a level, which defaults to 1.
        '''
        if version < 1:
            if 'visGroup' in state:
                for controlVisGroupSettings in state['visGroup'].values():
                    for ctrl in controlVisGroupSettings.keys():
                        controlVisGroupSettings[ctrl] = (controlVisGroupSettings[ctrl], 1)
        
        state['version'] = self.version
        
        self.rigState = state
        
    
    @classmethod
    def _isVirtual(cls, obj, name):
        fn = pymel.api.MFnDependencyNode(obj)
        try:
            if fn.hasAttribute('moRigData'):
                return True
        except Exception:
            pass
        
        try:  # Deprecated version
            if fn.hasAttribute('skeletonInfo'):
                return True
            return False
        except Exception:
            pass
            
        return False
    
    #rigCommand          = core.factory.StringAccess('rigCmd')
    ikControllerOptions = core.factory.StringAccess('ikControllerOptions')
    fkControllerOptions = core.factory.StringAccess('fkControllerOptions')
    
    rigData             = core.factory.JsonAccess('moRigData')  # This replaces NameInfo, Suffic, RigCmd,
    rigState            = core.factory.JsonAccess('moRigState')  # &&& This replaces MoVisGroup, MoCtrlLink, MoSDK, MoCustumAttr, MoSpaces
    
    # Need to update these with direct references to rigData[*]
    
    # !*suffix -> mirrorCode*!
    suffix              = core.factory.DeprecatedAttr( lambda obj: obj.rigData.get('mirrorCode'), deprecatedSuffixSetter)
    nameInfo            = core.factory.DeprecatedAttr( deprecated_nameInfo_get, deprecated_nameInfo_set )
    
    rigCommand          = core.factory.DeprecatedAttr( lambda obj: obj.rigData.get('rigCmd'), deprecatedRigCommandSetter, mayaAttr=False)
    
    # &&& Eventually remove when all the rigs have been updated to use fkControllerOptions/ikControllerOptions
    rigOptions = core.factory.StringAccess('rigOptions')
    
    # This actually only does ik params.  Probably should be renamed to reflect this.
    rigParams = core.factory.StringAccess('rigParameters')
    
    
    def updateToRigData(self):
        rigData = self.rigData
        
        if self.hasAttr('nameInfo'):
            head, repeat, tail = util.parse(self.nameInfo.get())
            rigData.update( {'nameInfo': {'head': head, 'repeat': repeat, 'tail': tail}} )
        
        if self.hasAttr('rigCmd'):
            rigData.update( {'rigCmd': self.rigCmd.get()} )
        
        if self.hasAttr('suffix'):
            rigData.update( {'mirrorCode': self.suffix.get()} )
        
        if self.hasAttr('rigParameters'):
            d = cardRigging.ParamInfo.toDict(self.rigParams)
            
            ikParams = rigData.get('ikParams', {})
            ikParams.update(d)
            rigData.update( {'ikParams': ikParams} )

        if rigData.get('rigCmd') == 'Arm':
            ikParams = rigData.get('ikParams', {})
            print('ik', ikParams, 'ikParams' in rigData)
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

        self.rigData = rigData
        
    '''
    DEPRECATED, the lead controller's vis dictates groups (is this still deprecated or did I resurrect it?)
    
    Rig parts are organized by rigGroupName, falling back to the main
    control's visGroup, if it exists.  Otherwise the pieces are put as a
    child of main.  Use `getGroupName()` which has this logic.
    '''
    rigGroupName = core.factory.StringAccess('groupName')
        
    @property
    def outputCenter(self):
        return OutputControls(self, 'Center')

    @property
    def outputLeft(self):
        return OutputControls(self, 'Left')
        
    @property
    def outputRight(self):
        return OutputControls(self, 'Right')
        
    @property
    def center(self):
        return None
        
    @property
    def joints(self):
        joints = []
        for j in self.attr('joints'):
            connected = j.jmsg.listConnections()
            if connected:
                joints.append(connected[0])
                
        return joints
        
    @property
    def rigCommandClass(self):
        try:
            return cardRigging.registeredControls[self.rigCommand]
        except Exception:
            return None
        
    @property
    def buildIk(self):
        return not core.factory._getStringAttr( self, 'metaControl' ).count( 'skipIk;' )
        
    @buildIk.setter
    def buildIk(self, val):
        if val:
            if not self.buildIk:
                core.factory._setStringAttr( self, 'metaControl', core.factory._getStringAttr( self, 'metaControl' ).replace('skipIk;', ''))
        else:
            if self.buildIk:
                core.factory._setStringAttr( self, 'metaControl', core.factory._getStringAttr( self, 'metaControl' ) + 'skipIk;')

    @property
    def buildFk(self):
        return not core.factory._getStringAttr( self, 'metaControl' ).count( 'skipFk;' )
        
    @buildFk.setter
    def buildFk(self, val):
        if val:
            if not self.buildFk:
                core.factory._setStringAttr( self, 'metaControl', core.factory._getStringAttr( self, 'metaControl' ).replace('skipFk;', ''))
        else:
            if self.buildFk:
                core.factory._setStringAttr( self, 'metaControl', core.factory._getStringAttr( self, 'metaControl' ) + 'skipFk;')
                
    def getGroupName(self, controlSpec):
        '''
        Return the .rigGroupName, falling back to the visGroup if the main
        controller
        '''
        name = self.rigGroupName
        if not name:
            if 'visGroup' in controlSpec['main']:
                name = controlSpec['main']['visGroup']
            
        return name
        
    def isCardMirrored(self):
        '''
        Returns the card tagged to mirror (itself or a parent) or False if it doesn't mirror.
        
        ..  todo::
            Rename to findMirroredCard()
        '''
        if self.mirror is False:
            return False
        
        elif self.mirror is None:
            card = self
            while card.parentCard:
                if card.parentCard.mirror not in [None, False]:
                    return card.parentCard
                card = card.parentCard
                    
            return False
        else:
            return self
        
    @property
    def mirror(self):
        '''
        Can have 3 values:
            None = mirror has not been set
            False = It is part of a mirror, but do not mirror it
            <str> = A string of comma separated pairs, ex "oldA newA, oldB newB, ..."
        '''
        if self.hasAttr( 'mirrorSubst' ):
            val = core.factory._getStringAttr(self, 'mirrorSubst')
            if val == 'DO_NOT_MIRROR':
                return False
            else:
                return val
        return None

    @mirror.setter
    def mirror(self, s):
        '''
        `None` will remove it, otherwise should have an empty string or data like:
        "oldA newA, oldB newB, ..."
        '''
        if s is not None:
            if s is True:
                core.factory._setStringAttr(self, 'mirrorSubst', '')
            elif s is False:
                core.factory._setStringAttr(self, 'mirrorSubst', 'DO_NOT_MIRROR')
            elif s == 'twin':
                core.factory._setStringAttr(self, 'mirrorSubst', 'twin')
            else:
                core.factory._setStringAttr(self, 'mirrorSubst', s)
        else:
            if self.hasAttr( 'mirrorSubst' ):
                self.mirrorSubst.delete()

    def jointNaming(self):
        # &&& DEPRECATED?
        name = self.nameInfo.get()
        if name.count(' '):
            return name.split(' ')
        return name
        
    def start(self):
        '''
        Returns the first joint in the chain.
        '''
        return self.joints[0]
    
    def end(self):
        '''
        Returns the last joint in the chain that isn't a helper, unless there
        is only one joint and it is a helper.
        
        ..  todo::
            Use this liberally since it handles helper joints!
            There might probably be branching cards in the future, not sure how to agnostically handle that.
        '''
        for j in reversed(self.joints):
            if not j.isHelper:
                return j
        
        # This might not be great but for Group controls, where it IS a helper,
        # fallback to returing the first joint.
        return self.joints[0]
        
    def nameList(self, usePrefix=True, mirroredSide=False):
        '''
        Returns a list of names for the joints that will be made, helpers are skipped.
        New version with definable repeating areas.
        '''
        
        #suffix = '_' + self.suffix.get() if self.suffix.get() else ''
        suffix = self.rigData.get('mirrorCode', '')
        suffix = '_' + suffix if suffix else ''
        
        
        # Inherit the suffix from the mirrored card if no suffix was provided
        if not suffix:
            mirrorSrc = self.isCardMirrored()
            if mirrorSrc:
                #suffix = '_' + mirrorSrc.suffix.get() if mirrorSrc.suffix.get() else ''
                suffix = mirrorSrc.rigData.get('mirrorCode', '')
                suffix = '_' + suffix if suffix else ''
                
        
        # &&& Need to actually deal with suffix crap at some point
        if mirroredSide and suffix:
            suffix = '_R' if suffix == '_L' else '_L'
        
        prefix = 'b_' if usePrefix else ''
        
        names = self.rigData.get('nameInfo')
        if names:
            head = names.get('head', [])
            repeat = names.get('repeat', '')
            tail = names.get('tail', [])
        else:
            # &&& DELETE ME when rigData is all there is
            head, repeat, tail = util.parse(self.nameInfo.get())
        
        validJointCount = len( [j for j in self.joints if not j.isHelper] )
        
        if len(self.joints) == 1:
            if head:
                names = [ '{0}{1}{2}'.format( prefix, head[0], suffix ) ]
            else:  # Include the number if a repeat is specified but it's a single joint
                names = [ '{0}{1}{2}01'.format( prefix, repeat, suffix ) ]
        
        else:
            if not repeat:
                names = [ '{0}{1}{2}'.format(prefix, name, suffix) for name in head + tail ]
            else:
                repeatCount = validJointCount - len(head) - len(tail)
                
                startNumResult = re.search( '\d+$', repeat )
                if startNumResult:
                    startNum = int(startNumResult.group())
                    repeat = repeat[ : -len(startNumResult.group()) ] # Trim off the number since it's used to denote start num
                else:
                    startNumResult = 1
                sequentialNames = [ repeat + '{0:0>2}'.format(i) for i in range(startNum, startNum + repeatCount + 1) ]

                
                names = [ '{0}{1}{2}'.format(prefix, name, suffix) for name in head + sequentialNames + tail ]
        
        return names
        
    def findSuffix(self):
        '''
        Search parents if needed for a suffix using the same rules as mirror
        state (i.e. it is set to 'inherited').
        '''
        
        if not self.suffix.get() and self.mirror is None:
            p = self.parentCard
            if p:
                return p.findSuffix()
            else:
                return ''
        else:
            return self.suffix.get()
        
    def getOutputJoints(self):
        '''
        Returns a list of joints names made, excluding any helpers.
        '''
        
        return list(itertools.chain( *self.getOutputMap(includeHelpers=False).values() ))
    
    def getOutputMap(self, includeHelpers, usePrefix=True):
        '''
        Bad name, map of a temp joint and the joint(s) it makes
        '''
        output = collections.OrderedDict()
        
        names = iter( itertools.chain(self.nameList(usePrefix=usePrefix), itertools.cycle(['NOT_ENOUGH_NAMES'])) )
        
        for j in self.joints:
            if j.isHelper:
                if includeHelpers:
                    output[j] = ['']
            
            else:
                output[j] = [names.next()]
                
        if self.isCardMirrored():
            
            [ output[j].append(name) for j, name in zip(self.joints, self.nameList(usePrefix=usePrefix, mirroredSide=True) ) if not j.isHelper ]
        
        return output
        
    
    def getRealJoints(self, side=None):
        '''
        ..  todo:: This fails on weapons generally, which have a 'mirror by name'
                so both cards report having the joint.

                I might have to do a complex check on sided-ness and mirroring
                to determine the truth.
        '''
            
        suffix = self.findSuffix()
        if not suffix:
            primarySide = 'Center'
            otherSide = ''
        else:
            primarySide = settings.letterToWord[suffix]
            otherSide = settings.otherWord(primarySide)

        result = []
        for j in self.joints:
            if j.isHelper:  # On freeform, there might be several intermediate helpers
                pass
            
            if side is None or side == primarySide:
                if j.real:
                    result.append(j.real)
            
            if side is None or side == otherSide:
                if self.mirror is not False and j.realMirror:
                    result.append(j.realMirror)
                
        return result
        
    def output(self):
        '''
        Returns a list of (<temp joint>, <left output>, <optional right output>)
        Ex:
            [
            (tempJoint, 'b_Bicep_L', 'b_Bicep_R'),
            (temp1Joint, 'b_Elbow_L', 'b_Elbow_R'),
            (temp2Joint, 'b_Wrist_L', 'b_Wrist_R'),
            ]
        
        
        &&& THIS IS THE SAME AS THE getOutputMap!
        '''

        joints = []
        
        if self.isCardMirrored():
            
            # &&& I'm having trouble encapsulating this suffix code
            suffix = self.findSuffix()
            suffix = '_' + suffix
            swap = '_R' if suffix == '_L' else '_L'
                        
            for j, name in zip(self.joints, self.nameList() ):
                if not j.isHelper:
                    joints.append( (j, name, name.replace(suffix, swap) ) )
        else:
            for j, name in zip(self.joints, self.nameList() ):
                if not j.isHelper:
                    joints.append( (j, name) )
            
        return joints
    
    def getSide(self, side):
        '''
        Basically a wrapper for getattr(self, side)
        '''
        return getattr(self, 'output' + side.title())

    def getKinematic(self, side, kinematic):
        '''
        Helper to make it easier to procedurally go through output controls.
        '''

        return getattr(self.getSide(side), kinematic)
        
    def hasBuiltJoints(self):
        for j in self.joints:
            if not j.isHelper and j.real:
                return True
        
        return False
        
    def makeJoints(self):
        select(cl=True)
        
        data = self.rigData
        checkOffcenter = True
        if 'log ignores' in data:
            if 'Centerline' in data['log ignores']:
                checkOffcenter = False
        
        names = self.nameList()
        
        if len(names) < len(self.joints):
            # Buffer for dummy joints if needed
            if self.joints[ len(names) ].isHelper:
                names += ['WILL_BE_DELETED']
            else:
                raise Exception( 'Not enough names specified to build joints on {0}'.format(self) )
        
        for name, bpJoint in zip( names, self.joints):
            select(cl=True)
            j = joint(
                n=name,
                p=xform(bpJoint, q=True, ws=True, t=True),
                relative=False)
            j.msg >> bpJoint.realJoint
            if checkOffcenter:
                log.Centerline.check(j)
            
            '''
            &&& This might be ready for prime time.
            info = bpJoint.info
            if 'mechanical' in info and info['mechanical']:
                m = joint(
                    n=name + '_mech',
                    p=xform(bpJoint, q=True, ws=True, t=True),
                    relative=False)
                pointConstraint(j, m)
                bjJoint.addRealExtra(m)
                #m.msg >> bpJoint.realJointExtra
            '''
            
    def isAsymmetric(self):
        '''
        Returns True if this card or an ancestor explicitly does not mirror.
        '''
        if self.mirror is False:
            return True
            
        elif self.mirror is None:
            card = self
            while card.parentCard:
                if card.parentCard.mirror is False:
                    return True
                
                # This means the card has mirror set, we only want to crawl up till
                # mirroring is specifically on or off.
                if card.parentCard.mirror not in [False, None]:
                    return False
                    
                card = card.parentCard
                    
            return False
        else:
            return False
            
    def makeJoints2(self):
        '''
        Just like `makeJoints` but orients and parents them.  (I *THINK* that buildJoints further supercedes this)
        
        ..  todo::
            * If a joint orients as parent, it needs to determing the parent orientation first
                * Maybe this means tracking what joints are oriented, and if the joint
                  doesn't exist, imaginging how it will be oriented in the future.
                
        
            Needs to deal with pure helper cards, and helper joints in general, better
        '''
        select(cl=True)
        
        names = self.nameList()
        
        if len(names) < len(self.joints):
            # Buffer for dummy joints if needed
            if self.joints[ len(names) ].isHelper:
                names += ['WILL_BE_DELETED']
            else:
                raise Exception( 'Not enough names specified to build joints on {0}'.format(self) )
        
        newJoints = []
        for name, srcJoint in zip( names, self.joints):
            select(cl=True)
            j = joint(
                n=name,
                p=xform(srcJoint, q=True, ws=True, t=True),
                relative=False)
            j.msg >> srcJoint.realJoint
            newJoints.append(j)
        
        self.orientJoints()
        
        # Mirror the joints across X
        mirroredJoints = []
        
        isMirrored = self.isCardMirrored()
        
        if isMirrored:
            for tempJnt, j in zip(self.joints, newJoints):
                #dup = duplicate(j)[0]
                dup = PyNode(mirrorJoint(j, mirrorYZ=True, mirrorBehavior=True)[0])
                
                if self.suffix.get() == 'L':
                    newName = re.sub( '_L$', '_R', shortName(j) )
                if self.suffix.get() == 'R':
                    newName = re.sub( '_R$', '_L', newName )
                
                dup.rename( newName )
                # &&& Probably should note naming failure here
                #dup.tx.set(dup.tx.get()*-1)
                #dup.jointOrientX.set( dup.jointOrientX.get() - 180.0 )
                mirroredJoints.append(dup)
                
                if not hasAttr(tempJnt, 'realJointMirror'):
                    tempJnt.addAttr( 'realJointMirror', at='message' )
                dup.msg >> tempJnt.realJointMirror
        
        # Parenting is aggressive in case things are made out of order
        
            # Set parents for mirrored joints
            for tempJnt, realMirror in zip(self.joints, mirroredJoints):
                p = tempJnt.parent
                # Set the parent, unless the parent isn't mirrored (ex clav->spine)
                if p.card.isCardMirrored():
                    if p.realMirror and realMirror.getParent() != p.realMirror:
                        realMirror.setParent(p.realMirror)
                else:
                    if p.real and realMirror.getParent() != p.real:
                        realMirror.setParent(p.real)
                
                # Set any children
                for child in tempJnt.proxyChildren:
                    if child.card.isCardMirrored():
                        if child.realMirror:
                            if child.realMirror.getParent() != realMirror:
                                child.realMirror.setParent(realMirror)
                
                # See if the mirror exists as a future parent
                for futureChild in tempJnt.msg.listConnections(type=BPJoint):
                    if getReparentCommand(futureChild) == tempJnt:
                        if futureChild.real:
                            futureChild.real.setParent(tempJnt.realMirror)
                        
        # Set parents for non-mirrored/center joints
        for tempJnt, real in zip(self.joints, newJoints):
            # Handle anything that parents to the mirrored joint.
            mirrorParent = getReparentCommand(tempJnt)
            if mirrorParent:
                if mirrorParent.realMirror:
                    real.setParent(mirrorParent.realMirror)
                continue
            
            # Handle standard single/original sided parenting.
            if tempJnt.parent:
                p = tempJnt.parent
                if p.real and real.getParent() != p.real:
                    real.setParent(p.real)
            else:
                real.setParent(getTrueRoot())
            
            for child in tempJnt.proxyChildren:
                if child.real:
                    if child.real.getParent() != real:
                        child.real.setParent(real)
                if not isMirrored and child.realMirror:
                    if child.realMirror.getParent() != real:
                        child.realMirror.setParent(real)
                
        # &&& Delete helpers, though not making them in the first place would be better
        for j in self.joints:
            if j.isHelper:
                if j.realMirror:
                    delete(j.realMirror)
                if j.real:
                    delete(j.real)
    
    
    def buildJoints(self):
        '''
        Intended replacement for makeJoints, orientJoints and parentJoints (does all 3).
        
        ..  todo::
            Need to deal with unbuild parents (for regular and mirrored joints)
                and post command parenting.
            Additionally, freeform joints could pose a problem.  I might want
                to bulid all joints then parent as a separate loop
        '''
        
        if self.rigData.get( 'rigCmd' ) in HELPER_CARDS:
            return
        
        self.removeBones()
                
        trueRoot = core.findNode.getRoot(make='root')

        core.layer.putInLayer(trueRoot, 'Joints')
        trueRoot.drawStyle.set(2)
                
        data = self.rigData
        checkOffcenter = True
        if 'log ignores' in data:
            if 'Centerline' in data['log ignores']:
                checkOffcenter = False
        
        names = self.nameList()
        
        jointsThatBuild = [j for j in self.joints if not j.isHelper]
        
        if len(names) < len(jointsThatBuild):
            raise Exception( 'Not enough names specified to build joints on {0}'.format(self) )
        
        isMirrored = self.isCardMirrored()
        
        if isMirrored:
            getMirrorName = getMirrorNameFunction(self)
        
        for name, bpJoint in zip( names, jointsThatBuild):
            # Make the joint

            j = joint( None,
                n=name,
                p=xform(bpJoint, q=True, ws=True, t=True),
                relative=False)
            j.msg >> bpJoint.realJoint
            if checkOffcenter:
                log.Centerline.check(j)
            
            #------ Orient it -------
            state, target = bpJoint.getOrientStateNEW()

            upAxis = 'y'
            aimAxis = self.getAimAxis(bpJoint.suffixOverride)
            
            upVector = self.upVector(bpJoint.customUp)  # If not custom, will default to card's up arrow
                                
            #state, target = bpJoint.getOrientState()
            
            #print( bpJoint, state, target )
                        
            #------- Parent it (so orient as parent works) -------
            if bpJoint.parent:
                
                if bpJoint.info.get('options', {}).get('mirroredSide'):
                    j.setParent( bpJoint.parent.realMirror )
                else:
                    j.setParent( bpJoint.parent.real )
            
            elif bpJoint.extraNode[0]:
                if bpJoint.info.get('options').get('mirroredSide'):
                    j.setParent( bpJoint.extraNode[0].realMirror )
            
            elif bpJoint.postCommand.count('reparent'):
                
                # &&& Need to make the post reparent command thing actually flexible and not a wreck.
                # &&& Also, need to alert if there isn't enough data.
                bpParent = bpJoint.extraNode[0]
                if bpParent:
                    if bpParent.realMirror:
                        j.setParent( bpParent.realMirror )
            else:
                j.setParent( trueRoot )
            
            
            if state in [   BPJoint.Orient.HAS_TARGET,
                            BPJoint.Orient.SINGLE_CHILD,
                            BPJoint.Orient.RELATED_CHILD,
                            BPJoint.Orient.CENTER_CHILD ]:

                lib.anim.orientJoint(j, target, None, aim=aimAxis, up=upAxis, upVector=upVector)
                
            elif state == BPJoint.Orient.AS_PARENT:
                print('Orienting as parent', j)
                joint( j, e=True, oj='none' )
            
            elif state == BPJoint.Orient.WORLD:
                p = j.getParent()
                j.setParent(w=True)
                joint( j, e=True, oj='none' )
                j.setParent(p)
            
            elif state == BPJoint.Orient.FAIL:
                warning('FAIL ' + j.name())
            
            #------ Mirror it -------
            if isMirrored:
                # Behavior mirror
                m = xform(j, q=True, ws=True, m=True)
                m[1] *= -1
                m[2] *= -1
            
                m[1 + 4] *= -1
                m[2 + 4] *= -1
                
                m[1 + 8] *= -1
                m[2 + 8] *= -1
                
                m[12] *= -1
                
                mirrorName = getMirrorName(name)
                
                jo = core.math.eulerFromMatrix(dt.Matrix(m), degrees=True)
                mj = joint(None, n=mirrorName, p=m[12:15], relative=False)
                mj.jointOrient.set(jo)
                
                # Hard link of output joint to blueprint joint to avoid any ambiguity
                core.factory._setSingleConnection(bpJoint, 'realJointMirror', mj)
            
                # Figure out if parent is mirrored to and parent appropriately
                if bpJoint.parent:
                    if bpJoint.parent.realMirror:
                        mj.setParent(bpJoint.parent.realMirror)
                    else:
                        mj.setParent(bpJoint.parent.real)

                
            
    def getUpArrow(self):
        for child in self.listRelatives():
            if child.name().endswith('arrow'):
                return child
            
    def upVector(self, arrow=None):
        '''
        Return the up vector based off of the arrow object, unless an other arrow is given.
        '''
        if not arrow:
            arrow = self.getUpArrow()
            assert arrow, 'Could not find up arrow for {0}'.format( self )
            
        end = dt.Vector(xform(arrow.vtx[61], q=True, ws=True, t=True))
        start = dt.Vector(xform(arrow.vtx[60], q=True, ws=True, t=True))
        return end - start
           
    def getAimAxis(self, suffix=''):
        '''
            Basically returns 'x' if on the left side, or '-x' if on the right.
            
        ..  todo::
            Need to unify where the orientAxis is determined, right now it lives
            here and in orientJoint()
        '''
        _suffix = suffix if suffix else self.suffix.get()
        aim = 'x' if _suffix in ['', 'L'] else '-x'
        if suffix:
            print( "OVERRIDEEN", aim )
        return aim
           
    def addJoint(self, newJoint=None):
        select(cl=True)
        
        if not newJoint:
            newJoint = _createTempJoint()
            
        newJoint.setParent( self, r=True )
        
        self.scale >> newJoint.inverseScale
        newJoint.msg >> self.attr('joints')[self.nextIndex()].jmsg
        
        return newJoint
           
    def nextIndex(self):
        '''
        Handles missing indicies (which might be overkill but better safe than sorry).
        '''
        
        joints = [ a for a in self.attr('joints')]
        
        if not joints:
            return 0
        else:
            return joints[-1].index() + 1
           
    def deleteJoint(self, jnt):
        
        parent = jnt.parent
        children = jnt.proxyChildren
        
        if parent:
            for child in children:
                proxy.pointer(parent, child)
           
        proxyParent = jnt.proxy.getParent()
        for child in jnt.proxy.listRelatives(type='joint'):
            child.setParent(proxyParent)
           
        delete( jnt.proxy )
        delete( jnt )
           
    def insertJoint(self, previousJoint):
        '''
        Insert a joint after the `previous` joint.
        
        ..  todo:: Need to handle sequence vs individual naming.
        '''
        select(cl=True)
        
        newJoint = self.addJoint()
        
        joints = self.joints[:]
        
        previousChildren = previousJoint.proxyChildren
        
        i = joints.index(previousJoint)

        proxy.pointer(previousJoint, newJoint)
        previousJointPos = dt.Vector( xform(previousJoint, q=True, ws=True, t=True) )
        
        # If the final pos isn't at the end, all the connections need shifting.
        if i < len(joints) - 2:
            followingJoint = joints[i + 1]
            insertPoint = joints[i + 1].cardCon
            
            for i, jnt in enumerate( joints[ i + 1:-1 ], i + 1):
                connectAttr( jnt.message, joints[i + 1].cardCon.jmsg, f=True )
            
            newJoint.message >> insertPoint.jmsg
            
            proxy.pointer(newJoint, followingJoint)
            
            # Position the new joint in between
            followingJointPos = dt.Vector( xform(followingJoint, q=True, ws=True, t=True) )
            
            pos = (previousJointPos - followingJointPos) / 2.0 + followingJointPos
        else:
            pos = previousJointPos + dt.Vector( meters(0.1, 0.1, 0.1) )
            
        for child in previousChildren:
            proxy.pointer(newJoint, child)
            
        xform( newJoint, ws=True, t=pos )
        
        self.setTempNames()
        
        return newJoint
    
    def divideJoint(self, previousJoint):
        '''
        Make a joint dividing the given and next joints.
        
        ..  todo::
            Need to actually handle updating names all the way
        '''
        
        nextJoint = previousJoint.proxyChildren[0]
        
        newJoint = self.insertJoint(previousJoint)
        
        info = newJoint.info
        info['twist'] = True
        newJoint.info = info
        
        newJoint.tx.unlock()
        c = pointConstraint(previousJoint, nextJoint, newJoint)
        a, b = c.getWeightAliasList()
        
        a.set(0.5)
        
        core.math.opposite(b) >> a
        
        rig.drive(newJoint, 'weight', b, 0, 1.0)
        
        # Update the names
        
        # Count how many other dividers there are
        dividerCount = 0
        cursor = previousJoint
        while cursor and cursor.info.get('twist'):
            dividerCount += 1
            cursor = cursor.parent
        
        cursor = nextJoint
        while cursor and cursor.info.get('twist'):
            dividerCount += 1
            cursor = cursor.proxyChildren[0]
            

        index = self.joints.index(previousJoint)
        
        head = self.rigData['nameInfo']['head']
        
        newName = head[index] + 'T' + str( dividerCount + 1 )
        newJoint.rename(newName + '_bpj')
        
        if index < len(head):
            head.insert( index, newName )
            rigData = self.rigData
            rigData['nameInfo']['head'] = head
            self.rigData = rigData
        
        return newJoint

           
    def merge(self, other):
        
        for j in other.joints:
            pos = xform(j, q=True, ws=True, t=True)
            self.addJoint(j)
            xform(j, ws=True, t=pos)
            
        srcStart, srcRep, srcEnd = util.parse(self.nameInfo.get())
        addStart, addRep, addEnd = util.parse(other.nameInfo.get())
        
        newStart = []
        newRep = ''
        newEnd = []
        
        if srcRep and addRep:
            # The only real issue is if both have repeating sections so
            # explicitly name the addRep
            count = len(other.joints) - (len(addStart) + len(addEnd))
            addStart += [ addRep + '{0:0>2}'.format(i + 1) for i in range(count) ]
            addRep = ''
        
        if srcRep:
            newStart = srcStart
            newRep = srcRep + '*'
            newEnd = srcEnd + addStart + addEnd
            
        elif addRep:
            newStart = srcStart + srcEnd + addStart
            newRep = addRep + '*'
            newEnd = addEnd
            
        else:
            newStart = srcStart + srcEnd + addStart + addEnd
                
        self.nameInfo.set( '%s %s %s' % (' '.join(newStart), newRep, ' '.join(newEnd)) )
           
    def setTempNames(self):
        '''
        Set the names of the temp joints based on what their output joints will be.
        '''

        """
        # Rename all the joints so when the second renaming occurs, it doesn't increment the name.
        for jnt in self.joints:
            jnt.rename('__placeholder')
        
        for jnt, name in self.getOutputMap(includeHelpers=True, usePrefix=False).items():
            if name[0]:
                jnt.rename(name[0] + '_bpj')
            else:
                # Should they be renamed after their parent?
                if not jnt.name().endswith('_tip'):
                    jnt.rename( simpleName(jnt.parent, '{0}_tip') )
        """
        
        queued = {}
        
        names = iter( itertools.chain(self.nameList(usePrefix=False, mirroredSide=False), itertools.cycle(['NOT_ENOUGH_NAMES'])) )
        
        for jnt in self.joints:
            if not jnt.isHelper:
                targetName = names.next() + '_bpj'
                if simpleName(jnt) != targetName:
                    if cmds.ls(targetName, r=1) and targetName != 'NOT_ENOUGH_NAMES_bpj':
                        jnt.rename('_temp_')
                        queued[jnt] = targetName
                    else:
                        jnt.rename(targetName)
            else:
                jnt.rename('_helper_pbj')
        
        for jnt, targetName in queued.items():
            jnt.rename(targetName)
                
           
    def orientJoints(self):
        '''
        Orient the real joints.  Use the card's arrow as the up vector.
        '''
        
        #axis = self.upVector()
        #upLoc = spaceLocator()
        
        #def moveUpLoc(obj, axis=axis):  # Move the upLoc above the given obj
        #    xform( upLoc, ws=True, t=axis + dt.Vector(xform(obj, q=True, ws=True, t=True)))
        
        #aim = 'x' if self.suffix.get() in ['', 'L'] else '-x'
        
        upAxis = 'y'
        
        for tempJnt in self.joints:
            if not tempJnt.real:
                continue
        
            j = tempJnt.real
            jPos = dt.Vector(xform(j, q=True, ws=True, t=True))
            
            if tempJnt.customOrient:
                matrix = xform(tempJnt.customOrient, q=True, ws=True, m=True)
                xVector = dt.Vector(matrix[0:3])
                yVector = dt.Vector(matrix[4:7])
                #zVector = matrix[8:11]
                
                lib.anim.orientJoint(j, jPos + xVector, jPos + yVector, up=upAxis)
                
            else:
                upVector = self.upVector(tempJnt.customUp) # Uses default if customUp isn't set
                
                state, target = tempJnt.getOrientState()
                
                if state in [   BPJoint.Orient.HAS_TARGET,
                                BPJoint.Orient.SINGLE_CHILD,
                                BPJoint.Orient.RELATED_CHILD,
                                BPJoint.Orient.CENTER_CHILD ]:
                    lib.anim.orientJoint(j, target, aim=self.getAimAxis(tempJnt.suffixOverride), up=upAxis, upVector=upVector)
                    
                elif state == BPJoint.Orient.AS_PARENT:
                    joint( j, e=True, oj='none' )
                
                elif state == BPJoint.Orient.WORLD:
                    p = j.getParent()
                    j.setParent(w=True)
                    joint( j, e=True, oj='none' )
                    j.setParent(p)
                
                elif state == BPJoint.Orient.FAIL:
                    warning('FAIL ' + j.name())
        
    def parentJoints(self):
        
        for j in self.joints:
            if j.parent:
                j.real.setParent( j.parent.real )
        
        '''
        If a card is marked as unbindable, move it to a proxy in the unbindable
        group.
        
        &&& Does this handle mirrored stuff at all?
        
        I don't think it handles freeform (non-linear) at all
        '''
        if self.rigDataQuery('joints', 'unbindable') is True:
            main = space.getMainGroup()

            unbindable = lib.getNodes.childByName(main, 'unbindable')
            if not unbindable:
                unbindable = group(n='unbindable', em=True, p=main)
            
            if self.start().parent:
                parent = self.start().parent.real
                parentName = simpleName(parent) + '_proxy'
            else:
                parent = main
                parentName = 'main_proxy'
            
            proxy = lib.getNodes.childByName(unbindable, parentName)
            if not proxy:
                proxy = group(em=True, n=parentName, p=unbindable)
                
                parentConstraint(parent, proxy, mo=False)
            
            self.start().real.setParent(proxy)

    def removeHelpers(self):
        '''
        Delete joints that are marked as helpers.
        '''
        for j in self.joints:
            if j.isHelper:
                delete( j.real )
                  
    @property
    def parentCard(self):
        # Returns the card that this card's joints are children to.
        
        parent = self.parentCardLink
        
        if parent == 'none':
            return None
        
        elif parent:
            return parent
        
        else:
            for j in self.joints:
                if self.joints[0].parent and self.joints[0].parent.cardCon.node() != self:
                    parent = self.joints[0].parent.cardCon.node()
                    self.parentCardLink = parent
                    return parent
        
        self.parentCardLink = 'none'
        return None

    @property
    def parentCardJoint(self):
        if self.joints[0].parent:
            return self.joints[0].parent
            
        return None
    
    @property
    def parentCardFinal(self):
        '''
        If this card parents to another card (ex, 'future parent mirror of'),
        return that instead of the existing parent, falling back to the regular
        parentCard.
        '''
        
        if self.joints[0]:
            finalParent = getReparentCommand(self.joints[0])
            if finalParent:
                return finalParent.card
        
        return self.parentCard
        
    @property
    def childrenCards(self):
        
        # First use moParentCardLink to determine children.
        subCards = [ n.node() for n in self.message.listConnections(d=True, s=False, p=True) if n.attrName() == 'moParentCardLink']
        
        # If that fails, it means it's an older rig, so we must use the proxy children connections,
        # which fails to deal with parent to mirror.
        if not subCards:
            subCards = []
            for _joint in self.joints:
                for child in _joint.proxyChildren:
                    if child.cardCon.node() != self and child.cardCon.node() not in subCards:
                        subCards.append(child.cardCon.node())
                    
        return sorted(subCards, key=lambda card: card.orderIndex.get() if card.hasAttr('orderIndex') else 0 )
        
    def childrenCardsBySide(self, side):
        '''
        When given a side, exclude children cards that don't build on that side.
        '''
        
        #self.childrenCards
        
        for jnt in self.joints:
            for j in jnt.message.listConnections(type=BPJoint):
                print( getReparentCommand(j), self )
                destParent = getReparentCommand(j)
                if destParent:
                    if destParent.card == self:
                        print( j, 'YYESS' )
        
    @property
    def extraNode(self):
        '''
        Wrapper to create underlying attr `.extraRigNodes` if needed for ease
        of use.
        
        ..  todo::
            * To be actually useful, this needs to be redone as a multi attr,
                [action, nodes, placement] so the action and node stay together,
                and have info on when the action will occur (might not be needed)
        '''
        return NodeListProxy(self)
              
    @property
    def size(self):
        '''
        Returns the width, height of the card.
        '''
        
        # Old way was polygons, new is nurbs but that means handling both
        if self.listRelatives(type='mesh'):
            tl = self.vtx[2]
            br = self.vtx[1]
        else:
            tl = self.cv[0][1]
            br = self.cv[1][0]
        
        topLeft = xform( tl, q=True, os=True, t=True )
        bottomRight = xform( br, q=True, os=True, t=True )
        
        return (topLeft[2] - bottomRight[2]) * self.sx.get(), \
               (topLeft[1] - bottomRight[1]) * self.sy.get()

    def _outputs(self):
        '''
        Generator yeilding the main controller and data about it:
            (RigControl, "<side>", "<type>").
            RigControl is the lead control, allowing access to sub controls
            side is 'Left', 'Right', 'Center'
            type is 'ik', 'fk'
        '''
        for side in ['Left', 'Right', 'Center' ]:
            for type in ['ik', 'fk']:
                node = getattr( getattr( self, 'output' + side ), type)
                if node:
                    yield (node, side, type)
                
    getMainControls = _outputs
    # Much better name
                
    def saveShapes(self):
        '''
        If there is any output, stores the shape info.
        Done as unique attr because I've had trouble in the past with compound
        array attrs with strings.
        '''
        for node, side, type in self._outputs():
            shapeInfo = controller.saveControlShapes(node)
            shapeInfo = core.text.asciiCompress(shapeInfo)
            core.factory._setStringAttr( self, 'outputShape' + side + type, shapeInfo)
                    
    def restoreShapes(self):
        '''
        Apply any shape data saved via saveShapes
        '''
        for node, side, type in self._outputs():
            shapeInfo = core.factory._getStringAttr( self, 'outputShape' + side + type)
            if shapeInfo:
                shapeInfo = core.text.asciiDecompress(shapeInfo)
                controller.loadControlShapes( node, shapeInfo.splitlines() )
        
    def saveSpaces(self):
        self._saveData( self.SPACES_STORAGE, space.serializeSpaces)

        # TEMP CODE, Remove old space storage method when new spaces are saved
        for side in ['Center', 'Left', 'Right']:
            for kinematic in ['ik', 'fk']:
                if self.hasAttr( 'spaces' + side + kinematic ):
                    self.deleteAttr( 'spaces' + side + kinematic )

    def restoreSpaces(self, clearOldSpaces=True):
        
        self.updateStoredData()
        
        def restoreTargets(control, data):
            if clearOldSpaces:
                space.removeAll(control)
    
            space.deserializeSpaces(control, data)
            
        self._restoreData( self.SPACES_STORAGE, restoreTargets )

    def updateStoredData(self):

        # Spaces are now in the much easier json format
        targetInfo = lambda: collections.defaultdict( list )  # noqa e731
        transformedData = collections.defaultdict( targetInfo )
        
        transferringOccurred = False
        for side in ['Center', 'Left', 'Right']:
            for kinematic in ['ik', 'fk']:
                if self.hasAttr( 'spaces' + side + kinematic ):
                    data = self.attr( 'spaces' + side + kinematic ).get()
                    for chunk in data.split('*'):
                        name, parts = chunk.split('=')
                        for spaces in parts.split(';'):
                            parts = spaces.split(',')
                            if len(parts) == 3:
                                transformedData[ side + ' ' + kinematic ][name.strip()].append(
                                    [ parts[0], parts[1], int(parts[2]) ] )
                    self.deleteAttr( 'spaces' + side + kinematic )
                    transferringOccurred = True
                        
        if transferringOccurred:
            core.factory._setStringAttr( self, self.SPACES_STORAGE, json.dumps(transformedData))

    def _saveData(self, attrName, function, returnData=False):
        '''
        Wrapper for storing controller data for all the controls made by this
        card.  Data must be json serializable.
        
        Results in something like:
            self.attrName = {
                '<side> <kinematic type>': {
                    'main': <main data>,
                    'socket': <socket data>,
                }
            }
            
            or, more specifcally
            
            self.MoVisGroup = {
                'Left ik': {
                    'main': 'hands',
                    'socket': 'sockets',
                }
            }
        
        :param string attrName: The name that will be stored on the card
        :param function function:  The function that will be run on each control
            to harvest data in the form of:
            
                def harvest(ctrl):
                    return <json serializable>
        
        '''
        allData = {}
        
        for ctrl, side, type in self._outputs():
            data = {}
            
            obtainedData = function(ctrl)
            if obtainedData:
                data['main'] = obtainedData
            
            for key, subCtrl in ctrl.subControl.items():
                obtainedData = function(subCtrl)
                if obtainedData:
                    data[key] = obtainedData
        
            if data:
                allData[ "%s %s" % (side, type) ] = data
        
        if returnData:
            return allData
        else:
            core.factory._setStringAttr( self, attrName, json.dumps(allData))
        
    def _restoreData(self, attrName, function, info=None):
        '''
        The other side of _saveData, except `function` must be in the form of:
            def applyData(ctrl, data):
                pass
        
        `ctrl` is obviously the rig control.
        `data` is whatever you stored with _saveData.
        
        :param info: Is when you feed it something instead of getting it from an attr

        '''
        if not info:
            info = core.factory._getStringAttr( self, attrName)
            info = json.loads(info)
        
        if not info:
            return
        
        for side_type, value in info.items():
            side, type = side_type.split()
            
            mainCtrl = getattr(getattr(self, 'output' + side), type)
            
            for id, ctrlInfo in value.items():
                if id == 'main':
                    ctrl = mainCtrl
                else:
                    ctrl = mainCtrl.subControl[id]
            
                function(ctrl, ctrlInfo)
        
    def saveCustomAttrs(self):
        self._saveData(self.CUSTOM_ATTR_STORAGE, controller.identifyCustomAttrs)
        
    def restoreCustomAttrs(self):
        self._restoreData(self.CUSTOM_ATTR_STORAGE, controller.restoreAttr)
        
    def removeRig(self):
        # Sometimes deleting the rig flips things out, so try deleting the constraints first
        try:
            for j in self.getRealJoints():
                constraints = listRelatives(j, type='constraint')
                if constraints:
                    delete(constraints)
        except Exception:
            print( traceback.format_exc() )
            print( 'Possibly nothing went wrong deleting the rig on card', self )
        
        for ctrl, side, type in self._outputs():
            delete(ctrl.container)

    def removeBones(self):
        self.removeRig()

        delete(self.getRealJoints())

    thingsToSave = [
        ('visGroup', lib.sharedShape.getVisGroup, lib.sharedShape.connect, 'MoVisGroup'),
        ('connections', getLinks, setLinks, LINK_STORAGE),
        ('setDriven', findSDK, applySDK, SDK_STORAGE),
        ('customAttrs', controller.identifyCustomAttrs, controller.restoreAttr, CUSTOM_ATTR_STORAGE),
        ('spaces', space.serializeSpaces, space.deserializeSpaces, SPACES_STORAGE),
        ('constraints', findConstraints, applyConstraints, None),
        ('lockedAttrs', findLockedAttrs, lockAttrs, None),
    ]
    
    def saveState(self):
        allData = self.rigState

        for niceName, harvestFunc, restoreFunc, attr in self.thingsToSave:
            if attr:
                self._saveData(attr, harvestFunc)
            data = self._saveData(attr, harvestFunc, returnData=True)
            allData[niceName] = data

        self.rigState = allData
        
        rigClass = self.rigCommandClass
        if rigClass:
            rigClass.saveState(self)
        
        self.saveShapes()

    def restoreState(self):
        '''
        Restores everything listed in `thingsToSave`, returning a list of ones that failed.
        '''

        allData = self.rigState
        
        issues = []

        for niceName, harvestFunc, restoreFunc, attr in self.thingsToSave:
            if niceName in allData and allData[niceName]:
                try:
                    self._restoreData(attr, restoreFunc, allData[niceName])
                except Exception:
                    print(traceback.format_exc())
                    issues.append( 'Issues restoring ' + niceName )
                
        rigClass = self.rigCommandClass
        
        if rigClass:
            try:
                rigClass.restoreState(self)
            except Exception:
                issues.append( 'Issues restoring shapes' )
        
        self.restoreShapes()
        
        return issues

    # -----------------

    def saveVisGroups(self):
        self._saveData('MoVisGroup', lib.sharedShape.getVisGroup)
        
    def restoreVisGroups(self):
        self._restoreData('MoVisGroup', lib.sharedShape.connect)

    def saveControlConnections(self):
        self._saveData(self.LINK_STORAGE, getLinks)
        
    def restoreControlConnections(self):
        self._restoreData(self.LINK_STORAGE, setLinks)

    def saveSetDrivenKeys(self):
        self._saveData(self.SDK_STORAGE, findSDK)
    
    def restoreSetDrivenKeys(self):
        self._restoreData(self.SDK_STORAGE, applySDK)

    def getAllControls(self):
        controls = []
        for ctrl, _, _ in self._outputs():
            controls.append( ctrl )
            for name, sub in ctrl.subControl.items():
                controls.append( sub )
        return controls

    def rigDataQuery(self, *path):
        '''
        Takes a json path, searching json for the result, returning it or NOT_FOUND.
        '''
        
        data = self.rigData
        try:
            for p in path:
                data = data[p]
            
            return data
        except Exception:
            return NOT_FOUND


'''
def findConstraints(ctr):
    align = core.dagObj.align(ctrl)

    return {
        'main': core.constraints.aimSerialize(ctrl) if aimConstraint(ctrl, q=True) else None,
        'align': core.constraints.aimSerialize(align) if align and aimConstraint(align, q=True) else None,
    }
'''


class NOT_FOUND:
    pass


def getTrueRoot():
    trueRoot = PyNode('b_root') if objExists( 'b_root' ) else joint(None, n='b_root')
    trueRoot.drawStyle.set(2)
    return trueRoot


def getReparentCommand(tempJoint):
    '''
    Given a `BPJoint`, returns the BPJoint who's mirror output will become
    this joint's parent or None if there isn't one.
    '''
    
    if not tempJoint.postCommand:
        return None
    
    for cmd in tempJoint.postCommand.split(';'):
        cmd = cmd.strip()
        
        if cmd.startswith('reparent'):
            match = re.search('\{extraNode([0-9]*)\}', cmd)
        
            if match:
                index = int(match.group(1))
                if tempJoint.extraNode[index]:
                    return tempJoint.extraNode[index]
    
    return None


class BPJoint(nt.Joint):

    postCommand     = core.factory.StringAccess('postCommand')
    parent          = core.factory.SingleConnectionAccess('parent')
    real            = core.factory.SingleConnectionAccess('realJoint')
    suffixOverride  = core.factory.StringAccess('suffixOverride')
    customUp        = core.factory.SingleConnectionAccess('customUp')
    customOrient    = core.factory.SingleConnectionAccess('moCustomOrient')
    proxy           = core.factory.SingleConnectionAccess('proxy')
    orientTarget    = core.factory.SingleStringConnectionAccess('orientTargetJnt')
    info            = core.factory.JsonAccess('motigaInfo')

    @classmethod
    def _isVirtual(cls, obj, name):
        fn = pymel.api.MFnDependencyNode(obj)
        try:
            if fn.hasAttribute('realJoint'):
                return True
            return False
        except Exception:
            pass
        return False
        
    def _getListConnections(self, attrName):
        '''
        If connected, return the single entry, otherwise none.
        '''
        connections = self.attr(attrName).listConnections()
        if connections:
            return connections
        else:
            return []
        
    @property
    def realMirror(self):
        ''' Returns the actual bone. Done via the `.realJointMirror` connection.'''

        mirror = core.factory._getSingleConnection(self, 'realJointMirror')
        if mirror:
            return mirror
        
        '''
        real = self.real
        if real:
            return getMirror( real.name(), self )
        '''
        
    @property
    def proxyChildren(self):
        return self._getListConnections('children')
        
    @property
    def isHelper(self):
        return self.hasAttr('helper')
        
    @isHelper.setter
    def isHelper(self, val):
        if val:
            if not self.hasAttr('helper'):
                self.addAttr( 'helper', at='bool' )
            self.overrideEnabled.set(True)
            self.overrideColor.set(31)
        else:
            if self.hasAttr('helper'):
                self.helper.delete()
                self.overrideEnabled.set(False)
                
    @property
    def cardCon(self):
        for connection in self.message.listConnections( p=True ):
            if isinstance( connection.node(), Card ) and connection.attrName() == 'jmsg':
                return connection.parent()
    
    @property
    def card(self):
        # Returns the card this belongs to.  If you need source info, use `.cardCon`
        return self.cardCon.node()
                        
    @property
    def extraNode(self):
        '''
        Wrapper to create underlying attr `.extraRigNodes` if needed for ease
        of use.
        '''
        return NodeListProxy(self)
        
    class Orient:
        FAIL = 'FAIL'
        HAS_TARGET = 'HAS_TARGET'
        AS_PARENT = 'AS_PARENT'
        SINGLE_CHILD = 'SINGLE_CHILD'
        CENTER_CHILD = 'CENTER_CHILD'
        RELATED_CHILD = 'RELATED_CHILD'
        WORLD = 'WORLD'
        Result = collections.namedtuple( 'Result', 'status joint' )

    def getOrientStateNEW(self):
        '''
            Future children are not considered for orientation
        '''
        
        '''
        set Machine  Wrist R
        Planter needs 3
        stoneSkin clavs
        Tank issues?

                
        temps = [t for t in ls(type='joint') if isinstance(t, nodeApi.BPJoint) and t.real]

        for t in temps:
            older = t.getOrientState()
            newer = t.getOrientStateNEW()
            try:
                if older[1] == newer[1].real:
                   continue
            except:
                pass
            
            if older[0] == newer[0]:
                continue

            print( t, ' -  ' , older, ' - ', newer )
        '''
        
        _pos = xform(self, q=True, ws=True, t=True)
        
        def tooClose(other):
            return core.math.isClose( _pos, xform(other, q=True, ws=True, t=True))
            
        cardJoints = self.card.joints
        children = self.proxyChildren
        localChildren = [c for c in children if c in cardJoints]
        outerChildren = [c for c in children if c not in localChildren and c.card.rigCommand != 'Group']
        
        target = self.orientTarget
        if target == '-world-':
            return self.Orient.Result( self.Orient.WORLD, None )
        elif target == '-parent-':
            return self.Orient.Result( self.Orient.AS_PARENT, None )
        elif target:
            return self.Orient.Result( self.Orient.HAS_TARGET, target )
                    
        if not children:
            return self.Orient.Result( self.Orient.AS_PARENT, None )
        
        if len(localChildren) == 1:
            if tooClose(localChildren[0]):
                return self.Orient.Result( self.Orient.AS_PARENT, None )
            else:
                return self.Orient.Result( self.Orient.SINGLE_CHILD, localChildren[0] )
        
        if localChildren:
            centered = [c for c in localChildren if abs(xform(c, q=True, ws=True, t=True)[0]) < 0.001]
            
            if len(centered) == 1 and not tooClose(centered[0]):
                return self.Orient.Result( self.Orient.SINGLE_CHILD, centered[0] )
            elif not outerChildren:
                return self.Orient.Result( self.Orient.AS_PARENT, None )
            
        # At this point, no local children were orientable so check the following card(s).
        
        if len(outerChildren) == 1:
            # If I'm not mirrored, but next is, it branches so use parent.
            if not self.card.isCardMirrored() and outerChildren[0].card.isCardMirrored():
                return self.Orient.Result( self.Orient.AS_PARENT, None )
                
            # Both self and child are mirrored, or child is skipped, so use it.
            else:
                if not tooClose(outerChildren[0]):
                    return self.Orient.Result( self.Orient.SINGLE_CHILD, outerChildren[0] )
                else:
                    return self.Orient.Result( self.Orient.AS_PARENT, None )
        
        # There are several outerChildren
        centered = [c for c in outerChildren if abs(xform(c, q=True, ws=True, t=True)[0]) < 0.001]
        
        if len(centered) == 1 and not tooClose(centered[0]):
            return self.Orient.Result( self.Orient.SINGLE_CHILD, centered[0] )
        
        return self.Orient.Result( self.Orient.AS_PARENT, None )

            
        '''
        
        #children = self.real.listRelatives(type='joint')
        children = self.proxyChildren
    
        if self.orientTarget:
            if isinstance(self.orientTarget, basestring):
                if self.orientTarget == '-world-':
                    return self.Orient.Result( self.Orient.WORLD, None )
                elif self.orientTarget == '-parent-':
                    return self.Orient.Result( self.Orient.AS_PARENT, None )
            return self.Orient.Result( self.Orient.HAS_TARGET, self.orientTarget )
        
        if len(children) == 0:
            return self.Orient.Result( self.Orient.AS_PARENT, None )
            
        if len(children) == 1 and \
            (children[0].card.isCardMirrored() == self.card.isCardMirrored()):  # noqa e125
            # I think  this is valid, if they are mirrored from the same base, it's ok
            # or if neither is mirrored, it's ok
            return self.Orient.Result( self.Orient.SINGLE_CHILD, children[0] )

        # We have several children so a few measures can be tried to determine a target.
        localChildren = [child for child in children if child.card == self.card]
        
        # If only one child is in the same card, orient to it.
        if len(localChildren) == 1:
            return self.Orient.Result( self.Orient.RELATED_CHILD, localChildren[0] )
        
        # If this isn't mirrored and all but one child is, orient to it.
        if not self.card.isCardMirrored():
            nonLocalChildren = [child for child in children if child.card != self.card]
            nonMirrored = [child for child in nonLocalChildren if not child.card.isCardMirrored()]
            
            if len(nonMirrored) == 1:
                return self.Orient.Result( self.Orient.CENTER_CHILD, nonMirrored[0] )
        
        return self.Orient.Result( self.Orient.FAIL, None )
        '''
        
    def getOrientState(self):
        '''
        ..  todo::
            This should probably be changed to look at virtual children so a
            card that is a child who's parent mirrors can mirror on it's own.
            
            But this might be too complicated.Orient
            OR future children DO NOT COUNT as orient targets!  JUST MAKE IT INVALID!  Does that sound good?
        '''
        
        children = self.real.listRelatives(type='joint')
    
        # First check if there are explicit orient instructions.
        if self.orientTarget:
            if isinstance(self.orientTarget, basestring):
                if self.orientTarget == '-world-':
                    return self.Orient.Result( self.Orient.WORLD, None )
                elif self.orientTarget == '-parent-':
                    return self.Orient.Result( self.Orient.AS_PARENT, None )
            elif self.orientTarget:
                return self.Orient.Result( self.Orient.HAS_TARGET, self.orientTarget )
        
        # Otherwise try to determine a sensible orientation from the children joints.
        if len(children) == 0:
            return self.Orient.Result( self.Orient.AS_PARENT, None )
            
        elif len(children) == 1:
            # If the child is on top of the joint, orient as the parent
            if core.math.isClose( xform(self, q=True, ws=True, t=True), xform(children[0], q=True, ws=True, t=True)):
                return self.Orient.Result( self.Orient.AS_PARENT, None )
            else:
                return self.Orient.Result( self.Orient.SINGLE_CHILD, children[0] )
            
        else:
            # Since we have multiple children, see if only one is in the center.
            # THis centers stuff looks like garbage, and is because helper joints ruin it...
            
            centers = []
            for child in children:
                if abs(xform(child, q=True, ws=True, t=True)[0]) < 0.001:
                    centers.append(child)

            if len(centers) == 1:
                return self.Orient.Result( self.Orient.CENTER_CHILD, centers[0] )
                
            else:
                related = []
                for temp in self.cardCon.node().joints:
                    related.append( temp.real )
                related.remove( self.real )
                
                relatedChildren = []
                for j in related:
                    if j in children:
                        relatedChildren.append(j)
                
                if len(relatedChildren) == 1:
                    return self.Orient.Result( self.Orient.RELATED_CHILD, relatedChildren[0] )
                else:
                    return self.Orient.Result( self.Orient.FAIL, None )
    
    def addRealExtra(self, joint):
        indicies = self.realJointExtra.getArrayIndices()
        if len(indicies) == indicies[-1] + 1:
            joint.msg >> self.realJointExtra[indicies[-1] + 1]
        else:
            for i in range( indicies[-1] + 1 ):
                if i not in indicies:
                    joint.msg >> self.realJointExtra[i]
                    break
    
    def setBPParent(self, parent):
        
        # Freeform and Squash allows non-linear parenting, but everything else must be kept linear.
        if self.card.rigCommand not in ('Freeform', 'SquashStretch'):
            if parent is None:
                if self.parent and self.parent.card != self.card:
                    self.card.parentCardLink = None
                    
                proxy.unpoint(self)
                return
            
            if self.card != parent.card:
                # Make sure sibling joints don't have a unique parent
                # set parent card attribute
                
                for sibling in self.card.joints:
                    if sibling == self:
                        continue
                    
                    # If sibling already has an external parent, exit.
                    if sibling.parent.card != self.card:
                        return
                
                self.card.parentCardLink = parent.card
            else:
                # Make sure it's not a cycle
                pass
        else:
            if self.card.parentCardLink != parent.card:
                self.card.parentCardLink = parent.card
            
        # point them
        proxy.pointer(parent, self)


def findSimilarOutput(side, otherCard, fallbackDirection):
    '''
    Looks for a RigController on the otherCard (and in the fallbackDirection)
    on the matching side, if possible.
    
    :param PyNode control: RigController or SubController
    :param PyNode otherCard: Card
    :param str fallbackDirection: 'up' or 'down' or None to search only the given card
    '''

    #main = getMainController(control)
    #side = main._outputAttr().side
    if otherCard.getSide(side):
        return rig._getActiveControl(otherCard.getSide(side))
    else:
        # If we have a situation where a non-mirrored obj has a mirrored parent,
        # try the default output first
        side = {'R': 'Right', 'L': 'Left', '': 'Center'}[ otherCard.findSuffix() ]
        if otherCard.getSide(side):
            return rig._getActiveControl(otherCard.getSide(side))
            
    # If we didn't find anything, then only one of these will return something valid, if at all
    if otherCard.outputLeft:
        return rig._getActiveControl(otherCard.outputLeft)
    if otherCard.outputRight:
        return rig._getActiveControl(otherCard.outputRight)
    if otherCard.outputCenter:
        return rig._getActiveControl(otherCard.outputCenter)
                    
    # If we made it here, the parent card had no control, so search the next level
    if fallbackDirection == 'up':
        if otherCard.parentCardFinal:
            if otherCard.parentCardFinal == otherCard.parentCard:
                return findSimilarOutput(side, otherCard.parentCardFinal, 'up')
            else:
                # Swap sides since future parent is being used
                side = 'Left' if otherCard.parentCardFinal.findSuffix() == 'R' else 'Right'
                return findSimilarOutput(side, otherCard.parentCardFinal, 'up')
            
    elif fallbackDirection == 'down':
        for child in otherCard.childrenCards:
            ctrl = findSimilarOutput(side, child, None)
            if ctrl:
                return ctrl
        
        for child in otherCard.childrenCards:
            ctrl = findSimilarOutput(side, child, 'down')
            if ctrl:
                return ctrl
        
    return None


class RigController(nt.Transform):

    @staticmethod
    def convert(mainControl):
        '''
        Adds special attributes to link the given control with other controls.
        Usage::
            ctrl = RigController.convert(ctrl)
            ctrl.subControl['pv'] = poleVectorCtrl
            ctrl.subDControl['socket'] = socketCtrl
        '''
        
        if not mainControl.hasAttr('controlLinks'):
            mobj = core.capi.asMObject(mainControl)
            cattr = OpenMaya.MFnCompoundAttribute()
            tattr = OpenMaya.MFnTypedAttribute()
            mattr = OpenMaya.MFnMessageAttribute()

            links = cattr.create("controlLinks", 'clnks')
            cattr.array = True

            name = tattr.create('controlName', 'nam', OpenMaya.MFnStringData.kString)
            link = mattr.create('controlLink', 'clk')

            cattr.addChild(name)
            cattr.addChild(link)
            
            mobj.addAttribute(links)
            
        # Return casted to have new api
        return PyNode(mainControl)

    @classmethod
    def _isVirtual(cls, obj, name):
        fn = pymel.api.MFnDependencyNode(obj)
        try:
            if fn.hasAttribute('controlLinks'):
                return True
        except Exception:  # .hasAttribute doesn't actually return False but errors, lame.
            pass
        return False

    @property
    def container(self):
        try:
            return self.containerLink.listConnections()[0]
        except Exception:
            return None
    
    @container.setter
    def container(self, container):
        if not self.hasAttr('containerLink'):
            self.addAttr( 'containerLink', at='message' )
            
        if container:
            container.message >> self.containerLink
        else:
            self.containerLink.disconnect()
    
    def setGroup(self, visGroupName):
        self.container.setParent( rig.getControlGroup(visGroupName) )
    
    def _outputAttr(self):
        '''
        Returns the plug that connects this to it's card, ex 'card.outputLeft.ik'
        '''
        for temp in self.message.listConnections(p=True):
            if isinstance(temp.node(), Card):
                cardPlug = temp
                break
        else:
            # Unable to determine card, should I verify this isn't a subcontrol?
            return None
        
        outputList = cardPlug.parent().array()
        side = outputList.name().rsplit('.')[-1][len('output'):]

        outputAttr = getattr(cardPlug.node(), 'output' + side)
        return outputAttr
                
    def getSide(self):
        outLink = self.message.listConnections(p=True, type=Card)[0]
        side = outLink.attrName(longName=True)[ len('outputLink'): ]
        return side
                
    def getOtherMotionType(self):
        '''
        If this is FK, returns Ik and vise-versa
        '''
        
        outputAttr = self._outputAttr()
        
        if self == getattr(outputAttr, 'ik'):
            return getattr(outputAttr, 'fk')
        else:
            return getattr(outputAttr, 'ik')
        
    def getMotionType(self):
        outputAttr = self._outputAttr()
        
        if self == getattr(outputAttr, 'ik'):
            return outputAttr.plug.name().split('.')[-1] + '.ik'
        else:
            return outputAttr.plug.name().split('.')[-1] + '.fk'
        
    def getCreateFunction(self):
        outputAttr = self._outputAttr()
        rigClass = self.card.rigCommandClass
        
        if self == getattr(outputAttr, 'ik'):
            return rigClass.ik
        else:
            return rigClass.fk
        
    @property
    def subControl(self):
        return self.Link(self)
        
    @property
    def card(self):
        # Return the card that created this control
        card = self.message.listConnections(type=Card)
        return card[0] if card else None

    def getOppositeSide(self):
        '''
        Returns the control on the other side if it exists, or None.
        '''
        card = self.card
        if not card:  # &&& Should this return something special on failure?
            return None

        if self == card.outputLeft.ik:
            return card.outputRight.ik
        elif self == card.outputRight.ik:
            return card.outputLeft.ik
            
        elif self == card.outputLeft.fk:
            return card.outputRight.fk
        elif self == card.outputRight.fk:
            return card.outputLeft.fk

    class Link(object):
        def __init__(self, src):
            self.src = src
            
        def __repr__(self):
            controls = collections.OrderedDict()
            for link in self.src.controlLinks:
                key = link.controlName.get()
                con = link.controlLink.listConnections()
                if con:
                    con = con[0]
                else:
                    con = None
                controls[key] = con
            return str(controls)
            
        def items(self):
            '''
            Like a regular dict.items() but only returns non-empty slots.
            '''
            controls = collections.OrderedDict()
            for link in self.src.controlLinks:
                key = link.controlName.get()
                con = link.controlLink.listConnections()
                if con:
                    controls[key] = con[0]
                
            return controls.items()
        
        def next(self, current):
            '''
            '''
            
            controls = [ctrl for k, ctrl in self.items()]
            
            if current == self.src:
                if controls:
                    return controls[0]

            # Check if there are no sub controls, or we're at the end
            if not controls or current == controls[-1]:
                
                children = self.src.card.childrenCards
                if children:
                    # Hop to the start of the first child card
                    for child in children:
                        side = rig.getMainController(current)._outputAttr().side
                        nextCtrl = findSimilarOutput(side, children[0], 'down')
                        if nextCtrl:
                            return nextCtrl
                            
                    # Getting here means no child card had output, so search the nextLevel
                else:
                    return current
            
            for i, ctrl in enumerate(controls):
                if ctrl == current:
                    return controls[i + 1]
            
        def prev(self, current):
            controls = [ctrl for k, ctrl in self.items()]
            
            if current == self.src:
                
                # &&& DO I need to see if the "Final" ness was used and then use it's side instead?  I think so....
                parentCardFinal = self.src.card.parentCardFinal
                
                if parentCardFinal:
                    side = rig.getMainController(current)._outputAttr().side
                    # Handle swapping side if future reparent is used
                    # DOES NOT WORK
                    #if parentCardFinal != self.src.card.parentCard:
                    #   # &&& I feel like there should be some configurable mapping somewhere for suffis stuff.
                    #    side = parentCardFinal.findSuffix()
                    #    side = 'Right' if side == 'L' else 'Left'
                        
                    parentCardMainCtrl = findSimilarOutput(side, self.src.card.parentCardFinal, 'up')
                    
                    if parentCardMainCtrl:
                        subControls = parentCardMainCtrl.subControl.items()
                        if subControls:
                            return subControls[-1][1]
                        else:
                            return parentCardMainCtrl
                    # A parent with output was not found, so leave the selection
                    return current
                    
                # &&& go to root node if possible?
                else:
                    return current
            
            if current == controls[0]:
                return self.src
            
            for i, ctrl in enumerate(controls):
                if ctrl == current:
                    return controls[i - 1]
                            
        def __contains__(self, key):
            try:
                self[key]
                return True
            except KeyError:
                return False
        
        def __getitem__(self, key):
            for link in self.src.controlLinks:
                if link.controlName.get() == key:
                    con = link.controlLink.listConnections()
                    if con:
                        return con[0]
                    return None
                    
            raise KeyError( '{0} does not have controlLink {1}'.format( self.src, key ) )
    
        def __setitem__(self, name, subControl):
            for link in self.src.controlLinks:
                if link.controlName.get() == name:
                    subControl.message >> link.controlLink
                    break
            else:
                i = self.src.controlLinks.numElements()
                self.src.controlLinks[i].controlName.set(name)
                subControl.message >> self.src.controlLinks[i].controlLink

    def cardPath(self):
        return _cardPath(self)


class SubController(nt.Transform):
    
    @classmethod
    def _isVirtual(cls, obj, name):
        # Returns True if it's message is connected to a .controlLink ()
        
        if name:  # Not sure why, but sometimes this is called without an name.
            obj = core.capi.asMObject(name)
            
            msgplug = obj.findPlug('message', False)

            for con in msgplug.connectedTo(False, True):
                if con.name().endswith('controlLink'):
                    return True
        
        return False

    def ownerInfo(self):
        '''
        Returns the node that has this as a sub control and the key to access it.
        '''
        
        obj = core.capi.asMObject(self)
        
        msgplug = obj.findPlug('message', False)

        for con in msgplug.connectedTo(False, True):
            if con.name().endswith('controlLink'):
                #node, plug = con.name().split('.', 1)
                
                # Can't remember why I did this but is seems fine.
                plug = con.partialName( useFullAttributePath=True, useLongNames=True)
                node = OpenMaya.MFnDagNode( con.node() ).fullPathName()

                return PyNode(node), getAttr( (node + '.' + plug)[:-11] + 'controlName' )
    
    def cardPath(self):
        return _cardPath(self)
            

def _cardPath(ctrl):
    '''
    Given a control, returns the string of plugs from the card that results in
    this control, ex: Elbow_L_Ctrl -> Bicep_Card.outputLeft.fk.subControl['1']
    '''
    cmd = ''
    
    if isinstance(ctrl, SubController):
        rigCtrl, key = ctrl.ownerInfo()
        cmd = ".subControl['{0}']".format(key)
    else:
        rigCtrl = ctrl
    
    cardName = "'%s'" % rigCtrl.card.name()
    data = rigCtrl.card.rigData
    if 'id' in data:
        cardName += ", cardId='%s'" % data['id']
    
    cmd = "FIND(%s)" % cardName + '.' + rigCtrl.getMotionType() + cmd
    
    return cmd


registerNodeType( SubController )
registerNodeType( RigController )
registerNodeType( Card )
registerNodeType( BPJoint )

#nodeTypes.BPJoint = TempJoint
#nodeTypes.Card = CardNode
#nodeTypes.SubController = SubController
#nodeTypes.RigController = RigController


def getMirrorNameFunction(card):
    if card.suffix.get() == 'L':
        return lambda x: re.sub('_L$', '_R', x)
    elif card.suffix.get() == 'R':
        return lambda x: re.sub('_R$', '_L', x)
        
    else:
        return lambda x: x