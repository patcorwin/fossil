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
from copy import deepcopy
import math
import operator
import re

from pymel.core import cmds, delete, dt, duplicate, group, hasAttr, joint, listRelatives, ls, makeIdentity, move, objExists, parentConstraint, PyNode, rotate, selected, showHidden, xform

from ...add import simpleName

from . import cardlister
from . import util

from ... import core


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


def lockRYZ(j):
    ''' Lock rotate Y and Z on most repose joints so editing happens in-plane.
    '''
    
    j.ry.lock()
    j.rz.lock()


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
    
    core.math.multiply(follower.tx, -1) >> mirror.tx
    follower.ty >> mirror.ty
    follower.tz >> mirror.tz
    
    follower.rx >> mirror.rx
    core.math.multiply(follower.ry, -1) >> mirror.ry
    core.math.multiply(follower.rz, -1) >> mirror.rz
    
    parentConstraint(reposeJoint, follower, mo=False)
    parentConstraint(mirror, reposeMirror)
    reposeMirror.setParent(reposeJoint)
    
    reposeMirror.message >> reposeJoint.mirrorGroup
    
    follower.setParent(grouper)
    mirror.setParent(grouper)
    
    return reposeMirror


def generateReposer(cards=None, placeholder=False):
    ''' If no cards are specificed, a new reposer is build, otherwise it
    rebuilds/adds reposers for the specified cards.
    
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
        cards = core.findNode.allCards()
        # Delete previous roots
        for oldRoot in getReposeRoots():
            oldRoot.deleteAttr('reposeRoot')
            
    # Otherwise populate the containers with the existing reposer to build/add new stuff.
    else:
        #allExistingRCards = set( cmds.ls( '*.bpCard', o=True, r=True, l=True ) )
        allExistingRJoints = set( cmds.ls( '*.bpj', o=True, r=True, l=True ) )
        
        for oldRoot in getReposeRoots():
            #rCards.append(oldRoot)
            #rCards += oldRoot.listRelatives
            
            #children = cmds.listRelatives( str(oldRoot), f=True, ad=True, type='nurbsSurface' )
            #rCards += [PyNode(c) for c in allExistingRCards.intersection(children)]
            
            joints = cmds.listRelatives( str(oldRoot), f=True, ad=True, type='joint' )
            joints = [PyNode(c) for c in allExistingRJoints.intersection(joints)]
        
            for rj in joints:
                bpj = rj.bpj.listConnections()[0]
                jointMapping[rj] = bpj
                jointMapping[bpj] = rj

    
    for card in cards:
        rCard = duplicate(card, po=0)[0]
        showHidden(rCard)
        core.dagObj.unlock(rCard)
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
        core.dagObj.lockScale( rCard )

        for jnt in card.joints:
            reposeJoint = joint(None)
            targetName = simpleName(jnt, '{}_repose' + suffix)
            
            previous, attrs = reposeLink(jnt, reposeJoint, 'bpj') if not placeholder else (None, [])
            unlock[reposeJoint] = attrs
            renameReposeObj(reposeJoint, targetName, previous)

            core.dagObj.matchTo(reposeJoint, jnt)

            #assert jnt.info.get('options', {}).get('mirroredSide', False) is False, 'parent to mirrored joints not supported yet'
            
            jointMapping[jnt] = reposeJoint
            jointMapping[reposeJoint] = jnt

            rJoints.append(reposeJoint)
    
    # Set their parents
    for reposeJoint in rJoints:
        #parent = reposeJoint.bpj.listConnections()[0].parent
        parent = jointMapping[reposeJoint].parent
        if parent in jointMapping: # Check against joint mapping in case only a few selected cards a being tposed
            #reposeJoint.setParent( getRJoint(parent) )
            reposeJoint.setParent( jointMapping[parent] )
    
    # Put under cards, card pivot to lead joint
    for rCard, card in zip(rCards, cards):
        bpj = card.parentCardJoint
        print('BPJ - - - - ', bpj, bpj in jointMapping)
        if bpj in jointMapping:
            start = card.start() if card.joints else bpj
            #rCard.setParent( getRJoint(bpj) )
            core.dagObj.unlock(rCard)
            
            #firstBpj = card.joints[0]
            #return
            
            isMirrored = card.isCardMirrored()
            
            
            mirroredSide = card.joints[0].info.get('options', {}).get('mirroredSide')
            print('rCard.mirror', rCard.mirror, 'info:', mirroredSide)
            #if rCard.mirror is False and mirroredSide:
            if isMirrored is False and card.mirror is False and mirroredSide:
                print('opposite mirror')
                rCard.setParent( makeMirrored( jointMapping[bpj] ) )
            else:
                print('regular side stuff')
                rCard.setParent( jointMapping[bpj] )
                
            #cmds.parent(str(rCard), str(jointMapping[bpj]))
            xform(rCard, ws=True, piv=xform(start, q=True, t=True, ws=True) )
            core.dagObj.lockTrans(rCard)
            
        else:
            if not placeholder:
                rCard.addAttr('reposeRoot', at='message')

        addVector(rCard, 'origRot', rCard.r.get())
        addVector(rCard, 'origTrans', rCard.t.get())
        #start = getRJoint(card.start())
        start = jointMapping[card.start()]
        start.setParent( rCard )
        core.dagObj.lockTrans( core.dagObj.lockScale( start ) )

        if rCard in unlock:
            for attr in unlock[rCard]:
                rCard.attr(attr).unlock()
                rCard.attr(attr).showInChannelBox(True)

    for reposeJoint in rJoints:
        lockRYZ(reposeJoint)
        
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


def updateReposers(cards=None):
    ''' Remake the given cards' reposers.  This probably works to generate them properly in the first place.
    '''
    if not cards:
        cards = selected()
    
    otherCards = cardlister.cardJointBuildOrder()
    for c in cards:
        otherCards.remove(c)
        
    with reposeToBindPose(otherCards):
        generateReposer( cards )


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


@contextlib.contextmanager
def matchReposer(cards):
    ''' Temporarily puts the cards (aka bind pose) in the tpose.
    '''
    relock = []
    prevPos = {}
    prevRot = {}

    validCards = getValidReposeCards()

    for card in cards:
        reposeCard = getRCard(card, validCards)
        if not reposeCard:
            continue
            
        prevRot[card] = card.r.get()
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
                        relock.append(plug)
                #if jnt.tx.isLocked():
                #    jnt.tx.unlock()
                #    relock.append(jnt)
                    
                prevPos[jnt] = jnt.t.get()
                
                trans = xform(repose, q=True, t=True, ws=True)
                try:
                    xform(jnt, ws=True, t=trans)
                except Exception:
                    del prevPos[jnt]
                    
    yield
    
    for jnt, pos in prevPos.items():
        try:
            jnt.t.set(pos)
        except Exception:
            pass
            
    for plug in relock:
        plug.lock()
        
    for card, rot in prevRot.items():
        try:
            card.r.set(rot)
        except:
            print('UNABLE TO RETURN ROTATE', card)


def goToBindPose():
    ''' Puts the rig into the bind pose.
    '''

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


    for ctrl in core.findNode.controllers():
        if ctrl.hasAttr( 'bindZero' ):
            try:
                ctrl.r.set( ctrl.bindZero.get() )
            except:
                pass

        if ctrl.hasAttr( 'bindZeroTr' ):
            ctrl.t.set( ctrl.bindZeroTr.get() )


@contextlib.contextmanager
def controlsToBindPose():
    controls = core.findNode.controllers()
    current = {ctrl: (ctrl.t.get(), ctrl.r.get()) for ctrl in controls }

    goToBindPose()
    
    yield
    
    for ctrl, (pos, rot) in current.items():
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
    mainCtrl = card.getKinematic(side, 'fk')
    
    controls = [mainCtrl] + [ v for k, v in mainCtrl.subControl.items()]
    joints = card.getRealJoints(side=side if side != 'center' else None)
    
    for ctrl, jnt in zip(controls, joints):
        if jnt.hasAttr('bindZero') and not core.math.isClose( jnt.bindZero.get(), (0, 0, 0) ):
            
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

        if jnt.hasAttr('bindZeroTr') and not core.math.isClose( jnt.bindZeroTr.get(), (0, 0, 0) ):
            
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
        cards = core.findNode.allCards()
        
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
            

def setValueHelper(attr, objs=None, *args):
    
    from pymel.core import selected
    
    if not objs:
        objs = selected()
    
    for obj in objs:
        if not obj.hasAttr(attr):
            continue
    
        mode = 't' if 'Trans' in attr else 'r'
        
        values = obj.attr(attr).get()
        
        for axis, val in zip('xyz', values):
            try:
                obj.attr( mode + axis ).set(val)
            except Exception:
                import traceback
                print(traceback.format_exc())


def reposeAdjusterSimple():
    
    from pymel.core import deleteUI, window, columnLayout, button, showWindow
    from functools import partial
    
    if window('REPOSER_POSE_SIMPLE', ex=True):
        deleteUI('REPOSER_POSE_SIMPLE')
    
    window('REPOSER_POSE_SIMPLE')
    with columnLayout():
        for attr in [
            'origRot',
            'origTrans',
            'prevRot',
            'prevTrans',
            'prevRotWorld',
            'prevTransWorld',
        ]:
            button(l=attr, c=partial(setValueHelper, attr) )
    
    showWindow()


def reposeDeal():
    from pymel.core import window, rowColumnLayout, text, button, checkBox, showWindow, Callback, scrollLayout
    
    roots = getReposeRoots()

    allRepose = roots[:]
    for root in roots:
        allRepose += listRelatives(root, ad=True, type='transform')

    checks = {
        'origRot': [],
        'origTrans': [],
        'prevRot': [],
        'prevTrans': [],
        'prevRotWorld': [],
        'prevTransWorld': [],
    }

    attrs = {
        'origR': [ 'origRot', 'r' ],
        'origT': [ 'origTrans', 't' ],
        'prevR': [ 'prevRot', 'r' ],
        'prevT': [ 'prevTrans', 't' ],
        'prevRW': [ 'prevRotWorld', 'prevRW' ],
        'prevTW': [ 'prevTransWorld', 'prevTW' ],
    }

    def setValues(objs, checks, column):
        
        targets = [obj for obj, check in zip(objs, checks[column]) if check.getValue()]

        setValueHelper( column, targets )
        
        '''
        print(targets)
        for target in targets:
            print(target)
            if column == 'origR':
                target.r.set( target.origR.get() )
            elif column == 'origT':
                target.t.set( target.origTrans.get() )
                
            elif column == 'prevR':
                target.r.set( target.prevRot.get() )
            elif column == 'prevT':
                target.t.set( target.prevTrans.get() )
                
            else:
                raise Exception('IMPELEMNT WORLKD')
        '''

    window()
    with scrollLayout():
        with rowColumnLayout(nc=7):
            text(l='')

            button(l='origR', c=Callback( setValues, allRepose, checks, 'origRot') )
            button(l='origT', c=Callback( setValues, allRepose, checks, 'origTrans') )

            button(l='prevR', c=Callback( setValues, allRepose, checks, 'prevRot') )
            button(l='prevT', c=Callback( setValues, allRepose, checks, 'prevTrans') )

            button(l='prevRW', c=Callback( setValues, allRepose, checks, 'prevRW') )
            button(l='prevTW', c=Callback( setValues, allRepose, checks, 'prevTW') )
            
            for obj in allRepose:
                text(l=obj.name())
                checks['origRot'].append( checkBox(l='') )
                checks['origTrans'].append( checkBox(l='') )
                
                checks['prevRot'].append( checkBox(l='', v=not obj.origRot.get() == obj.prevRot.get() ) )
                checks['prevTrans'].append( checkBox(l='', v=not obj.origTrans.get() == obj.prevTrans.get() ) )

                checks['prevRotWorld'].append( checkBox(l='') )
                checks['prevTransWorld'].append( checkBox(l='') )

    showWindow()

            
def reposeAdjuster():
    
    roots = getReposeRoots()

    #cards = listRelatives(r[1], ad=True, type='nurbsSurface')
    joints = {}

    entries = []
    for root in roots:
        
        entries.append( [0, [root] ] )
        
        def children(n, depth=1, card=None):
            for x in listRelatives(n, type='transform'):
                if x.type() != 'joint':
                    
                    if entries[-1][0] == depth:
                        entries[-1][1].append( x )
                    else:
                        entries.append( [depth, [x]] )
                    #print( '   ' * depth + str(x) )
                    
                    children(x, depth + 1, x)
                else:
                    joints.setdefault(card, []).append( x )
                    
                    children(x, depth, card)

        children(root, card=root)
    
    from pymel.core import window, columnLayout, button, rowLayout, text, showWindow, deleteUI, PyNode, frameLayout, scrollLayout
    from functools import partial
    
    if window('REPOSER_POSE', ex=True):
        deleteUI('REPOSER_POSE')
    
    def setRot(obj, r, *args):
        obj = PyNode(obj)
        for axis, val in zip('xyz', r):
            try:
                obj.attr( 'r' + axis ).set(val)
            except Exception:
                pass
    
    def setTrans(obj, t, *args):
        obj = PyNode(obj)
        for axis, val in zip('xyz', t):
            try:
                obj.attr( 't' + axis ).set(val)
            except Exception:
                pass
    
    window('REPOSER_POSE')
    scrollLayout()
    with columnLayout():
        
        for depth, nodes in entries:
            for n in nodes:
                #print( '   ' * depth + str(n) )
                with rowLayout(nc=3 if depth else 4):
                    text(l=(' ' * 8) * depth)
                    text(l=str(n))
                    
                    button(l='Rot', c=partial(setRot, n.name(), n.r.get()) )
                    if depth == 0:
                        button(l='Trans', c=partial(setTrans, n.name(), n.t.get()) )
                
                if n in joints:
                    with frameLayout(cll=True, cl=True, l=''):
                        with columnLayout():
                            for j in joints[n]:
                                button(l=str(j), c=partial(setRot, j.name(), j.r.get()) )
                        
    
    showWindow()
    
    for c, js in joints.items():
        print( c, '---------------' )
        print( '\n'.join( [str(j) for j in js] ) )
    
    #for x in entries:
    #    print( x )
    
    
# -----------------------------------------------------------------------------
# Alignment stuff

'''
pdil.tool.fossil.tpose.armAlign( PyNode('Shoulder_card') )
pdil.tool.fossil.tpose.wristAlign( PyNode('Shoulder_card').joints[2] )

