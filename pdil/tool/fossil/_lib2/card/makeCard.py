'''

'''
import os

import math

from maya.api import OpenMaya
from pymel.core import createNode, PyNode, xform, rotate, nurbsPlane, polyCylinder, scale, delete, makeIdentity, joint, hide, pointConstraint, group, parentConstraint, aimConstraint, warning, dt, confirmDialog, duplicate, ls, importFile, mel, spaceLocator, distanceDimension, select


import pdil

from ..._core import find
from ..._core import config
from ..._lib import proxyskel
from . import moveCard
from ... import enums
from ... import util


try:
    basestring
except NameError: # python 3 compatibility
    basestring = str


def addOutputControlsAttrs(obj):
    _addOutputControls(obj, "Center")
    _addOutputControls(obj, "Left")
    _addOutputControls(obj, "Right")


def _addOutputControls(obj, side):
    '''
    Adds attributes to card for tracking the created controls.  Used in conjunction
    with OutputControls.
    
    :param PyNode obj: The card to add attributes to
    :param str side: Either "Left", "Right" or "Center"
    '''
    if obj.hasAttr('output' + side):
        return

    mobj = pdil.capi.asMObject(obj)
    cattr = OpenMaya.MFnCompoundAttribute()
    mattr = OpenMaya.MFnMessageAttribute()
    nattr = OpenMaya.MFnNumericAttribute()
    
    extraNodes = cattr.create('output' + side, 'out' + side[0])
    cattr.array = True

    link = mattr.create( 'outputLink' + side, 'ol' + side[0] )
    type = nattr.create('out' + side + 'Type', 'o' + side[0] + 't', OpenMaya.MFnNumericData.kInt, 0)
    
    cattr.addChild(link)
    cattr.addChild(type)

    mobj.addAttribute(extraNodes)


def addJointArrayAttr(obj):
    '''
    .. todo:: Eventually this should be abstracted.
    '''
    
    mobj = pdil.capi.asMObject( obj )

    cAttr = OpenMaya.MFnCompoundAttribute()
    mList = cAttr.create( 'joints', 'jnts' )
    cAttr.array = True

    mAttr = OpenMaya.MFnMessageAttribute()
    jMsg = mAttr.create( 'jmsg', 'jmsg' )

    cAttr.addChild( jMsg )

    mobj.addAttribute( mList )


def placeJoints(card, positions):
    '''
    Takes a list of x,y and positions the joints.  The center is (0,0) and
    extends to 1,1 and -1,-1
    '''
    width, height = card.size
    wMod = width / 2.0
    hMod = height / 2.0
    for pos, jnt in zip( positions, card.joints ):
        jnt.tz.set( -wMod * pos[0] )
        jnt.ty.set( hMod * pos[1] )
    
    if hasattr(card, 'center') and not card.center:
        pass
    else:
        card.pivToStart()


def makeArrow():
    '''
    Creates an arrow, with the base vert of 60 and tip of 60.
    '''
    arrow = polyCylinder( r=1, h=10, sx=20, sy=2, sz=1, ax=[0, 1, 0] )[0]
    scale( arrow.vtx[40:59], [1.75, 0, 1.75] )
    arrow.ty.set( 5 )
    makeIdentity(arrow, apply=True, t=True, r=True, s=True, n=False)
    xform(arrow, piv=(0, 0, 0), ws=True)
    delete( arrow, ch=True )
        
    jnt = joint(None)
    jnt.drawStyle.set( 2 )
    arrow.getShape().setParent( jnt, add=True, shape=True )
    delete( arrow )
    
    return jnt


def pivTo(card, x, y):
    ''' Move the pivot to the point in the same, x,y coords
    '''
    width, height = card.size
    wMod = width / 2.0
    hMod = height / 2.0
    
    piv = xform(card, q=True, ws=True, t=True)
    
    xform( card, ws=True, piv=[0, piv[1] + hMod * y, piv[2] - wMod * x  ] )


def pivToStart(card):
    ''' Move the pivot to the start joint.
    '''
    
    piv = xform(card.start(), q=True, ws=True, piv=True)
    xform( card, ws=True, piv=piv[:3])


