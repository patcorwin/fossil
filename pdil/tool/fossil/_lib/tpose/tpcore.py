# Functionality so a custom tpose can be made with fk offsets to put into the bind pose
'''
TODO:
* When reposer exists, copy unlocked translate and rotates
* Just copy the values onto the node so the old one can be deleted
* Delete old version, if it exists
* Rename the old one before making the new one
'''

from __future__ import absolute_import, division, print_function

import contextlib

from pymel.core import cmds, delete, duplicate, group, hasAttr, joint, listRelatives, ls, makeIdentity, objExists, parentConstraint, PyNode, showHidden, xform, evalDeferred

from pymel.core import displaySmoothness # noqa for an evalDeferred


from pdil import simpleName
import pdil


from ... import util
from ..._core import find
from ..._lib import proxyskel


def updateReposers(cards=None, missingOnly=False, progress=None):
    ''' (Re)Make the given cards' reposers.
    
    Args:
        cards: Cards to operate on, `None`, the default, operates on all cards.
        missingOnly: If `True`, only make missing reposers.
        progress: Optional progressWindow passed to `generateReposer()`, see it for configuration.
    '''
    if not cards:
        cards = util.selectedCards()
    
    if not cards:
        cards = find.blueprintCards()
    
    valid = getValidReposeCards()
    cards = [card for card in cards if not getRCard(card, valid)]
    
    otherCards = find.cardJointBuildOrder()
    for c in cards:
        otherCards.remove(c)
        
    #with pdil.ui.progressWin(title='Building reposers', max=len(cards) * 2) as prog:
    with reposeToBindPose(otherCards):
        generateReposer( cards, progress=progress)
    
    # For some reason the shaders are always messed up so burp the display to correct it, and only when evalDeferred
    evalDeferred( "displaySmoothness( '{}', divisionsU=0, divisionsV=0, pointsWire=4, pointsShaded=1, polygonObject=1)".format( getReposeContainer().name() ) )


#------------------------------------------------------------------------------


def reposerExists():
    ''' Returns `True` if repose cards exist.
    '''
    return bool( getReposeRoots() )


def getValidReposeCards():
    ''' Return valid repose cards, i.e. excludes the 'old' ones.
    '''
    return listRelatives( listRelatives( getReposeRoots(), ad=True, type='nurbsSurface' ), p=True )


def getRJoint(bpj):
    ''' Get repositioned joint from blueprint joint
    '''
    for plug in bpj.message.listConnections(s=False, d=True, p=True):
        if plug.attrName() == 'bpj':
            return plug.node()


def getRCard(card, validCards=None):
    ''' Given a regular bp card, returns the reposeCard from the list of `validCards`
    Use `getValidReposeCards()` for `validCards` (this is performance optimization).
    '''
    validCards = validCards if validCards else getValidReposeCards()
    
    for plug in card.message.listConnections(s=False, d=True, p=True):
        if plug.attrName() == 'bpCard':
            if plug.node() in validCards:
                return plug.node()


def getReposeContainer():
    name = 'ReposeContainer'
    
    mainBP = proxyskel.masterGroup()
    for obj in listRelatives(mainBP):
        if obj.name() == name:
            return obj
    
    grp = group(n=name, em=True)
    grp.visibility.set(False)
    grp.setParent(mainBP)
    return grp


"""
def getReposeCardNormal(obj):
    a = dt.Vector( xform(obj.cv[0][0], q=True, ws=True, t=True) )
    b = dt.Vector( xform(obj.cv[1][0], q=True, ws=True, t=True) )
    c = dt.Vector( xform(obj.cv[0][1], q=True, ws=True, t=True) )
    
    v1 = a - b
    v2 = c - b
    
    return v1.cross(v2).normal()


def matchWorldAxis(obj, viaOrbit=False):
    
    normal = getReposeCardNormal(obj)
    x_abs, y_abs, z_abs = abs(normal)
    x, y, z = normal
    
    if x_abs > y_abs and x_abs > z_abs:
        #X_abs DOM
        pass

    elif y_abs > x_abs and y_abs > z_abs:
        yRot = dt.Vector( x, 0, z ).angle( dt.Vector(1, 0, 0) )
        print(yRot)
        
        
    elif z_abs > x_abs and z_abs > y_abs:
        #Z DOM
        pass
"""