pdil.tool.fossil.tpose.fingerAlign( PyNode('Index01_L_bpj') )
pdil.tool.fossil.tpose.fingerAlign( PyNode('Middle02_L_bpj') )
pdil.tool.fossil.tpose.fingerAlign( PyNode('Pinky02_L_bpj') )

pdil.tool.fossil.tpose.footAlign( PyNode('Ball_L_bpj') )

pdil.tool.fossil.tpose.pelvisAlign( PyNode('Pelvis_bpj'), PyNode('Ball_L_bpj'))

pdil.tool.fossil.tpose.spineAlign( PyNode('Spine_card'), 20)


with o.rigData as rigData:
    rigData['tpose'] = [{
        'order': 0,
        'call': 'spineAlign',
        'args': ['self', 20]
    }]

with o.rigData as rigData:
    rigData['tpose'] = [{
        'order': 10,
        'call': 'armAlign',
        'args': ['self']
    },
    {
        'order': 20,
        'call': 'wristAlign',
        'args': ['self.joints[2]']
    }]
    
with o.rigData as rigData:
    rigData['tpose'] = [{
        'order': 30,
        'call': 'fingerAlign',
        'args': ['self.joints[0]']
    }]
with o.rigData as rigData:
    rigData['tpose'] = [{
        'order': 40,
        'call': 'fingerAlign',
        'args': ['self.joints[0]']
    }]