def makeCard(jointCount=5, jointNames={'repeat': 'DEFAULT'}, rigInfo=None, size=(4, 6), suffix='', parent=None):
    '''
    ..  todo:: Do not use defaults.  &&& Not sure what I meant by this, maybe pull all defaults to require names?
    rigInfo is unused, can it be pulled?  Suffix might also need pulling after
    the `one correct way` to assign sides is figured out.
    '''
    if isinstance(jointNames, basestring):
        head, repeat, tail = util.parse(jointNames)
        jointNames = {'head': head, 'repeat': repeat, 'tail': tail}
        
    elif isinstance(jointNames, list):
        jointNames = {'head': jointNames}
    
    leadName = jointNames.get('head')[0] if jointNames.get('head') else jointNames.get('repeat', 'DEFAULT')
    
    joints = []
    width, height = size
    
    # Base the card name off the lead joint
    cardName = leadName
    
    if not isinstance( cardName, basestring ):
        cardName = cardName[0]
        #jointNames = ' '.join(jointNames)
    
    if not cardName.endswith('_card'):
        if cardName.endswith('_'):
            cardName += 'card'
        else:
            cardName += '_card'
    
    # Make the actual card and tag with attrs
    card = nurbsPlane(w=width, lr=height / float(width), ax=(1, 0, 0), n=cardName, d=1, u=1, v=1 )[0]
    
    card.addAttr( 'fossilRigData', dt='string' )
    card.addAttr( 'fossilRigState', dt='string' )
    
    addOutputControlsAttrs(card)
    addJointArrayAttr(card)
    
    # Reassign it so it gets the proper interface now that it has the attrs
    card = PyNode(card)
    
    rigData = {
        'buildOrder': 10,
        'mirrorCode': suffix,
        'nameInfo': jointNames,
    }
    
    card.rigData = rigData
    
    arrow = makeArrow()
    arrow.setParent( card )
    arrow.rename('arrow')
    card.scale >> arrow.inverseScale
    
    arrow.t.set(0, 0, 0)
    arrow.r.set(0, 0, -90)
    hide(arrow)
    card.setParent( proxyskel.masterGroup() )

    # Place all the joints

    delta = height / float(jointCount - 1) if jointCount > 1 else 0
    
    for i in range(jointCount):
        newJoint = card.addJoint()
        joints.append(newJoint)
        newJoint.ty.set( height / 2.0 - delta * i )
        
    if len(joints) > 1:
        for parentBpj, childBpj in zip( joints[0:-1], joints[1:] ):
            proxyskel.pointer( parentBpj, childBpj )
    elif joints:
        proxyskel.makeProxy(joints[0], proxyskel.getProxyGroup())
        joints[0].ty.set(0)
    
    if joints:
        card.setTempNames()
        
        pivToStart(card)
    
    if parent:
        card.joints[0].setBPParent(parent)
        
        # Set to matching joint radius as convenience
        radius = parent.radius.get()
        for j in card.joints:
            j.radius.set(radius)
            j.proxy.radius.set(radius)
    
    pdil.pubsub.publish('fossil card added', card)
    
    return card


def nextLetter(c):
    # Naively increment the letter, ex  B -> C, or  M -> N.
    if not c:
        return 'A'
    
    return chr(ord(c) + 1)


def findUniqueNameInfo(nameScheme, alteration, cards=None):
    scheme = (nameScheme[0], nameScheme[1] + alteration, nameScheme[2])
    for c in cards:
        if util.parse(c.nameInfo.get()) == scheme:
            return findUniqueNameInfo(nameScheme, nextLetter(alteration), cards=cards)
    else:
        return scheme


class Orientation:
    VERTICAL = 'vertical'
    HORIZONTAL = 'horizontal'