def renameReposeObj(obj, targetName, previous):
    ''' Rename `obj` to `targetName`, suffixing the (possible) existing one and storing transform info.
    '''
    #print('    Rename {} with prev of {}'.format(obj, previous) )
    oldName = targetName.replace('repose', 'old')
    if objExists(oldName):  # and '_helper' not in oldName:
        # For now, just skip of _helpers, though I should give them generated unique names
        print(oldName, 'exists, deleting')
        delete(oldName)
    
    if objExists(targetName):
        old = PyNode(targetName)
        old.rename( oldName )
        
        previous = old if not previous else previous
    
    if previous:
        addVector(obj, 'prevRot', previous.r.get())
        addVector(obj, 'prevTrans', previous.t.get())
        addVector(obj, 'prevRotWorld', xform(previous, q=True, ws=True, ro=True))
        addVector(obj, 'prevTransWorld', xform(previous, q=True, ws=True, t=True))
    
    obj.rename( targetName )


def reposeLink(srcObj, reposeObj, attr):
    ''' Removes existing connections (shouold only be one if ther are any) hooking up the new object.
    Returns the previously connected object, and a list of attrs on the orig that were unlocked.
    '''
    
    existing = [plug for plug in srcObj.message.listConnections(d=True, s=False, p=True) if plug.attrName() == attr]
    
    for plug in existing:
        srcObj.message.disconnect(plug)
    
    reposeObj.addAttr(attr, at='message')
    srcObj.message >> reposeObj.attr(attr)

    unlocked = []

    if existing:
        unlocked = [attr for attr in [t + a for t in 'tr' for a in 'xyz'] if not existing[0].node().attr(attr).isLocked()]
        '''
        # Inherit unlocks from previous.  Not sure this is as useful with the orbits.
        for attr in [t + a for t in 'tr' for a in 'xyz']:
            print(existing[0].node().attr(attr), existing[0].node().attr(attr).isLocked())
            if not existing[0].node().attr(attr).isLocked():
                reposeObj.attr(attr).unlock()
                reposeObj.attr(attr).showInChannelBox(True)
        '''
        
        return existing[0].node(), unlocked
    
    return None, unlocked


def stripReposerCard(card):
    ''' Make sure the reposer card doesn't look like a blueprint card.
    '''
    
    for attr in [
        'fossilRigData',
        'outputLeft',
        'outputCenter',
        'outputRight',
        'outputShapeCenterfk',
        'outputShapeCenterik',
        'outputShapeLeftfk',
        'outputShapeLeftik',
        'outputShapeRightfk',
        'outputShapeRightik',
        'fossilRigState',
    ]:
        if card.hasAttr(attr):
            card.deleteAttr(attr)


def makeMirrored(reposeJoint):
    ''' Makes a joint that mirrors the transforms of the given repose joint, possibly returning an already existing one.
    '''
    
    if hasAttr(reposeJoint, 'mirrorGroup'):
        con = reposeJoint.mirrorGroup.listConnections()
        if con:
            return con[0]
    else:
        reposeJoint.addAttr('mirrorGroup', at='message')
    
    root = PyNode(reposeJoint.fullPath().split('|', 2)[1])
    print(root)
    for child in root.listRelatives():
        if child.name() == 'mirrorGroups':
            grouper = child
            break
    else:
        grouper = group(em=True, n='mirrorGroups')
        grouper.inheritsTransform.set(False)
        grouper.setParent(root)
    
    
    follower = group(em=True)
    mirror = group(em=True)
    reposeMirror = group(em=True)
    
    pdil.math.multiply(follower.tx, -1) >> mirror.tx
    follower.ty >> mirror.ty
    follower.tz >> mirror.tz
    
    follower.rx >> mirror.rx
    pdil.math.multiply(follower.ry, -1) >> mirror.ry
    pdil.math.multiply(follower.rz, -1) >> mirror.rz
    
    parentConstraint(reposeJoint, follower, mo=False)
    parentConstraint(mirror, reposeMirror)
    reposeMirror.setParent(reposeJoint)
    
    reposeMirror.message >> reposeJoint.mirrorGroup
    
    follower.setParent(grouper)
    mirror.setParent(grouper)
    
    return reposeMirror