with o.rigData as rigData:
    rigData['tpose'] = [{
        'order': 50,
        'call': 'fingerAlign',
        'args': ['self.joints[0]']
    }]
    
with o.rigData as rigData:
    rigData['id'] = 'leg'
    rigData['tpose'] = [{
        'order': 60,
        'call': 'legAlign',
        'args': ['self']
    },
    {
        'order': 70,
        'call': 'footAlign',
        'args': ['self.joints[2]']
    }]
    

with o.rigData as rigData:
    rigData['tpose'] = [{
        'order': 8,
        'call': 'pelvisAlign',
        'args': ['self', 'id:leg.joints[2]' ]
    }]



'''

def getCardParent(rJoint):
    ''' Returns the parent reposeCard, skipping the auto-created 'transform#'
    
    When ancestors are scaled, they can create intermediate transforms that need
    to be ignored.
    '''
    p = rJoint.getParent()
    if p.hasAttr('bpParent'):
        return p
    else:
        return p.getParent()


def armAlign(shoulderCard):
    ''' Rotates the lead joint to point down the +X axis, and the other joints
    to be almost straight, with a slight bend pointing behind, -Z.
    '''
    shoulderJoint = shoulderCard.joints[0]
    
    shoulderRepose = getRJoint(shoulderJoint)
    
    xform( getCardParent(shoulderRepose), ws=True, ro=[0, 0, 90] )
    
    out = core.dagObj.getPos( getRJoint(shoulderCard.joints[1]) ) - core.dagObj.getPos( getRJoint(shoulderCard.joints[0]) )
    toRotate = math.degrees( out.angle( (1, 0, 0) ) )
    rotate(shoulderRepose, [0, -toRotate + 2, 0 ], ws=True, r=True)

    elbowRepose = getRJoint(shoulderCard.joints[1])
    out = core.dagObj.getPos( getRJoint(shoulderCard.joints[2]) ) - core.dagObj.getPos( getRJoint(shoulderCard.joints[1]) )
    toRotate = math.degrees( out.angle( (1, 0, 0) ) )
    rotate(elbowRepose, [0, toRotate - 2, 0 ], ws=True, r=True)


def wristAlign( wristJoint ):
    '''
    Assumptions, aiming down +x
    '''
    rotatingJoint = getRJoint(wristJoint)
    rotatingJoint.ry.unlock()
    rotatingJoint.rz.unlock()
    
    targetJoint = getRJoint( wristJoint.orientTarget )
    targetCard = getCardParent(targetJoint)

    aim = core.dagObj.getPos(targetJoint) - core.dagObj.getPos(rotatingJoint)

    rotate(rotatingJoint, [0, math.degrees( math.atan( aim.z / aim.x ) ), 0], ws=True, r=True )

    rotate(rotatingJoint, [0, 0, -math.degrees(math.atan(aim.y / aim.x))], ws=True, r=True )

    m = xform(targetCard, q=True, ws=True, m=True)
    rotate(rotatingJoint, [ -math.degrees( math.atan( m[2] / m[1] ) )  ], ws=True, r=True)
    

def legAlign(legCard):
    xform( getCardParent(getRJoint(legCard.joints[0])), ws=True, ro=[0, 0, 0] )


def footAlign( endJoint ):
    '''
    Assumptions, aim down +Z
    '''
    rotatingJoint = getRJoint(endJoint)
    rotatingJoint.ry.unlock()
    rotatingJoint.rz.unlock()
    
    targetJoint = getRJoint( endJoint.orientTarget )
    targetCard = getCardParent(targetJoint)

    aim = core.dagObj.getPos(targetJoint) - core.dagObj.getPos(rotatingJoint)

    rotate(rotatingJoint, [0, -math.degrees( math.atan( aim.x / aim.z ) ), 0], ws=True, r=True )

    rotate(rotatingJoint, [math.degrees(math.atan(aim.y / aim.z)), 0, 0], ws=True, r=True )


    m = xform(targetCard, q=True, ws=True, m=True)
    rotate(rotatingJoint, [0, 0, -math.degrees( math.atan( m[1] / m[0] ) )], ws=True, r=True)
    
    
def fingerAlign( baseJoint ):
    
    fingerCardRepose = getCardParent(getRJoint(baseJoint))
    
    xform( fingerCardRepose, ws=True, ro=[90, 90, 180] )
    
    reposes = [getRJoint(j) for j in baseJoint.card.joints]
    
    for jointA, jointB in zip(reposes, reposes[1:]):
        bPos = core.dagObj.getPos( jointB )
        aPos = core.dagObj.getPos( jointA )
        out = bPos - aPos
        toRotate = math.degrees( out.angle( (1, 0, 0) ) )
        
        if aPos.y < bPos.y:
            toRotate *= -1
        
        rotate(jointA, [0, 0, toRotate ], ws=True, r=True)
    
    
def pelvisAlign( pelvisCard, referenceJoint ):
    pelvisCardRepose = getRCard( pelvisCard )
    delta = core.dagObj.getPos( referenceJoint ) - core.dagObj.getPos( getRJoint(referenceJoint) )
    move(pelvisCardRepose, [0, delta.y, 0], ws=True, r=True)
    
    
def spineAlign( spineCard, rotation, threshold=6 ):
    ''' Rotates the joints of `spineCard` cumulatively to `rotation`, which is spread out proportionally.
    
    Joints less than `threshold` from the up axis are not considered.
    '''
    up = dt.Vector(0, 1, 0)
    
    spineEnd = spineCard.joints[-1] # &&& This should validate the end joint is real and not a helper
    childrenOfSpineCards = [getRJoint(bpj).getParent() for bpj in spineEnd.proxyChildren]
    preserve = { card: core.dagObj.getRot(card) for card in childrenOfSpineCards }
    
    # Get the positions of the spine joints AND the next joint, since that determines the rotation of the final spine
    reposeJoints = [getRJoint(j) for j in spineCard.joints ]
    pos = [core.dagObj.getPos( rj ) for rj in reposeJoints ]
    
    nextJoint = spineEnd.getOrientStateNEW()
    if nextJoint.joint:
        pos.append( core.dagObj.getPos( getRJoint(nextJoint.joint) ) )
    
    angles = [ math.degrees((child - cur).angle( up ))
                for cur, child in zip( pos, pos[1:] ) ]
    
    currentRotations = [core.dagObj.getRot( rj ) for rj in reposeJoints]
    
    adjust = [ (i, angle) for i, angle in enumerate(angles) if angle > threshold ]
    total = sum( (angle for _, angle in adjust ) )
        
    for i, angle in adjust:
        currentRotations[i].x -= rotation * ( angle / total )
        xform(reposeJoints[i], ws=True, ro=currentRotations[i] )
    
    
    for bpj, rot in preserve.items():
        xform(bpj, ws=True, ro=rot)


# It's cheesy to cache parents globally, but for now better than an overly complicated
# system to pass this data around
if '_falseParentCache' not in globals():
    _falseParentCache = {}

def falseParentSetupAlign(card, bpj):
    ''' Temporarily parent the rCard under the rJoint so it inherits any modifications.
    '''
    global _falseParentCache
    rCard = getRCard(card)
    rJoint = getRJoint(bpj)

    _falseParentCache[rCard] = rCard.getParent()

    rCard.setParent(rJoint)


def falseParentTeardownAlign(card, bpj):
    ''' Temporarily parent the rCard under the rJoint so it inherits any modifications.
    '''
    global _falseParentCache
    rCard = getRCard(card)
    
    rCard.setParent(_falseParentCache[rCard])

        
alignCommands = {
    'armAlign': armAlign,
    'wristAlign': wristAlign,
    'legAlign': legAlign,
    'footAlign': footAlign,
    'fingerAlign': fingerAlign,
    'pelvisAlign': pelvisAlign,
    'spineAlign': spineAlign,
    'falseParentSetupAlign': falseParentSetupAlign,
    'falseParentTeardownAlign': falseParentTeardownAlign,
}

def runAdjusters():

    adjustments = []
    
    followup = []
    
    for card in core.findNode.allCards():
        temp = card.rigData.get('tpose', [])
        for t in temp:
            t['card'] = card
            if t['call'] == 'falseParentSetupAlign':
                teardown = deepcopy(t)
                teardown['call'] = 'falseParentTeardownAlign'
                followup.append( teardown )
            
        adjustments += temp
    
    adjustments.sort( key=operator.itemgetter('order') )
    
    adjustments += followup
    
    for adjust in adjustments:
        try:
            applyTposeAdjust( adjust )
        except Exception:
            print('ERROR ADJUSTING', adjust['order'], adjust['call'])
            raise


adjusterInputRE = re.compile(r'((?P<self>self)|(id:(?P<id>[a-zA-Z]+)))(\.joints\[(?P<joint>\d+)\])?')


def applyTposeAdjust(adjust):
    cmd = alignCommands[ adjust['call'] ]
    
    card = adjust['card']
    
    converted = []
    for arg in adjust['args']:
        if isinstance(arg, basestring):
            result = adjusterInputRE.match(arg).groupdict()
            
            targetCard = card if result['self'] else util.FIND(None, cardId=result['id'])
            jointIndex = int(result['joint']) if result['joint'] else None
            
            if jointIndex is None:
                converted.append( targetCard )
            else:
                converted.append( targetCard.joints[ jointIndex ] )
        else:
            converted.append(arg)

    cmd( *converted )