def splitCard(tempJoint):
    '''
    Everything after and including the given joint will become a new card.
    '''
    oldCard = tempJoint.cardCon.node()
    if oldCard.start() == tempJoint:
        warning( 'Cannot split at the first joint' )
        return
    
    card = makeCard(jointCount=0, size=(1, 1))
    newCvs = list(card.cv)
    newCvs = [newCvs[0], newCvs[2], newCvs[1], newCvs[3]]

    points = [ dt.Vector(xform(v, q=True, ws=True, t=True)) for v in oldCard.cv ]
    points = [points[0], points[2], points[1], points[3]]  # vtx and points must be rearranged in the same way
    vtx = list(oldCard.cv)
    vtx = [vtx[0], vtx[2], vtx[1], vtx[3]]
    
    midA = (points[0] - points[2]) / 2.0 + points[2]
    midB = (points[1] - points[3]) / 2.0 + points[3]
    
    xform( vtx[0], ws=True, t=midA )
    xform( vtx[1], ws=True, t=midB )
        
    card.setParent( oldCard.getParent() )
    card.t.set( oldCard.t.get() )
    card.r.set( oldCard.r.get() )
    card.s.set( oldCard.s.get() )
    
    xform( newCvs[0], ws=True, t=points[0] )
    xform( newCvs[1], ws=True, t=points[1] )
    xform( newCvs[2], ws=True, t=midA )
    xform( newCvs[3], ws=True, t=midB )
    
    start, repeat, end = util.parse( oldCard.nameInfo.get())
    
    index = oldCard.joints.index(tempJoint)
    
    if index == len(start):
        # New card is repeat + end
        oldCard.nameInfo.set( ' '.join(start) )
        card.nameInfo.set( repeat + '* ' + ' '.join(end) )

    elif index == len(oldCard.joints) - len(end):
        oldCard.nameInfo.set( ' '.join(start) + ' ' + repeat + '*' )
        card.nameInfo.set( ' '.join(end) )
    else:
        # Terrible split!
        oldCard.nameInfo.set( ' '.join(start) + ' ' + repeat + '*' )
        card.nameInfo.set( repeat + 'X* ' + ' '.join(end) )
        confirmDialog(m="You are splitting in the repeating Zone, you'll want to fix up names\nAn 'X' has been added to the new cards repeating section")
    
    card.rename( card.nameInfo.get() )
    oldCard.rename( oldCard.nameInfo.get() )
    
    # Move the appropriate joints to the new card.
    for j in oldCard.joints[index: ]:
        prevConnection = j.message.listConnections(type=card.__class__, p=1)
        j.message.disconnect( prevConnection[0] )
        
        # Not sure why position is lost but I'm not sure it really matters
        pos = xform(j, q=True, ws=True, t=True)
        card.addJoint(j)
        xform(j, ws=True, t=pos)
    
    # Update .parentCard
    movedJoints = set( card.joints )
    for childCard in card.childrenCards:
        for j in childCard.joints:
            if j.parent in movedJoints:
                childCard.parentCardLink = card
                continue
    
    # There might be a way to deal with moving controls, but the fact a split happend indicates they will be rebuilt.

    
def mirrorCard(card):
    dup = duplicateCard(card)
    
    mult = pdil.math.multiply( [card.tx, card.ry, card.rz], [-1, -1, -1])
    mult >> dup.tx
    
    card.rx >> dup.rx
    mult.node().outputY >> dup.ry
    mult.node().outputZ >> dup.rz
    
    card.ty >> dup.ty
    card.tz >> dup.tz


def duplicateCard(card):
    d = duplicate( card )[0]
    proxyskel.relink( card, d )
    if card.parentCard:
        d.parentCardLink = card.parentCard
    return d


def getArrows():
    return ls( 'arrow' )


def getConnectors():
    '''
    #-# I *think* the idea is to toggle the proxy connector display but I'm not certain
    I also don't think this is useful.  Maybe it was when I didn't have the connectors autohide with the card.
    '''
    #cards = ls( '*.skeletonInfo', o=1 )
    for card in find.blueprintCards():
        for j in card.joints:
            if not j.parent:
                return j.proxy


def customUp(jnt, arrow=None):

    if not arrow:
        arrow = makeArrow()
        arrow.setParent( jnt.getParent() )
        arrow.rename( 'custom_arrow' )
        pdil.dagObj.moveTo( arrow, jnt )
    
    PyNode(jnt).customUp = arrow
    return arrow
        

def customOrient(bpJoint):
    newNodes = importFile( os.path.dirname(__file__) + '/Axis.ma', rnn=True, renameAll=True )
    transform = ls(newNodes, type='transform')[0]
    masterGroup = proxyskel.masterGroup()
    for child in masterGroup.listRelatives():
        if child.name() == 'customOrients':
            customGroup = child
            break
    else:
        customGroup = group(n='customOrients', p=masterGroup, em=True)
    
    transform.setParent(customGroup)
    transform.scale.set(3, 3, 3)
    
    transform.t.setKeyable(False)
    bpJoint.customOrient = transform
    pointConstraint(bpJoint, transform)
    transform.t.lock()
    
    transform.rename( pdil.simpleName(bpJoint, 'orient_{0}') )