def generateReposer(cards=None, placeholder=False, progress=None):
    ''' If no cards are specificed, a new reposer is build, otherwise it
    rebuilds/adds reposers for the specified cards.
    
    
    Args:
        cards
        placeholder
        progress: Optional `progressWindow` that will be `.update()`'d twice for
            each card, MUST be preconfigured (in case several things are updating)
    
    &&& TODO Verify the cards can be built in any order
    '''
    
    global jointMapping # global'd for debugging
    suffix = '_placeholder' if placeholder else ''
    
    rJoints = []
    rCards = []
    unlock = {} # <repose joint or card>: <list of attrs to be re-locked>

    jointMapping = {}  # Lazy "bi-directional mapping" of bpj <-> reposeJoint, both are added as keys to eachother

    # Build all the cards and joints
    if not cards:
        cards = find.blueprintCards()
        # Delete previous roots
        for oldRoot in getReposeRoots():
            oldRoot.deleteAttr('reposeRoot')
            
    # Otherwise populate the containers with the existing reposer to build/add new stuff.
    else:
        #allExistingRCards = set( cmds.ls( '*.bpCard', o=True, r=True, l=True ) )
        allExistingRJoints = set( cmds.ls( '*.bpj', o=True, r=True, l=True ) )
        
        for oldRoot in getReposeRoots():
            joints = cmds.listRelatives( str(oldRoot), f=True, ad=True, type='joint' )
            joints = [PyNode(c) for c in allExistingRJoints.intersection(joints)]
        
            for rj in joints:
                bpj = rj.bpj.listConnections()[0]
                jointMapping[rj] = bpj
                jointMapping[bpj] = rj

    
    for card in cards:
        if progress:
            progress.update()
        
        rCard = duplicate(card, po=0)[0]
        showHidden(rCard)
        pdil.dagObj.unlock(rCard)
        stripReposerCard(rCard)
        
        targetName = simpleName(card, '{}_repose' + suffix)
        
        previous, attrs = reposeLink(card, rCard, 'bpCard') if not placeholder else (None, [])
        unlock[rCard] = attrs
        
        renameReposeObj(rCard, targetName, previous)
        
        for child in rCard.listRelatives():
            if not child.type() == 'nurbsSurface':
                delete(child)
        rCards.append(rCard)
        makeIdentity(rCard, t=False, r=False, s=True, apply=True)
        pdil.dagObj.lock( rCard, 's' )

        for jnt in card.joints:
            reposeJoint = joint(None)
            targetName = simpleName(jnt, '{}_repose' + suffix)
            
            previous, attrs = reposeLink(jnt, reposeJoint, 'bpj') if not placeholder else (None, [])
            unlock[reposeJoint] = attrs
            renameReposeObj(reposeJoint, targetName, previous)

            pdil.dagObj.matchTo(reposeJoint, jnt)

            #assert jnt.info.get('options', {}).get('mirroredSide', False) is False, 'parent to mirrored joints not supported yet'
            
            jointMapping[jnt] = reposeJoint
            jointMapping[reposeJoint] = jnt

            rJoints.append(reposeJoint)
            
    
    # Set their parents
    for reposeJoint in rJoints:
        parent = jointMapping[reposeJoint].parent
        if parent in jointMapping: # Check against joint mapping in case only a few selected cards a being tposed
            reposeJoint.setParent( jointMapping[parent] )
    
    reposeContainer = getReposeContainer()
    
    
    # Put under cards, card pivot to lead joint
    for rCard, card in zip(rCards, cards):
        if progress:
            progress.update()
        bpj = card.parentCardJoint
        #print('BPJ - - - - ', bpj, bpj in jointMapping)
        if bpj in jointMapping:
            start = card.start() if card.joints else bpj
            #rCard.setParent( getRJoint(bpj) )
            pdil.dagObj.unlock(rCard)
            
            #firstBpj = card.joints[0]
            #return
            
            isMirrored = card.isCardMirrored()
            
            
            mirroredSide = card.joints[0].info.get('options', {}).get('mirroredSide')
            #print('rCard.mirror', rCard.mirror, 'info:', mirroredSide)
            #if rCard.mirror is False and mirroredSide:
            if isMirrored is False and card.mirror is False and mirroredSide:
                #print('opposite mirror')
                rCard.setParent( makeMirrored( jointMapping[bpj] ) )
            else:
                #print('regular side stuff')
                rCard.setParent( jointMapping[bpj] )
                
            #cmds.parent(str(rCard), str(jointMapping[bpj]))
            xform(rCard, ws=True, piv=xform(start, q=True, t=True, ws=True) )
            pdil.dagObj.lock(rCard, 't')
            
        else:
            if not placeholder:
                rCard.addAttr('reposeRoot', at='message')
                rCard.setParent( reposeContainer )
                
        addVector(rCard, 'origRot', rCard.r.get())
        addVector(rCard, 'origTrans', rCard.t.get())
        #start = getRJoint(card.start())
        start = jointMapping[card.start()]
        start.setParent( rCard )
        pdil.dagObj.lock( start, 't s' )

        if rCard in unlock:
            for attr in unlock[rCard]:
                rCard.attr(attr).unlock()
                rCard.attr(attr).showInChannelBox(True)
                
    for reposeJoint in rJoints:
        pdil.dagObj.lock(reposeJoint, 'ry rz')
        pdil.dagObj.lock(reposeJoint, 't s') # I can't see why I wasn't locking t/s already.  Possible exception, `freeform`
        
        if reposeJoint in unlock:
            for attr in unlock[reposeJoint]:
                reposeJoint.attr(attr).unlock()
                reposeJoint.attr(attr).showInChannelBox(True)
        
        addVector(reposeJoint, 'origRot', reposeJoint.r.get())
        addVector(reposeJoint, 'origTrans', reposeJoint.t.get())
    
        '''
        children = reposeJoint.listRelatives(type='transform')
        if len(children) > 1:
            for child in children:
                orbit = joint(reposeJoint)
                orbit.t.lock()
                orbit.s.lock()
                renameReposeObj(orbit, simpleName(child, '{}_orbit'), None)
                child.setParent(orbit)
        '''
    

