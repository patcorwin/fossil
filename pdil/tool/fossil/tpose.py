# Functionality so a custom tpose can be made with fk offsets to put into the bind pose

from __future__ import absolute_import, division, print_function

import contextlib

from pymel.core import delete, duplicate, joint, ls, makeIdentity, xform

from ...add import simpleName

#from . import cardlister


from ... import core


def reposerExists():
    return bool( ls('*_repose' ) )


def getRJoint(bpj):
    # Get repositioned joint from blueprint joint
    for plug in bpj.message.listConnections(s=False, d=True, p=True):
        if plug.attrName() == 'bpj':
            return plug.node()


def lockRYZ(j):
    j.ry.lock()
    j.rz.lock()


def generateReposer():
    
    rJoints = []
    rCards = []

    # Build all the cards and joints
    cards = core.findNode.allCards()
    for card in cards:
        rCard = duplicate(card, po=0)[0]
        rCard.deleteAttr('fossilRigData')
        for child in rCard.listRelatives():
            if not child.type() == 'nurbsSurface':
                delete(child)
        rCards.append(rCard)
        makeIdentity(rCard, t=False, r=False, s=True, apply=True)
        core.dagObj.lockScale( rCard )

        for jnt in card.joints:
            j = joint(None)
            j.rename(  simpleName(jnt, '{}_repose') )

            core.dagObj.matchTo(j, jnt)

            assert jnt.info.get('options', {}).get('mirroredSide', False) is False, 'parent to mirrored joints not supported yet'
            j.addAttr('bpj', at='message')
            jnt.message >> j.bpj

            rJoints.append(j)

    # Set their parents
    for j in rJoints:
        parent = j.bpj.listConnections()[0].parent
        if parent:
            j.setParent( getRJoint(parent) )

    # Put under cards, card pivot to lead joint
    for rCard, card in zip(rCards, cards):
        bpj = card.parentCardJoint
        if bpj:

            start = card.start() if card.joints else bpj
            rCard.setParent( getRJoint(bpj) )
            core.dagObj.unlock(rCard)
            xform(rCard, ws=True, piv=xform(start, q=True, t=True, ws=True) )
            core.dagObj.lockTrans(rCard)

        start = getRJoint(card.start())
        start.setParent( rCard )
        core.dagObj.lockTrans( core.dagObj.lockScale( start ) )

    for j in rJoints:
        lockRYZ(j)


@contextlib.contextmanager
def matchReposer(cards):
    relock = []
    prevPos = {}
    prevRot = {}

    for card in cards:
        reposeCard = card.name() + '1'

        prevRot[card] = card.r.get()
        rot = xform(reposeCard, q=True, ws=True, ro=True)
        xform(card, ws=True, ro=rot)
        
        for jnt in card.joints:
            repose = getRJoint(jnt)

            if repose:
                if jnt.tx.isLocked():
                    jnt.tx.unlock()
                    relock.append(jnt)

                prevPos[jnt] = jnt.t.get()

                trans = xform(repose, q=True, t=True, ws=True)
                try:
                    xform(jnt, ws=True, t=trans)
                except:
                    del prevPos[jnt]

    yield

    for jnt, pos in prevPos.items():
        try:
            jnt.t.set(pos)
        except:
            pass

    for jnt in relock:
        jnt.tx.lock()

    for card, rot in prevRot.items():
        card.r.set(rot)


def goToBindPose():
    for ctrl in core.findNode.controllers():
        if ctrl.hasAttr( 'bindZero' ):
            ctrl.r.set( ctrl.bindZero.get() )

        if ctrl.hasAttr( 'bindZeroTr' ):
            ctrl.t.set( ctrl.bindZeroTr.get() )


def _mark(card, side):
    mainCtrl = card.getKinematic(side, 'fk')
    
    controls = [mainCtrl] + [ v for k, v in mainCtrl.subControl.items()]
    joints = card.getRealJoints(side=side if side != 'center' else None)
    
    for ctrl, jnt in zip(controls, joints):
        if jnt.hasAttr('bindZero') and not core.math.isClose( jnt.bindZero.get(), (0, 0, 0) ):
            
            if not ctrl.hasAttr('bindZero'):
                ctrl.addAttr( 'bindZero', at='double3' )
                ctrl.addAttr( 'bindZeroX', at='double', p='bindZero' )
                ctrl.addAttr( 'bindZeroY', at='double', p='bindZero' )
                ctrl.addAttr( 'bindZeroZ', at='double', p='bindZero' )
                
            ctrl.bindZero.set( jnt.bindZero.get() )
            
            ctrl.bindZero.lock()

        if jnt.hasAttr('bindZeroTr') and not core.math.isClose( jnt.bindZeroTr.get(), (0, 0, 0) ):
            
            if not ctrl.hasAttr('bindZeroTr'):
                ctrl.addAttr( 'bindZeroTr', at='double3' )
                ctrl.addAttr( 'bindZeroTrX', at='double', p='bindZeroTr' )
                ctrl.addAttr( 'bindZeroTrY', at='double', p='bindZeroTr' )
                ctrl.addAttr( 'bindZeroTrZ', at='double', p='bindZeroTr' )
                
            ctrl.bindZeroTr.set( jnt.bindZeroTr.get() )
            
            ctrl.bindZeroTr.lock()


def markBindPose(cards=None):
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