def tempWidget():
    ctrl = PyNode(mel.eval('curve -d 1 -p 0 4 0 -p -2.828427 2.828427 -2.47269e-007 -p -4 0 -3.49691e-007 -p -2.828427 -2.828427 -2.47269e-007 -p 0 -4 0 -p 2.828427 -2.828427 0 -p 4 0 0 -p 2.828427 2.828427 0 -p 0 4 0 -p -1.23634e-007 2.828427 2.828427 -p -1.74846e-007 0 4 -p -1.23634e-007 -2.828427 2.828427 -p 0 -4 0 -p 3.70903e-007 -2.828427 -2.828427 -p 5.24537e-007 0 -4 -p 3.70903e-007 2.828427 -2.828427 -p 0 4 0 -p 0 0 0 -p 0 -4 0 -p 0 0 0 -p -4 0 0 -p 4 0 0 -p 0 0 -4 -p 0 0 4 -k 0 -k 1 -k 2 -k 3 -k 4 -k 5 -k 6 -k 7 -k 8 -k 9 -k 10 -k 11 -k 12 -k 13 -k 14 -k 15 -k 16 -k 17 -k 18 -k 19 -k 20 -k 21 -k 22 -k 23 ;'))
    return ctrl


def directPlacementMode(card):
    
    assert len(card.joints) == 3

    grp = group(em=True, n='DirectPlacement_Deletable')

    ctrls = []
    for bpj in card.joints:
        ctrl = tempWidget()
        pdil.dagObj.matchTo(ctrl, bpj)
        ctrls.append(ctrl)
        ctrl.setParent(grp)
        
    base, up, aim = ctrls

    aimLoc = spaceLocator()
    aimLoc.setParent(aim)
    aimLoc.t.set(0, 0, 0)
    
    baseLoc = spaceLocator()
    baseLoc.setParent(base)
    baseLoc.t.set(0, 0, 0)
    
    dist = distanceDimension( baseLoc, aimLoc )
    dist.getParent().setParent(grp)
    hide(dist)
    
    
    pointConstraint( base, card, mo=True )
    
    aimConstraint( aim, card, wut='object', wuo=up, aim=[0, -1, 0], u=[0, 0, -1], mo=True)
    
    # save base dimension
    # current dimesion / base dimension
    # multiply x, z by card's existing scale
    
    dist.addAttr('baseDist', at='double', dv=dist.distance.get())
    
    scaled = pdil.math.divide( dist.distance, dist.baseDist )
    
    mult = createNode( 'multiplyDivide' )
    
    scaled >> mult.input1X
    scaled >> mult.input1Y
    scaled >> mult.input1Z
    
    mult.input2Y.set( card.sy.get() )
    mult.input2Z.set( card.sz.get() )
    
    mult.outputY >> card.sy
    mult.outputZ >> card.sz

    pointConstraint(up, card.joints[1], sk='x' )


def cardIk(card):

    #ctrl = mel.eval( 'curve -d 1 -p -0.5 1 -0.866026 -p -0.5 1 0.866025 -p 1 1 0 -p -0.5 1 -0.866026 -p 0 0 0 -p -0.5 -1 -0.866026 -p -0.5 -1 0.866025 -p 0 0 0 -p -0.5 1 0.866025 -p 1 1 0 -p 0 0 0 -p 1 -1 0 -p -0.5 -1 -0.866026 -p -0.5 -1 0.866025 -p 1 -1 0 -k 0 -k 1 -k 2 -k 3 -k 4 -k 5 -k 6 -k 7 -k 8 -k 9 -k 10 -k 11 -k 12 -k 13 -k 14 ;' )

    ctrl = tempWidget()

    ctrl.rename( card.name() + "_target" )
    
    upCtrl = duplicate(ctrl)[0]
    upCtrl.rename( card.name() + "_up" )
    
    aim = spaceLocator()
    aim.setParent(ctrl)
    aim.t.set(0, 0, 0)
    hide(aim)
    
    up = spaceLocator()
    up.setParent( upCtrl )
    hide(up)
    
    base = spaceLocator()
    base.rename( 'cardIkBase' )
    hide(base)
    pointConstraint( card, base )

    pdil.dagObj.moveTo( ctrl, card.joints[-1] )
    #pdil.dagObj.moveTo( upCtrl, card.vtx[1] )
    pdil.dagObj.moveTo( upCtrl, card.cv[1][0] )

    aimConstraint( aim, card, wut='object', wuo=up, aim=[0, -1, 0], u=[0, 0, -1])

    dist = distanceDimension( base, aim )
    dist.getParent().setParent(ctrl)
    hide(dist)

    pdil.math.divide( dist.distance, dist.distance.get() / card.sy.get() ) >> card.sy
        
    follower = spaceLocator()
    follower.rename( 'cardIkFollower' )
    follower.setParent( card )
    follower.t.set(0, 0, 0)
    hide(follower)
    
    pointConstraint( up, follower, skip=['x', 'z'] )
    
    sideDist = distanceDimension( follower, up )
    sideDist.getParent().setParent(ctrl)
    hide(sideDist)

    pdil.math.divide( sideDist.distance, sideDist.distance.get() / card.sz.get() ) >> card.sz
    
    # Orient controls with the card so moving in local space initially preserves orientation.
    upCtrl.setRotation( card.getRotation(space='world'), space='world' )
    ctrl.setRotation( card.getRotation(space='world'), space='world' )

    distBetweenCtrls = (ctrl.getTranslation(space='world') - upCtrl.getTranslation(space='world') ).length()
    if distBetweenCtrls < 8.0:
        upCtrl.s.set( [distBetweenCtrls / 8.0] * 3 )
        ctrl.s.set( [distBetweenCtrls / 8.0] * 3 )
    
    select(ctrl)