def getReposeRoots():
    ''' Return the top level reposer cards
    '''
    return [plug.node() for plug in ls('*.reposeRoot')]


def setRot(obj, r):
    ''' Attempts to set each axis individually.
    '''
    for axis, val in zip('xyz', r):
        try:
            obj.attr( 'r' + axis ).set(val)
        except Exception:
            pass


def setTrans(obj, t):
    ''' Attempts to set each axis individually.
    '''
    for axis, val in zip('xyz', t):
        try:
            obj.attr( 't' + axis ).set(val)
        except Exception:
            pass


@contextlib.contextmanager
def reposeToBindPose(cards):
    ''' Temporarily puts the repose cards in their original orientation (to add/edit cards).
    '''
    validCards = getValidReposeCards()

    currentTrans = {}
    currentRot = {}

    jointRot = {}

    for card in cards:
        reposeCard = getRCard(card, validCards)
        if not reposeCard:
            continue

        currentRot[reposeCard] = reposeCard.r.get()
        currentTrans[reposeCard] = reposeCard.t.get()
        
        setRot(reposeCard, reposeCard.origRot.get())
        setTrans(reposeCard, reposeCard.origTrans.get())

        for jnt in card.joints:
            repose = getRJoint(jnt)

            if repose:
                jointRot[repose] = repose.r.get()
                setRot(repose, repose.origRot.get())

    yield

    for reposeCard, origRot in currentRot.items():
        setRot(reposeCard, origRot )
        setTrans(reposeCard, currentTrans[reposeCard] )

    for reposeJoint, origRot in jointRot.items():
        setRot(reposeJoint, origRot )


