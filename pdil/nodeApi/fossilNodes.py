'''
Definitions of custom PyMel node types.
'''
from __future__ import print_function, absolute_import

import collections
import itertools
import logging
import math
import re
import traceback

from maya.api import OpenMaya

import pymel.api
from pymel.core import cmds, objExists, PyNode, ls, nt, listRelatives, joint, hasAttr, removeMultiInstance, \
    xform, delete, warning, dt, connectAttr, pointConstraint, getAttr, scaleConstraint, orientConstraint

import pdil

from ..tool.fossil import cardRigging
from ..tool.fossil import enums
from ..tool.fossil import rig
from ..tool.fossil import node
from ..tool.fossil import log
from ..tool.fossil._core import ids
from ..tool.fossil._core import config
from ..tool.fossil._core import exceptions
from ..tool.fossil._lib import misc
from ..tool.fossil._lib import proxyskel
from ..tool.fossil._lib import visNode
from ..tool.fossil._lib import space
from ..tool.fossil._lib2 import controllerShape

from ..tool.fossil import util



from . import registerNodeType

try:
    basestring
except NameError:
    basestring = str


def findConstraints(ctrl):
    ''' Returns dict { 'ctrl': <fullSerialize>, 'align': <fullSerialize> }
    '''
    
    align = pdil.dagObj.align(ctrl)
    
    ctrlConstraints = pdil.constraints.fullSerialize(ctrl, nodeConv=ids.getIdSpec)
    alignConstraints = pdil.constraints.fullSerialize(align, nodeConv=ids.getIdSpec) if align else {}
    
    return { 'ctrl': ctrlConstraints, 'align': alignConstraints }


def applyConstraints(ctrl, data):
    ''' Reverse of `findConstraints`
    '''

    align = pdil.dagObj.align(ctrl)

    if data['ctrl']:
        pdil.constraints.fullDeserialize(ctrl, data['ctrl'], nodeDeconv=ids.readIdSpec)
    
    if data['align']:
        pdil.constraints.fullDeserialize(align, data['align'], nodeDeconv=ids.readIdSpec)


def findSDK(ctrl):
    align = pdil.dagObj.align(ctrl)
    
    data = {
        'main': misc.findSDK(ctrl),
        'align': misc.findSDK(align) if align else []
    }
    
    if data['main'] or data['align']:
        return data
    else:
        return {}


def restoreCustomAttr(*args, **kwargs):
    ''' Restore attr wrapper to also try to reapply previously failed set driven keys.
    '''
    
    controllerShape.restoreAttr(*args, **kwargs)
    misc.retrySDK()


def applySDK(ctrl, info):
    misc.applySDK(ctrl, info['main'])
    misc.applySDK(pdil.dagObj.align(ctrl), info['align'])
    

def getLinks(ctrl):
    links = []
    for attr in ctrl.listAttr(k=True) + [ctrl.t, ctrl.r, ctrl.s]:
        cons = attr.listConnections(s=True, d=False, p=True, type='transform')
        if cons:
            links.append( [cons[0].name(), attr.attrName()] )
    
    return links


def getLinksScaleOnly(ctrl):
    ''' Returns [ (targetPlug, 'sx') .. ] for each connected channel. Excludes scaleConstraints.
    '''
    links = []
    for attr in [ctrl.s, ctrl.sx, ctrl.sy, ctrl.sz]:
        cons = attr.listConnections(s=True, d=False, p=True, type='transform')
        if cons and not cons[0].node().type() == 'scaleConstraint':
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

    mobj = pdil.capi.asMObject(obj)
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
                        if pdil.shortName(child) == pdil.shortName(m):
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
    
    newJoint = joint(None)
    newJoint.tx.lock()
    
    newJoint.addAttr( 'parent', at='message' )
    newJoint.addAttr( 'children', at='message' )
    newJoint.addAttr( 'realJoint', at='message' )
    
    mObj = pdil.capi.asMObject(newJoint)
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


card_log = logging.getLogger('fossil.CardNode')
joint_build_log = logging.getLogger(__name__ + '.buildJoints')


def getRJoint(bpj):
    '''
    Get Repositioned joint from blueprint joint

    &&& How to I have just one version instead of another in tpose.py?
    '''
    for plug in bpj.message.listConnections(s=False, d=True, p=True):
        if plug.attrName() == 'bpj':
            return plug.node()


class JointMode:
    default = 0
    tpose = 1
    bind = 2