def removeCardIk(card):
    aimNode = card.rx.listConnections()
    if not aimNode:
        return
        
    card.rx.disconnect()
    card.ry.disconnect()
    card.rz.disconnect()
    
    card.sy.disconnect()
    card.sz.disconnect()
        
    aim = aimConstraint( aimNode, q=True, tl=True )[0]
    up = aimConstraint( aimNode, q=True, wuo=True )
    
    aimCtrl = aim.getParent()
    upCtrl = up.getParent()
    
    scaleA, scaleB = aimCtrl.listRelatives(ad=1, type='distanceDimShape')
    
    delete(
        scaleA.startPoint.listConnections()[0],
        scaleB.startPoint.listConnections()[0],
        aimCtrl,
        upCtrl )
    

def reconnectRealBones():
    '''
    If the cards lose their connection to the bones, run this to reconnect them.
    
    ..  todo::
        * I don't think there is anything actually preventing a helper from
            being the child of another helper.  Either fix that or account for it here
            
    '''
    failures = []

    for card in find.blueprintCards():
        for jnt, names in card.getOutputMap(includeHelpers=True).items():
            if names[0]:
                realJoint = ls(names[0])
                if len(realJoint) == 1:
                    jnt.real = realJoint[0]
                else:
                    failures.append( jnt )
            
            if len(names) > 1:
                realJoint = ls(names[1])
                if len(realJoint) == 1:
                    jnt.realMirror == realJoint[0]
                else:
                    failures.append( jnt )

                    
    return failures


# Basic cards -----------------------------------------------------------------
#-# How can I turn this into a data driven thing?
'''
I think I want to the user to be able to select cards and save them as a "preset"
- Save .rigInfo
- Save the offset from the joint it is connected to

Is this it?  It looks so simple!
'''