class matchReposer(object):
    ''' Temporarily puts the cards (aka bind pose) in the tpose.
    
    Intended use is as a context manager but steps can be separated for debugging.
    '''
    
    def __enter__(self):
        pass
        
    def __exit__(self, type, value, traceback):
        self.unmatch()
    
    def __init__(self, cards):
        self.relock = []
        self.prevPos = {}
        self.prevRot = {}

        validCards = getValidReposeCards()

        for card in cards:
            reposeCard = getRCard(card, validCards)
            if not reposeCard:
                continue
                
            self.prevRot[card] = self.getRotations(card)
            rot = xform(reposeCard, q=True, ws=True, ro=True)
            
            # Need to unlock/disconnect rotation, then redo it later (to handle twists aiming at next joint)
            
            xform(card, ws=True, ro=rot)
            
            for jnt in card.joints:
                repose = getRJoint(jnt)
                
                if repose:
                    for axis in 'xyz':
                        plug = jnt.attr('t' + axis)
                        if plug.isLocked():
                            plug.unlock()
                            self.relock.append(plug)
                    #if jnt.tx.isLocked():
                    #    jnt.tx.unlock()
                    #    relock.append(jnt)
                        
                    self.prevPos[jnt] = jnt.t.get()
                    
                    trans = xform(repose, q=True, t=True, ws=True)
                    try:
                        xform(jnt, ws=True, t=trans)
                    except Exception:
                        del self.prevPos[jnt]
                        
    def unmatch(self):
        
        for jnt, pos in self.prevPos.items():
            try:
                jnt.t.set(pos)
            except Exception:
                pass
                
        for plug in self.relock:
            plug.lock()
            
        for card, rot in self.prevRot.items():
            self.restoreRotations(card, rot)


    @staticmethod
    def getRotations(obj):
        ''' Returns dict of {'rx': <rotation val>} for settable rotations.
        '''
        restoreInfo = {}
        
        # Early out if everything is locked
        if obj.r.listConnections(s=True, d=False, p=False) or obj.r.isLocked():
            return restoreInfo
        
        for axis in 'xyz':
            plug = obj.attr( 'r' + axis )
            if not (plug.isLocked() or plug.listConnections(s=True, d=False, p=False)):
                restoreInfo['r' + axis] = plug.get()
        
        return restoreInfo
    
    
    @staticmethod
    def restoreRotations(obj, restoreInfo):
        ''' Applies rotation dict from `.getRotations`
        '''
        for attr, val in restoreInfo.items():
            obj.attr(attr).set(val)


class goToBindPose(object):
    ''' Puts the rig into the bind pose.
    
    Intended use is as a context manager but steps can be separated for debugging.
    '''
    
    def __enter__(self):
        pass
    
    def __exit__(self, type, value, traceback):
        self.returnFromPose()
        
    def __init__(self):
        # &&& I need some coralary toTPose, which is basically zeroPose but also does uncontrolled joints, just in case

        # Joints without controllers still need to be reposed
        '''
        joints = []
        for card in core.findNode.allCards():
            joints += card.getOutputJoints()

        for j in joints:
            if not j.tr.listConnections():
                if j.hasAttr('bindZero'):
                    j.r.set( j.bindZero.get() )
                if j.hasAttr( 'bindZeroTr' ):
                    if not j.hasAttr('tposeTr'):
                        addVector(j, 'tposeTr', j.t.get()).lock()

                    j.t.set( j.bindZeroTr.get() )
        '''

        controls = find.controllers()
        self.current = {ctrl: (ctrl.t.get(), ctrl.r.get()) for ctrl in controls }


        for ctrl in controls:
            if ctrl.hasAttr( 'bindZero' ):
                try:
                    ctrl.r.set( ctrl.bindZero.get() )
                except Exception:
                    pass

            if ctrl.hasAttr( 'bindZeroTr' ):
                ctrl.t.set( ctrl.bindZeroTr.get() )

    def returnFromPose(self):
        for ctrl, (pos, rot) in self.current.items():
            setRot(ctrl, rot)
            setTrans(ctrl, pos)


def addVector(obj, name, val):
    ''' Adds a double3 attribute to obj, setting the value and returning the plug.
    '''
    if not obj.hasAttr(name):
        obj.addAttr( name, at='double3' )
        obj.addAttr( name + 'X', at='double', p=name )
        obj.addAttr( name + 'Y', at='double', p=name )
        obj.addAttr( name + 'Z', at='double', p=name )
        
    plug = obj.attr(name)
    plug.set( val )
    
    return plug