class Card(nt.Transform):
    
    version = 1
    
    parentCardLink = pdil.factory.SingleStringConnectionAccess('moParentCardLink')
        
    @classmethod
    def _isVirtual(cls, obj, name):
        fn = pymel.api.MFnDependencyNode(obj)
        try:
            if fn.hasAttribute('fossilRigData'):
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
    
    ikControllerOptions = pdil.factory.StringAccess('ikControllerOptions')
    fkControllerOptions = pdil.factory.StringAccess('fkControllerOptions')
    
    rigData             = pdil.factory.JsonAccess('fossilRigData', {'version': 1})  # This replaces NameInfo, Suffix, RigCmd,
    rigState            = pdil.factory.JsonAccess('fossilRigState')  # Storage for all rig modifications like shapes, spaces and vis groups
    
    # Need to update these with direct references to rigData[*]
    
    # !*suffix -> mirrorCode*!
    suffix              = pdil.factory.DeprecatedAttr( lambda obj: obj.rigData.get('mirrorCode'), deprecatedSuffixSetter)
    nameInfo            = pdil.factory.DeprecatedAttr( deprecated_nameInfo_get, deprecated_nameInfo_set )
        
    # This actually only does ik params.  Probably should be renamed to reflect this.
    rigParams = pdil.factory.StringAccess('rigParameters')
            
    '''
    DEPRECATED, the lead controller's vis dictates groups (is this still deprecated or did I resurrect it?)
    
    Rig parts are organized by rigGroupName, falling back to the main
    control's visGroup, if it exists.  Otherwise the pieces are put as a
    child of main.  Use `getGroupName()` which has this logic.
    '''
    rigGroupName = pdil.factory.StringAccess('groupName')
        
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
        '''
        &&& I think I can just do self.attr('joints').listConnections(),
        it's 3x faster than this.
        '''
        joints = []
        for j in self.attr('joints'):
            connected = j.jmsg.listConnections()
            if connected:
                joints.append(connected[0])
                
        return joints
        
    @property
    def rigCommandClass(self):
        try:
            return cardRigging.registeredControls[self.rigData.get(enums.RigData.rigCmd)]
        except Exception:
            return None
        
    @property
    def buildIk(self):
        return not pdil.factory.getStringAttr( self, 'metaControl' ).count( 'skipIk;' )
        
    @buildIk.setter
    def buildIk(self, val):
        if val:
            if not self.buildIk:
                pdil.factory.setStringAttr( self, 'metaControl', pdil.factory.getStringAttr( self, 'metaControl' ).replace('skipIk;', ''))
        else:
            if self.buildIk:
                pdil.factory.setStringAttr( self, 'metaControl', pdil.factory.getStringAttr( self, 'metaControl' ) + 'skipIk;')

    @property
    def buildFk(self):
        return not pdil.factory.getStringAttr( self, 'metaControl' ).count( 'skipFk;' )
        
    @buildFk.setter
    def buildFk(self, val):
        if val:
            if not self.buildFk:
                pdil.factory.setStringAttr( self, 'metaControl', pdil.factory.getStringAttr( self, 'metaControl' ).replace('skipFk;', ''))
        else:
            if self.buildFk:
                pdil.factory.setStringAttr( self, 'metaControl', pdil.factory.getStringAttr( self, 'metaControl' ) + 'skipFk;')
                
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
            val = pdil.factory.getStringAttr(self, 'mirrorSubst')
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
                pdil.factory.setStringAttr(self, 'mirrorSubst', '')
            elif s is False:
                pdil.factory.setStringAttr(self, 'mirrorSubst', 'DO_NOT_MIRROR')
            elif s == 'twin':
                pdil.factory.setStringAttr(self, 'mirrorSubst', 'twin')
            else:
                pdil.factory.setStringAttr(self, 'mirrorSubst', s)
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
        
    def nameList(self, usePrefix=True, mirroredSide=False, excludeSide=False):
        '''
        Returns a list of names for the joints that will be made, helpers are skipped.
        New version with definable repeating areas.
        '''
        
        mirrorCode = self.rigData.get('mirrorCode', '')
        #card_log.debug('{} mirror code, via rigData is {}'.format(self, mirrorCode))
        
        # Inherit the suffix from the mirrored card if no suffix was provided
        if not mirrorCode:
            mirrorSrc = self.isCardMirrored()
            if mirrorSrc:
                mirrorCode = mirrorSrc.rigData.get('mirrorCode', '')
                #card_log.debug('Mirror inherited on {} = {}'.format(self, mirrorCode))
        
        if mirrorCode and not excludeSide:
            if mirroredSide:
                suffix = config.jointSideSuffix( config.otherSideCode(mirrorCode) )
            else:
                suffix = config.jointSideSuffix( mirrorCode )
        else:
            suffix = ''
        
        
        #prefix = config.prefix if usePrefix else ''
        prefix = config._settings['joint_prefix'] if usePrefix else ''
        
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
                
                startNumResult = re.search( r'\d+$', repeat )
                if startNumResult:
                    startNum = int(startNumResult.group())
                    repeat = repeat[ : -len(startNumResult.group()) ] # Trim off the number since it's used to denote start num
                else:
                    startNum = 1
                sequentialNames = [ repeat + '{0:0>2}'.format(i) for i in range(startNum, startNum + repeatCount) ]

                
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
                output[j] = [next(names)]
                
        if self.isCardMirrored():
            
            [ output[j].append(name) for j, name in zip(self.joints, self.nameList(usePrefix=usePrefix, mirroredSide=True) ) if not j.isHelper ]
        
        return output
        
    
    def getRealJoints(self, side=None):
        ''' Returns a list of real joints, optionally taking 'left', 'right' or 'center'.
        
        ..  todo:: This fails on weapons generally, which have a 'mirror by name'
                so both cards report having the joint.

                I might have to do a complex check on sided-ness and mirroring
                to determine the truth.
        '''
        assert side in (None, 'left', 'right', 'center')
        
        sideName = self.findSuffix()
        if not sideName:
            primarySide = 'center'
            otherSide = ''
        else:
            #primarySide = config.letterToWord[suffix]
            primarySide = sideName
            otherSide = config.otherSideCode(primarySide)

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
        ''' A wrapper for getattr(self, side), expects 'left', 'right' and 'center'
        '''
        return getattr(self, 'output' + side.title())

    def getLeadControl(self, side, kinematic):
        '''
        Helper to make it easier to procedurally go through output controls.
        '''

        return getattr(self.getSide(side), kinematic)
        
    def hasBuiltJoints(self):
        for j in self.joints:
            if not j.isHelper and j.real:
                return True
        
        return False
        
            
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
            
    
    def buildJoints_core(self, mode):
        '''
        Creates, parents and orients the joints of a card.
        
        ..  todo::
            Need to deal with unbuild parents (for regular and mirrored joints)
                and post command parenting.
            Additionally, freeform joints could pose a problem.  I might want
                to bulid all joints then parent as a separate loop
        '''
        
        if self.rigData.get( 'rigCmd' ) in HELPER_CARDS:
            return
        
        if mode != JointMode.bind:
            self.removeBones()
        
        trueRoot = getTrueRoot()

        pdil.layer.putInLayer(trueRoot, 'Joints')
        trueRoot.drawStyle.set(2)
                
        data = self.rigData
        checkOffcenter = True
        if 'log ignores' in data:
            if 'Centerline' in data['log ignores']:
                checkOffcenter = False
        
        names = self.nameList()
        
        jointsThatBuild = [j for j in self.joints if not j.isHelper]
        
        if mode == JointMode.tpose:
            positions = [xform(getRJoint(j), q=True, ws=True, t=True) for j in jointsThatBuild]
        else:
            positions = [xform(j, q=True, ws=True, t=True) for j in jointsThatBuild]

        if len(names) < len(jointsThatBuild):
            raise Exception( 'Not enough names specified to build joints on {0}'.format(self) )
        
        isMirrored = self.isCardMirrored()
        card_log.debug( '{} is mirrored'.format(isMirrored) )
        
        outputJoints = []
        
        # If not mirrored, mirrorName is just ignored in the loop body.
        for name, jpos, bpJoint, mirrorName in zip( names, positions, jointsThatBuild, self.nameList(mirroredSide=True)):
            # Make the joint
            name = name if mode != JointMode.bind else name + '_tempAlign'
            j = joint(None,
                      n=name,
                      p=jpos,
                      relative=False)
            outputJoints.append(j)
            
            if mode != JointMode.bind:
                j.msg >> bpJoint.realJoint
            else:
                pdil.factory.setSingleConnection(bpJoint, 'bind', j)


            if checkOffcenter:
                log.Centerline.check(j)
            
            #------ Orient it -------
            state, target = bpJoint.getOrientState()

            upAxis = 'y'
            aimAxis = self.getAimAxis(bpJoint.suffixOverride)
            
            upVector = self.upVector(bpJoint.customUp)  # If not custom, will default to card's up arrow
                                            
            #print( bpJoint, state, target )
                        
            #------- Parent it (so orient as parent works) -------
            # probably move into a function?
            
            if mode == JointMode.bind:
                def redirect(node):
                    cons = node.message.listConnections(p=True, s=False, d=True)
                    for con in cons:
                        if isinstance(con.node(), BPJoint):
                            if con.attrName() == 'realJointMirror':
                                return con.node().bindMirror.listConnections()[0]
                            else:
                                return con.node().bind.listConnections()[0]

                            #subCons = con.node().message.listConnections(p=True, s=False, d=True)
                            #for subCon in subCons:
                            #    if subCons.attrName() == 'bpj':
                            #        return subCon.node()
                    
                    return node
            else:
                def redirect(node):
                    return node
            
            if bpJoint.parent:
                
                # ! CRITICAL ! Changes to this logic need to be reflected in tpose.reposerToBind
                if bpJoint.info.get('options', {}).get('mirroredSide'):
                    j.setParent( redirect(bpJoint.parent.realMirror) )
                else:
                    j.setParent( redirect(bpJoint.parent.real) )
            
            elif bpJoint.extraNode[0]:
                if bpJoint.info.get('options').get('mirroredSide'):
                    j.setParent( redirect(bpJoint.extraNode[0].realMirror) )
            
            elif bpJoint.postCommand.count('reparent'):
                
                # &&& Need to make the post reparent command thing actually flexible and not a wreck.
                # &&& Also, need to alert if there isn't enough data.
                bpParent = bpJoint.extraNode[0]
                if bpParent:
                    if bpParent.realMirror:
                        j.setParent( redirect(bpParent.realMirror) )
            else:
                j.setParent( redirect(trueRoot) )
            
            
            if state in [   BPJoint.Orient.HAS_TARGET,
                            BPJoint.Orient.SINGLE_CHILD,
                            BPJoint.Orient.RELATED_CHILD,
                            BPJoint.Orient.CENTER_CHILD ]:

                pdil.anim.orientJoint(j, target, None, aim=aimAxis, up=upAxis, upVector=upVector)
                
            elif state == BPJoint.Orient.AS_PARENT:
                #print('Orienting as parent', j)
                joint( j, e=True, oj='none' )
            
            elif state == BPJoint.Orient.WORLD:
                p = j.getParent()
                j.setParent(w=True)
                joint( j, e=True, oj='none' )
                j.setParent(p)
            
            elif state == BPJoint.Orient.CUSTOM:
                
                matrix = dt.Matrix( xform(target, q=True, ws=True, m=True) )
                
                targetPos = bpJoint.getTranslation(space='world') - dt.Vector( matrix[0][:3] )
                upVector = dt.Vector( matrix[1][:3] )
                
                pdil.anim.orientJoint(j, targetPos, None, aim=aimAxis, up=upAxis, upVector=upVector)
            
            elif state == BPJoint.Orient.FAIL:
                warning('FAIL ' + j.name())
            
            #------ Mirror it -------
            if isMirrored:
                # Behavior mirror
                m = xform(j, q=True, ws=True, m=True)
                
                
                if self.mirror == 'twin':
                    """
                    forward = dt.Vector(0, 0, 1)
                    backward = dt.Vector(0, 0, -1)
                    
                    x = dt.Vector( m[0:3] )
                    y = dt.Vector( m[0 + 4:3 + 4] )
                    z = dt.Vector( m[0 + 8:3 + 8] )
                    
                    shortAngle = forward.angle(x)
                    shortAxis = 'x'
                    direction = forward
                    
                    for d in [forward, backward]:
                        for axis in [x, y, z]:
                            angle = d.angle(axis)
                            if angle < shortAngle:
                                shortAngle = angle
                                shortAxis = axis
                                direction = d
                    
                    yPlaneProjection = dt.Vector( shortAxis.x, 0, shortAxis.z )
                    quat = yPlaneProjection.rotateTo(direction)
                    
                    x0 = x.rotateBy(quat).rotateBy(quat)
                    y0 = y.rotateBy(quat).rotateBy(quat)
                    z0 = z.rotateBy(quat).rotateBy(quat)
                    
                    m[0:3] = list(x0)
                    m[0 + 4:3 + 4] = list(y0)
                    m[0 + 8:3 + 8] = list(z0)
                    
                    # Find which base is facing forward and up
                    # Find how off rotated it is from forward
                    # Rotate the matrix in the other direction
                    """
                    
                    m[1] *= -1
                    m[2] *= -1
                
                    m[1 + 4] *= -1
                    m[2 + 4] *= -1
                    
                    m[1 + 8] *= -1
                    m[2 + 8] *= -1
                    
                    x = dt.Vector( m[0:3] )
                    y = dt.Vector( m[0 + 4:3 + 4] )
                    z = dt.Vector( m[0 + 8:3 + 8] )
                    
                    #lateral = dt.Vector(m[4:7])
                    lateral = dt.Vector(m[0:3])
                    lateral.normalize()
                    quat = dt.Quaternion( math.pi, lateral )
                    
                    m[0:3] = list( x.rotateBy(quat) )
                    m[0 + 4:3 + 4] = list( y.rotateBy(quat) )
                    m[0 + 8:3 + 8] = list( z.rotateBy(quat) )
                else:
                    # Flip y,z on each axis
                    m[1] *= -1
                    m[2] *= -1
                
                    m[1 + 4] *= -1
                    m[2 + 4] *= -1
                    
                    m[1 + 8] *= -1
                    m[2 + 8] *= -1
                
                m[12] *= -1 # Flip X
                
                jo = pdil.math.eulerFromMatrix(dt.Matrix(m), degrees=True)
                pos = j.getTranslation(space='world')
                pos.x *= -1

                mirrorName = mirrorName if mode != JointMode.bind else mirrorName + '_tempAlign'

                mj = joint(None, n=mirrorName, p=pos, relative=False)
                outputJoints.append(mj)
                mj.jointOrient.set(jo)
                
                # Hard link of output joint to blueprint joint to avoid any ambiguity
                if mode != JointMode.bind:
                    pdil.factory.setSingleConnection(bpJoint, 'realJointMirror', mj)
                else:
                    pdil.factory.setSingleConnection(bpJoint, 'bindMirror', mj)
            
                # Figure out if parent is mirrored to and parent appropriately
                if bpJoint.parent:
                    if bpJoint.parent.realMirror:
                        mj.setParent( redirect( bpJoint.parent.realMirror) )
                    else:
                        mj.setParent( redirect( bpJoint.parent.real) )
                else:
                    mj.setParent(trueRoot)
        
        return outputJoints
                
            
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
            print( "OVERRIDEN", aim )
        return aim
           
    def addJoint(self, newJoint=None):
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
                proxyskel.pointer(parent, child)
           
        proxyParent = jnt.proxy.getParent()
        for child in jnt.proxy.listRelatives(type='joint'):
            child.setParent(proxyParent)
           
        delete( jnt.proxy )
        delete( jnt )
        
        # &&& THis needs to clean up the list order too via jnt.cardCon
        
    def insertParent(self, targetJoint):
        ''' Insert a parent to the given targetJoint.
        '''
        joints = self.joints[:]
        newJoint = self.addJoint()
        
        parentIndex = joints.index(targetJoint)
        joints.insert(parentIndex, newJoint)
        
        card = targetJoint.card
        for i, jnt in enumerate(joints[parentIndex:], parentIndex):
            connectAttr( jnt.message, card.attr('joints[%i].jmsg' % i), f=True )
        
        if targetJoint.bpParent:
            a = pdil.dagObj.getPos(targetJoint)
            b = pdil.dagObj.getPos(targetJoint.bpParent)
            pdil.dagObj.moveTo( newJoint, a + (a - b) / 2.0 )
            
            proxyskel.pointer(targetJoint.bpParent, newJoint)
        else:
            pdil.dagObj.moveTo( newJoint, targetJoint )
        
        proxyskel.pointer(newJoint, targetJoint)
        return newJoint
        
    
    def insertChild(self, previousJoint):
        '''
        Insert a joint after the `previous` joint.
        
        ..  todo:: Need to handle sequence vs individual naming.
        '''
        newJoint = self.addJoint()
        
        joints = self.joints[:]
        
        previousChildren = previousJoint.proxyChildren
        
        i = joints.index(previousJoint)

        proxyskel.pointer(previousJoint, newJoint)
        previousJointPos = dt.Vector( xform(previousJoint, q=True, ws=True, t=True) )
        
        # If the final pos isn't at the end, all the connections need shifting.
        if i < len(joints) - 2:
            followingJoint = joints[i + 1]
            insertPoint = joints[i + 1].cardCon
            
            for i, jnt in enumerate( joints[ i + 1:-1 ], i + 1):
                connectAttr( jnt.message, joints[i + 1].cardCon.jmsg, f=True )
            
            newJoint.message >> insertPoint.jmsg
            
            proxyskel.pointer(newJoint, followingJoint)
            
            # Position the new joint in between
            followingJointPos = dt.Vector( xform(followingJoint, q=True, ws=True, t=True) )
            
            pos = (previousJointPos - followingJointPos) / 2.0 + followingJointPos
        else:
            pos = previousJointPos
            
        for child in previousChildren:
            proxyskel.pointer(newJoint, child)
            
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
        
        pdil.math.opposite(b) >> a
        
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
                    jnt.rename( pdil.simpleName(jnt.parent, '{0}_tip') )
        """
        
        queued = {}
        
        names = iter( itertools.chain(self.nameList(usePrefix=False, mirroredSide=False), itertools.cycle(['NOT_ENOUGH_NAMES'])) )
        
        for jnt in self.joints:
            if not jnt.isHelper:
                targetName = next(names) + '_bpj'
                if pdil.simpleName(jnt) != targetName:
                    if cmds.ls(targetName, r=1) and targetName != 'NOT_ENOUGH_NAMES_bpj':
                        jnt.rename('_temp_')
                        queued[jnt] = targetName
                    else:
                        jnt.rename(targetName)
            else:
                #jnt.rename('_helper_bpj')
                jnt.rename( pdil.simpleName(self, '{}_helper_bpj') )
        
        for jnt, targetName in queued.items():
            jnt.rename(targetName)
                

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
        
        '''
        the above loop done 1000x
        ~.88

        1.5 as cmds

        .55 as cmds but cast to pynode at end

        '''

        ''' &&& Trash this I think
        # If that fails, it means it's an older rig, so we must use the proxy children connections,
        # which fails to deal with parent to mirror.
        if not subCards:
            subCards = []
            for _joint in self.joints:
                for child in _joint.proxyChildren:
                    if child.cardCon.node() != self and child.cardCon.node() not in subCards:
                        subCards.append(child.cardCon.node())
        '''
        return sorted(subCards, key=lambda card: (card.rigData.get('buildOrder', 10), card.name()) )
        
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
                ctrl = getattr( getattr( self, 'output' + side ), type)
                if ctrl:
                    yield (ctrl, side, type)
                
    getMainControls = _outputs
    # Much better name
                
    def saveShapes(self):
        '''
        If there is any output, stores the shape info.
        Done as unique attr because I've had trouble in the past with compound
        array attrs with strings.
        '''
        for ctrl, side, type in self.getMainControls():
            shapeInfo = controllerShape.saveControlShapes(ctrl)
            shapeInfo = pdil.text.asciiCompress(shapeInfo)
            pdil.factory.setStringAttr( self, 'outputShape' + side + type, shapeInfo)
                    
    def restoreShapes(self, objectSpace=True, targetKeys=None, targetSide=None, targetMotion=None):
        '''
        Apply any shape data saved via saveShapes
        '''
        for ctrl, side, type in self._outputs():
            if targetSide and targetSide != side:
                continue
            
            if targetMotion and targetMotion != type:
                continue
            
            shapeInfo = pdil.factory.getStringAttr( self, 'outputShape' + side + type)
            if shapeInfo:
                shapeInfo = pdil.text.asciiDecompress(shapeInfo)
                controllerShape.loadControlShapes( ctrl, shapeInfo.splitlines(), useObjectSpace=objectSpace, targetCtrlKeys=targetKeys)
    
    
    def saveJointData(self):
        ''' Saves set driven keys, scaleConstriant and connections.
        '''
        
        for bpj in self.joints:
            for mirrorKey, jnt in [('real', bpj.real), ('realMirror', bpj.realMirror)]:
                if jnt:

                    scaleConst = scaleConstraint(jnt, q=True)
                    orientConst = orientConstraint(jnt, q=True)
                    
                    scaleTarget = scaleConstraint(scaleConst, q=True, tl=True) if scaleConst else None
                    orientTarget = orientConstraint(orientConst, q=True, tl=True) if orientConst else None

                    with bpj.info as info:
                        info['rigState.{}.sdk'.format(mirrorKey)] = misc.findSDK(jnt)  # Technically this will pick up sdk on any attr
                        info['rigState.{}.connections'.format(mirrorKey)] = getLinksScaleOnly(jnt)
                    
                        # The intent is that if the orient target is the same, then scale was setup in fossil so don't save it
                        if scaleTarget and scaleTarget != orientTarget:
                            scales = pdil.constraints.scaleSerialize(jnt, nodeConv=ids.getIdSpec)
                        else:
                            scales = None
                            
                        info['rigState.{}.scaleConstraint'.format(mirrorKey)] = scales
                        
    
    def restoreJointData(self):
        for bpj in self.joints:
            for mirrorKey, jnt in [('real', bpj.real), ('realMirror', bpj.realMirror)]:
                info = bpj.info
                if jnt:
                    
                    sdk = info.get('rigState.{}.sdk'.format(mirrorKey), None)
                    if sdk:
                        misc.applySDK(jnt, sdk)
                    
                    scaleConstInfo = info.get('rigState.{}.scaleConstraint'.format(mirrorKey), None)
                    if scaleConstInfo:
                        pdil.constraints.scaleDeserialize(jnt, scaleConstInfo, nodeDeconv=ids.readIdSpec)
    
                    conInfo = info.get('rigState.{}.connections'.format(mirrorKey), None)
                    if conInfo:
                        setLinks(jnt, conInfo)
    
    
    def _saveData(self, function):
        '''
        Runs `function` on each control made by the card, returning a dict like:
        
            {
                '<side> <kinematic type>': {
                    'main': <return of function(main)>,
                    'socket': <return of function(socket)>,
                }
            }
            
        <side> is "Left" "Right" or "Center" and <kinematic type> is "ik" of "fk"
        so the keys are things like "Left fk"
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
        
        return allData
        
    def _restoreData(self, function, info):
        '''
        The other side of _saveData, running `function` on each control, passing the
        appropriate `info`.
        '''
        
        issues = []
        
        for side_type, value in info.items():
            side, type = side_type.split()
            
            mainCtrl = getattr(getattr(self, 'output' + side), type)
            
            for id, ctrlInfo in value.items():
                if id == 'main':
                    ctrl = mainCtrl
                else:
                    ctrl = mainCtrl.subControl[id]
                try:
                    function(ctrl, ctrlInfo)
                except Exception:
                    print('> > > --------------', ctrl, ctrlInfo)
                    print( traceback.format_exc() )
                    print('< < < --------------')
                    issues.append( traceback.format_exc() )
        
        if issues:
            raise Exception('\n\n'.join(issues))
                
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
        ('customAttrs', controllerShape.identifyCustomAttrs, restoreCustomAttr),
        ('visGroup',    visNode.getVisLevel,               visNode.connect),
        ('connections', getLinks,                           setLinks),
        ('setDriven',   findSDK,                            applySDK),
        ('spaces',      space.serializeSpaces,              space.deserializeSpaces),
        ('constraints', findConstraints,                    applyConstraints),
        ('lockedAttrs', findLockedAttrs,                    lockAttrs),
    ]
    
    toSave = collections.OrderedDict( [
        ('customAttrs', (controllerShape.identifyCustomAttrs, restoreCustomAttr)), # Do this first!
        ('visGroup',    (visNode.getVisLevel,               visNode.connect)),
        ('connections', (getLinks,                          setLinks)),
        ('setDriven',   (findSDK,                           applySDK)),
        ('spaces',      (space.serializeSpaces,             space.deserializeSpaces)),
        ('constraints', (findConstraints,                   applyConstraints)),
        ('lockedAttrs', (findLockedAttrs,                   lockAttrs)),
    ] )
    

    def saveState(self):
        allData = self.rigState
        
        for niceName, (harvestFunc, restoreFunc) in self.toSave.items():
            data = self._saveData(harvestFunc)
            
            # I think this is a good idea.  Helping the corner case if you accidentally go fk
            # to preserve ik data instead of clobbering it.
            
            if niceName not in allData:
                allData[niceName] = data
            else:
                allData[niceName].update( data )
                
        self.rigState = allData
        
        rigClass = self.rigCommandClass
        if rigClass:
            rigClass.saveState(self)
        
        self.saveJointData()
        
        self.saveShapes()

    def restoreState(self, shapesInObjectSpace=True):
        '''
        Restores everything listed in `toSave`, returning a list of ones that failed.
        
        &&& Need to have optional error ignoring for testing but a nicer user experience.
            Currently the test_controller_shape_restore looks at the result but defaulting
            to erroring would be better.
        '''

        allData = self.rigState
        
        errors = exceptions.FossilMultiError()
        #issues = []

        for niceName, (harvestFunc, restoreFunc) in self.toSave.items():
            if niceName in allData and allData[niceName]:
                try:
                    self._restoreData(restoreFunc, allData[niceName])
                except Exception:
                    print(traceback.format_exc())
                    #issues.append( 'Issues restoring ' + niceName )
                    errors.append( 'Issues restoring ' + niceName + ' on ' + self.shortName(), traceback.format_exc())
                
        rigClass = self.rigCommandClass
        
        if rigClass:
            try:
                rigClass.restoreState(self)
            except Exception:
                #issues.append( 'Issues restoring shapes' )
                errors.append( 'Issues restoring shapes on ' + self.shortName(), traceback.format_exc())
        
        self.restoreJointData()
        
        self.restoreShapes(objectSpace=shapesInObjectSpace)
        
        #return issues
        if errors:
            raise errors


    # -----------------

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

    def autoRename(self):
        ''' Renames based on the name pattern
        '''
        
        nameInfo = self.rigData.get('nameInfo', {})
        name = nameInfo.get('head', '')
        if name:
            self.rename( name[0] + '_card' )
            
        name = nameInfo.get('repeat', '')
        if name:
            self.rename( name + '_card' )
            
        name = nameInfo.get('tail', '')
        if name:
            self.rename( name[0] + '_card' )
            
        
'''
def findConstraints(ctr):
    align = pdil.dagObj.align(ctrl)

    return {
        'main': pdil.constraints.aimSerialize(ctrl) if aimConstraint(ctrl, q=True) else None,
        'align': pdil.constraints.aimSerialize(align) if align and aimConstraint(align, q=True) else None,
    }
'''


class NOT_FOUND:
    pass


def getTrueRoot():
    ''' Returns the root joint according the 'root_name', building it if needed.
    
    &&& DUPLICATED CODE IN fossileNodes
    '''
    rootName = config._settings['root_name']
    
    trueRoot = PyNode(rootName) if objExists( rootName ) else joint(None, n=rootName)
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
            match = re.search(r'\{extraNode([0-9]*)\}', cmd)
        
            if match:
                index = int(match.group(1))
                if tempJoint.extraNode[index]:
                    return tempJoint.extraNode[index]
    
    return None


class BPJoint(nt.Joint):

    postCommand     = pdil.factory.StringAccess('postCommand')
    real            = pdil.factory.SingleConnectionAccess('realJoint')
    realMirror      = pdil.factory.SingleConnectionAccess('realJointMirror')
    suffixOverride  = pdil.factory.StringAccess('suffixOverride')
    customUp        = pdil.factory.SingleConnectionAccess('customUp')
    customOrient    = pdil.factory.SingleConnectionAccess('moCustomOrient')
    proxy           = pdil.factory.SingleConnectionAccess('proxy')
    orientTarget    = pdil.factory.SingleStringConnectionAccess('orientTargetJnt')
    info            = pdil.factory.JsonAccess('fossilInfo')

    
    # &&& I need to deprecate this to remove any conflicts with pymel and replace it with property `bpParent`
    # AND change the local storage to something like fslBPParent
    parent          = pdil.factory.SingleConnectionAccess('parent')

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
    def bpParent(self):
        return pdil.factory.getSingleConnection(self, 'parent')
    
    @bpParent.setter
    def bpParent(self, val):
        self.setBPParent(val)
    
    #&&& MAKE THIS bpChildren to match bpParent and because "proxy" is the referenced visibility skeleton
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
        CUSTOM = 'CUSTOM'
        Result = collections.namedtuple( 'Result', 'status joint' )

    def getOrientState(self):
        '''
            Future children are not considered for orientation
        '''
        
        '''
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
            return pdil.math.isClose( _pos, xform(other, q=True, ws=True, t=True))
            
        cardJoints = self.card.joints
        children = self.proxyChildren
        localChildren = [c for c in children if c in cardJoints]
        outerChildren = [c for c in children if c not in localChildren and c.card.rigData.get( enums.RigData.rigCmd ) != 'Group']
        
        if self.customOrient:
            return self.Orient.Result( self.Orient.CUSTOM, self.customOrient )
        
        target = self.orientTarget
        joint_build_log.debug( '.orientTarget = {}'.format(target) )
        if target == '-world-':
            joint_build_log.debug('world')
            return self.Orient.Result( self.Orient.WORLD, None )
        elif target == '-as parent-':
            joint_build_log.debug('-parent- set explicitly')
            return self.Orient.Result( self.Orient.AS_PARENT, None )
        elif target:
            joint_build_log.debug('explicit target {}'.format(target))
            return self.Orient.Result( self.Orient.HAS_TARGET, target )
                    
        if not children:
            joint_build_log.debug('parent, no children exist')
            return self.Orient.Result( self.Orient.AS_PARENT, None )
        
        if len(localChildren) == 1:
            if tooClose(localChildren[0]):
                joint_build_log.debug('parent, SINGLE local child is too close')
                return self.Orient.Result( self.Orient.AS_PARENT, None )
            else:
                joint_build_log.debug('Towards single local child {}'.format(localChildren[0]))
                return self.Orient.Result( self.Orient.SINGLE_CHILD, localChildren[0] )
        
        if localChildren:
            centered = [c for c in localChildren if abs(xform(c, q=True, ws=True, t=True)[0]) < 0.001]
            
            if len(centered) == 1 and not tooClose(centered[0]):
                joint_build_log.debug('A single child was centered {}'.format(centered[0]))
                return self.Orient.Result( self.Orient.SINGLE_CHILD, centered[0] )
            elif not outerChildren:
                joint_build_log.debug('parent, too many local children')
                return self.Orient.Result( self.Orient.AS_PARENT, None )
            
        # At this point, no local children were orientable so check the following card(s).
        
        if len(outerChildren) == 1:
            # If I'm not mirrored, but next is, it branches so use parent.
            if not self.card.isCardMirrored() and outerChildren[0].card.isCardMirrored():
                joint_build_log.debug('as parent, next card branches')
                return self.Orient.Result( self.Orient.AS_PARENT, None )
                
            # Both self and child are mirrored, or child is skipped, so use it.
            else:
                if not tooClose(outerChildren[0]):
                    #joint_build_log.debug()
                    return self.Orient.Result( self.Orient.SINGLE_CHILD, outerChildren[0] )
                else:
                    #joint_build_log.debug()
                    return self.Orient.Result( self.Orient.AS_PARENT, None )
        
        # There are several outerChildren
        centered = [c for c in outerChildren if abs(xform(c, q=True, ws=True, t=True)[0]) < 0.001]
        
        if len(centered) == 1 and not tooClose(centered[0]):
            #joint_build_log.debug()
            return self.Orient.Result( self.Orient.SINGLE_CHILD, centered[0] )
        
        #joint_build_log.debug()
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
        if self.card.rigData.get( enums.RigData.rigCmd ) not in ('Freeform', 'SquashStretch', 'SurfaceFollow'):
            if parent is None:
                if self.parent and self.parent.card != self.card:
                    self.card.parentCardLink = None
                    
                proxyskel.unpoint(self)
                pdil.pubsub.publish('fossil card reparented')
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
            if parent:
                if self.card != parent.card:
                    if self.card.parentCardLink != parent.card:
                        self.card.parentCardLink = parent.card
            else:
                # Don't know why someone would need this, but they could freeform mutliple top level joints.
                self.parent = None
                proxyskel.unpoint(self.parent)
            
        # Link to new parent
        proxyskel.pointer(parent, self)
        pdil.pubsub.publish('fossil card reparented')


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
            mobj = pdil.capi.asMObject(mainControl)
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
    
    @property
    def isPrimarySide(self):
        side = self.getSide()
        if side == 'Center':
            return True
        
        if side == self.card.findSuffix().title():
            return True
        
        return False
        
    
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
    
    def getMotionKeys(self):
        ''' Return [<side>, <kinematic>], ex ['Center', 'ik'].  Use with `Card.getLeadController()`.
        '''
        outputAttr = self._outputAttr()
        
        side = outputAttr.plug.name().split('.')[-1][6:]
        
        if self == getattr(outputAttr, 'ik'):
            return [side, 'ik']
        else:
            return [side, 'fk']
        
    
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
        card = [c for c in self.message.listConnections() if isinstance(c, Card)]
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
        
        def keys(self):
            keys = []
            for link in self.src.controlLinks:
                key = link.controlName.get()
                con = link.controlLink.listConnections()
                if con:
                    keys.append(key)
            return keys
        
        def values(self):
            values = []
            for link in self.src.controlLinks:
                con = link.controlLink.listConnections()
                if con:
                    values.append(con[0])
            return values
        
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
                        side = node.leadController(current)._outputAttr().side
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
                    side = node.leadController(current)._outputAttr().side
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


class SubController(nt.Transform):
    
    @classmethod
    def _isVirtual(cls, obj, name):
        # Returns True if it's message is connected to a .controlLink ()
        
        if name:  # Not sure why, but sometimes this is called without an name.
            obj = pdil.capi.asMObject(name)
            
            msgplug = obj.findPlug('message', False)

            for con in msgplug.connectedTo(False, True):
                if con.name().endswith('controlLink'):
                    return True
        
        return False

    def ownerInfo(self):
        '''
        Returns the node that has this as a sub control and the key to access it.
        '''
        
        obj = pdil.capi.asMObject(self)
        
        msgplug = obj.findPlug('message', False)

        for con in msgplug.connectedTo(False, True):
            if con.name().endswith('controlLink'):
                #node, plug = con.name().split('.', 1)
                
                # Can't remember why I did this but is seems fine.
                plug = con.partialName( useFullAttributePath=True, useLongNames=True)
                node = OpenMaya.MFnDagNode( con.node() ).fullPathName()

                return PyNode(node), getAttr( (node + '.' + plug)[:-11] + 'controlName' )


registerNodeType( SubController )
registerNodeType( RigController )
registerNodeType( Card )
registerNodeType( BPJoint )