def spineCard(spineCount, orientation=Orientation.VERTICAL, isStart=True):
    '''
    Makes a spine with a Pelvis as the core joint and sub joints of the spine
    and hips occupying the same space.
    '''
    hasHips = True
    hasPelvis = True
            
    spine = makeCard( spineCount, 'Spine*', size=pdil.meters([0.5, 1]) )
    with spine.rigData as data:
        data[enums.RigData.rigCmd] = 'TranslateChain'
        
    util.annotateSelectionHandle( spine.joints[0], 'Spine Start', (0, -2, 0) )
    
    if hasPelvis:
        pelvis = makeCard( 1, 'Pelvis', size=pdil.meters([0.2, 0.2]) )
        pelvis.fkControllerOptions = '-shape band -size 20 -color blue .65'
        pelvis.start().orientTarget = '-world-'
        pelvis.rz.set(90)
        pelvis.start().t.lock()
        moveCard.toObjByCenter( pelvis, spine.start() )
        with pelvis.rigData as data:
            data[enums.RigData.rigCmd] = 'TranslateChain'
        #proxyskel.pointer( pelvis.start(), spine.start())
        spine.start().setBPParent( pelvis.start() )
        pointConstraint( spine.start(), pelvis)
        util.annotateSelectionHandle( pelvis.start(), 'Pelvis (top joint)', (0, 0, -2) )
    
    if hasHips:
        hips = makeCard( 1, 'Hips', size=pdil.meters([0.2, 0.2]) )
        hips.fkControllerOptions = '-shape band -size 15 -color red .65'
        hips.start().orientTarget = '-world-'
        hips.ry.set(-90)
        hips.start().t.lock()
        moveCard.toObjByCenter( hips, spine.start() )
        with hips.rigData as data:
            data[enums.RigData.rigCmd] = 'TranslateChain'
        #proxyskel.pointer( pelvis.start(), hips.start() )
        hips.start().setBPParent( pelvis.start() )
        pointConstraint( spine.start(), hips)
        util.annotateSelectionHandle( hips.start(), 'Hips', (0, -2, 0) )
    
    if orientation == Orientation.VERTICAL:
        spine.rx.set( 180 )
    else:
        spine.rx.set( -90 )
    
    moveCard.up( spine, pdil.meters(0.5) )
    #spine.buildOrder.set( 0 )  # Probably not needed since (when?) proper build order is enforced

    if isStart:
        if hasPelvis:
            pelvis.start().proxy.setParent( proxyskel.getProxyGroup() )
        else:
            spine.start().proxy.setParent( proxyskel.getProxyGroup() )
    
    return spine, hips


def arm(clav, side):
    leftArm = makeCard( 3, ['Shoulder', 'Elbow', 'Wrist'], size=pdil.meters([.2, 1]), suffix=side )
    with leftArm.rigData as data:
        data[enums.RigData.rigCmd] = 'IkChain'
    placeJoints( leftArm, [(0, 1), (0.5, 0), (0, -1)] )
    
    rigData = leftArm.rigData
    rigData['ikParams'] = {'name': 'Arm', 'endOrientType': 'True_Zero'}
    leftArm.rigData = rigData
    #clavicleEnd = getattr(clav, attrMap[side] )[0]
    
    moveCard.to( leftArm, clav.end() )
    moveCard.farther( leftArm, pdil.meters(.25) )
    #proxyskel.pointer( clav.end(), leftArm.start() )
    leftArm.start().setBPParent( clav.end() )
    return leftArm


def handSetup( leftArm, numFingers, makeThumb ):
    #hand = Container('Hand', pdil.meters(0.20, 0.20) )
    hand = makeCard( 1, 'Hand', size=pdil.meters([0.20, 0.20]) )
    
    # It makes sense that the wrist is oriented to the hand
    leftArm.end().customUp = hand.getUpArrow()
    
    placeJoints( hand, [(0, -.7)] )
    hand.joints[0].isHelper = True
    leftArm.end().orientTarget = hand.joints[0]
    hand.joints[0].setBPParent( leftArm.end() )
    
    xform( hand, ws=True, t=xform(leftArm.end(), q=True, ws=True, t=True) )
    moveCard.down( hand, pdil.meters(.1) )
    #hand.setParent( leftArm.end() )
    xform( hand, ws=True, piv=xform(leftArm.end(), q=True, ws=True, t=True) )
    
    pointConstraint( leftArm.end(), pdil.dagObj.zero( hand ), mo=True)
    [ hand.attr('t' + a).lock() for a in 'xyz' ]
    
    mod = 0.15 / (numFingers - 1) if numFingers > 1 else 0
    
    for i, finger in enumerate(['Index', 'Middle', 'Ring', 'Pinky'][:numFingers]):
        card = makeCard( 4, finger + '*', suffix='left' )
        moveCard.to( card, leftArm.end() )
        moveCard.backward( card, pdil.meters(i * mod - 0.1) )
        moveCard.down( card, pdil.meters(0.20) )
        
        grp = group(card, n=finger + "_grp")
        card.setParent( grp )
        
        parentConstraint( hand, grp, mo=True )
        card.ry.set(90)
        
        card.joints[-1].isHelper = True
        
        #proxy.pointer( leftArm.end(), card.start() )
        card.start().setBPParent( leftArm.end() )
        
        with card.rigData as data:
            data[enums.RigData.rigCmd] = 'TranslateChain'
    
    if makeThumb:
        thumb = makeCard( 4, 'Thumb*', suffix='left' )
        moveCard.to(thumb, leftArm.end())
        thumb.ry.set(-90)
        
        moveCard.to( thumb, leftArm.end() )
        moveCard.forward( thumb, pdil.meters(0.1) )
        moveCard.down( thumb, pdil.meters(0.1) )
        moveCard.closer( thumb, pdil.meters(0.05) )
        thumb.end().isHelper = True
        grp = group(thumb, n="Thumb_grp")
        parentConstraint( hand, grp, mo=True )
        
        #proxy.pointer( leftArm.end(), thumb.start() )
        thumb.start().setBPParent( leftArm.end() )
        with thumb.rigData as data:
            data[enums.RigData.rigCmd] = 'TranslateChain'

        