def _mark(card, side):
    ''' Helper, copies the bind transform from the joint to the controllers on the given card.
    '''
    mainCtrl = card.getLeadControl(side, 'fk')
    
    controls = [mainCtrl] + [ v for k, v in mainCtrl.subControl.items()]
    joints = card.getRealJoints(side=side if side != 'center' else None)
    
    for ctrl, jnt in zip(controls, joints):
        if jnt.hasAttr('bindZero') and not pdil.math.isClose( jnt.bindZero.get(), (0, 0, 0) ):
            
            addVector(ctrl, 'bindZero', jnt.bindZero.get()).lock()
            '''
            if not ctrl.hasAttr('bindZero'):
                ctrl.addAttr( 'bindZero', at='double3' )
                ctrl.addAttr( 'bindZeroX', at='double', p='bindZero' )
                ctrl.addAttr( 'bindZeroY', at='double', p='bindZero' )
                ctrl.addAttr( 'bindZeroZ', at='double', p='bindZero' )
                
            ctrl.bindZero.set( jnt.bindZero.get() )
            
            ctrl.bindZero.lock()
            '''

        if jnt.hasAttr('bindZeroTr') and not pdil.math.isClose( jnt.bindZeroTr.get(), (0, 0, 0) ):
            
            '''
            if not ctrl.hasAttr('bindZeroTr'):
                ctrl.addAttr( 'bindZeroTr', at='double3' )
                ctrl.addAttr( 'bindZeroTrX', at='double', p='bindZeroTr' )
                ctrl.addAttr( 'bindZeroTrY', at='double', p='bindZeroTr' )
                ctrl.addAttr( 'bindZeroTrZ', at='double', p='bindZeroTr' )
                
            ctrl.bindZeroTr.set( jnt.bindZeroTr.get() )
            
            ctrl.bindZeroTr.lock()
            '''
            addVector(ctrl, 'bindZeroTr', jnt.bindZeroTr.get()).lock()


def markBindPose(cards=None):
    '''
    If any cards were build with the tpose system, mark what the bind pose is on the FK controllers.
    Operates on all cards by default but can be give a specific list.
    '''
    if not cards:
        cards = find.blueprintCards()
        
    for card in cards:
        
        if card.outputCenter.fk:
            _mark(card, 'center')
            
        elif card.outputLeft.fk:
            
            _mark(card, 'left')
            
            _mark(card, 'right')
            
            '''
            controls = [card.outputLeft.fk] + [ v for k, v in card.outputLeft.fk.subControl.items()]
            joints = card.getRealJoints(side='left')
            
            for ctrl, jnt in zip(controls, joints):
                if jnt.hasAttr('bindZero') and not core.math.isClose( jnt.bindZero.get(), (0, 0, 0) ):
                    print(ctrl, jnt)
            
            
            controls = [card.outputLeft.fk] + [ v for k, v in card.outputRight.fk.subControl.items()]
            joints = card.getRealJoints(side='right')
            '''


def backportReposition(rCard):
    ''' Creates several nodes so changes to the repose card are moved back to the original.  Requires teardown.
    '''
    
    # ??? Unsure if I need to match the pivot and maintain offset?  I probably do.
    # The pivot of the real card needs to be in relation to it's parent (I think)
    
    # ??? I probably need to clear these out when updating cards, so test that first?
    
    rGroup = group(em=True)
    pdil.dagObj.matchTo(rGroup, rCard)

    card = pdil.factory.getSingleConnection( rCard, 'bpCard' )
    cardGroup = group(em=True)
    pdil.dagObj.matchTo(cardGroup, card)

    reposeProxy = group(em=True)
    reposeProxy.setParent(rGroup)
    parentConstraint( rCard, reposeProxy )

    cardProxy = group(em=True)
    cardProxy.setParent(cardGroup)
    reposeProxy.t >> cardProxy.t
    reposeProxy.r >> cardProxy.r

    parentConstraint(cardProxy, card)
    pdil.dagObj.unlock(rCard)
    
    pdil.factory.setSingleConnection(rGroup, 'fossil_backport', rCard)
    pdil.factory.setSingleConnection(cardGroup, 'fossil_backport', rCard)


def backportRepositionTeardown(rCard):
    
    card = pdil.factory.getSingleConnection( rCard, 'bpCard' )
    delete( card.listRelatives(type='parentConstraint') )
    
    for con in rCard.listConnections(s=False, d=True, p=True):
        if con.attrName() == 'fossil_backport':
            delete( con.node() )
            
    pdil.dagObj.lock(rCard, 't')