def leg( startJoint, dist ):
    '''
    dist, pos moves left
    '''

    suffix = 'left' if dist > 0 else 'right'

    leftLeg = makeCard( 3, ['Hip', 'Knee', 'Ankle'], size=pdil.meters([.2, 1]), suffix=suffix )
    with leftLeg.rigData as data:
        data[enums.RigData.rigCmd] = 'IkChain'
    rigData = leftLeg.rigData
    rigData['ikParams'] = {'name': 'Leg', 'endOrientType': 'True_Zero_Foot'}
    leftLeg.rigData = rigData
    
    placeJoints( leftLeg, [ (0, 1), (-0.23, 0.1), (0, -0.6) ] )
    moveCard.to( leftLeg, startJoint )
    moveCard.left( leftLeg, pdil.meters(dist) )
    
    leftLeg.start().setBPParent(startJoint)
    leftLeg.mirror = ''
    
    return leftLeg


def hindleg(startJoint=None, dist=0.20):
    suffix = 'left' if dist > 0 else 'right'

    leg = makeCard( 4, ['Hip', 'Knee', 'Ankle', 'Ball'], size=pdil.meters([.2, 1]), suffix=suffix )
    with leg.rigData as data:
        data[enums.RigData.rigCmd] = 'DogHindleg'
    placeJoints( leg, [ (0, 1), (-1, 0.1), (1, -0.5), (0.1, -1) ] )
    
    if startJoint:
        moveCard.to( leg, startJoint )
        leg.start().setBPParent( startJoint )
    
    moveCard.left( leg, pdil.meters(dist) )
    
    leg.mirror = ''
    return leg


def foot(legCard):
    foot = makeCard( 3, [ 'Ball', 'Toe', 'ToeEnd'], size=pdil.meters([.4, 0.2]), suffix='left' )
    placeJoints( foot, [(0.5, -1), (-0.7, -1), (-1, -1)] )
    foot.joints[-1].isHelper = True
        
    pivTo( foot, 1, 1 )
    pointConstraint( legCard.end(), foot )
    foot.t.lock()
    
    foot.start().setBPParent( legCard.end() )
    
    return foot


# Sort of special cards -------------------------------------------------------

def squashAndStretchCard(parent, count):
    '''
    ..  todo::
        * Use parent name by default
        * Arrange joints in circle (as separately callable thing)
        * Orient card along parent's X
    '''

    dist = 3.75  # I think this is due to meter being 0.15
    card = makeCard( 1, 'Squash*', size=pdil.meters([.15, .15]) )
        
    angle = math.pi * 2.0 / count
    
    for i in range(count):
        card.addJoint()
       
        card.joints[i].tz.set( math.cos(angle * i) * dist )
        card.joints[i].ty.set( math.sin(angle * i) * dist )
    
    moveCard.toObjByCenter( card, parent )
    
    #card.setTempNames()
    with card.rigData as data:
        data[enums.RigData.rigCmd] = 'SquashStretch'
    for j in card.joints:
        j.setBPParent(parent)
        #j.orientTarget = card.end()
    
    card.end().isHelper = True
        
    rot = xform(parent, q=True, ws=True, ro=True)

    xform(card, ws=True, ro=rot)
    rotate(card, [0, 0, -90], r=True, os=True)
    
    # &&& I do not get what name scheme I'm doing here
    cards = find.blueprintCards()
    cards.remove(card)
    nameScheme = findUniqueNameInfo(util.parse(card.nameInfo.get()), '', cards=cards)
    
    card.nameInfo.set( ' '.join(nameScheme[0]) + nameScheme[1] + '* ' + ' '.join(nameScheme[2]) )
    
    return card


def weaponCard(parentName, name, asymmetric=True):
    '''
    
    I think parent might be a joint name and have it figure more stuff out than normal.
    
    It seems logical that the anticipated things are Wrist and spine.  Then the
    rest of the joints can be listed out.
    '''
    
    card = makeCard( 1, name, size=pdil.meters([.15, .15]) )
    with card.rigData as data:
        data[enums.RigData.rigCmd] = 'TranslateChain'
    
    parent, direct = util.findTempJoint(parentName)
    
    if asymmetric:
        if parent.cardCon.node().isCardMirrored():
            card.mirror = False
            
            if not direct:
                # Put card under root and set future parent
                card.start().postCommand = 'reparent {extraNode0};'
                card.start().extraNode[0] = parent
            else:
                card.start().setBPParent(parent)
                
        else:
            card.start().setBPParent(parent)
    
    else:
        card.start().setBPParent(parent)


def addTwistCard(jnt):
    '''
    Given a `BPJoint` to drive a twist, creates a card with sibling twist helper.
    '''
    names = jnt.card.nameList(usePrefix=False)
    name = names[ jnt.cardCon.index() ]
    # Strip off the suffix if one exists
    if jnt.card.isCardMirrored(): # &&& Should I get the suffix off of this?
        mirrorCode = jnt.card.rigData.get('mirrorCode', '') # &&& Can I always get the mirror code and always set it?
        suffix = config.jointSideSuffix( mirrorCode )
        name = name[: -len(suffix) ]
    else:
        mirrorCode = ''
        
    name += 'Twist'
    
    card = makeCard( jointCount=1, jointNames=[name], rigInfo=None, size=(1, 1) )
    # &&& Can I prevent joints from being added to this card?
    
    # Keep the card scaled along the length of the bone.
    xform( card, piv=(0, .5, 0), ws=True )
    aimConstraint( jnt, card, aim=[0, -1, 0], u=[1, 0, 0], wut='objectrotation', wuo=jnt.cardCon.node(), wu=[0, 0, 1] )
    pointConstraint( jnt.parent, card )
    
    dist, distNode, grp = pdil.dagObj.measure( jnt, jnt.parent )
    grp.setParent( card )
    distNode.setParent( card )
    dist >> card.sy
    
    # The twist needs to stay on axis.
    card.start().tz.lock()
    
    card.extraNode[0] = jnt
    if mirrorCode:
        card.suffix.set( mirrorCode )
    with card.rigData as data:
        data[enums.RigData.rigCmd] = 'TwistHelper'
    
    card.sz.set( max(card.sy.get() / 4.0, 1.0) )
    
    card.start().setBPParent(jnt.parent)
    return card


def bipedSetup(spineCount=4, neckCount=1, numFingers=4, legType='Human', thumb=True, spineOrient=Orientation.VERTICAL):

    spine, hips = spineCard(spineCount, spineOrient)
    
    # Neck
    neck = makeCard( neckCount, 'Neck*', size=pdil.meters([.15, .4]) )
    with neck.rigData as data:
        data[enums.RigData.rigCmd] = 'TranslateChain'
    neck.rx.set( 180 )
        
    moveCard.to( neck, spine.end() )
    moveCard.up( neck, pdil.meters(0.10) )

    neck.start().setBPParent( spine.end() )

    # Head
    head = makeCard( 2, 'Head HeadTip', size=pdil.meters([.3, .3]) )
    with head.rigData as data:
        data[enums.RigData.rigCmd] = 'TranslateChain'
    head.rx.set( 180 )
        
    moveCard.to( head, neck.end() )
    moveCard.up( head, pdil.meters(0.10) )
    head.end().isHelper = True

    head.start().setBPParent( neck.end() )
    
    spine.end().orientTarget = neck.start()
        
    # Arms
    clav = makeCard( 1, 'Clavicle', size=pdil.meters([.1, .1]), suffix='left' )
    with clav.rigData as data:
        data[enums.RigData.rigCmd] = 'TranslateChain'
    moveCard.to( clav, spine.end() )
    moveCard.forward( clav, pdil.meters(0.10) )
    moveCard.left( clav, pdil.meters(0.2) )
    clav.ry.set(-90)
    clav.mirror = ''
    
    clav.start().setBPParent( spine.end() )
    leftArm = arm( clav, 'left' )
    handSetup( leftArm, numFingers, thumb )

    # Legs
    if legType == 'Human':
        leftLeg = leg( hips.start(), 0.20 )
        foot(leftLeg)
    elif legType == 'Dogleg':
        leftLeg = hindleg( hips.start(), 0.20 )

    