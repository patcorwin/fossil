from contextlib import contextmanager
import json
import logging

from pymel.core import cmds, delete, getAttr, objExists, orientConstraint, pointConstraint, select, setAttr, traceback

import pdil

from ... import cardRigging
from ... import util
from ... import node

from ..._core import find
from ..._core import skinning
from ..._lib import space
from ..._lib import tpose
from ..._lib2 import controllerShape

from pdil import nodeApi


log = logging.getLogger(__name__)


if '_meshStorage' not in globals():
    _meshStorage = {}


def buildBones(cards=None, removeTempBind=True):
    global _meshStorage
    
    if not cards:
        cards = set(util.selectedCards())
        if not cards:
            pdil.ui.notify( m='No cards selected' )
            return

    issues = validateBoneNames(cards)
    if issues:
        pdil.ui.notify(m='\n'.join(issues), t='Fix these')
        return
    
    cardBuildOrder = find.cardJointBuildOrder()

    skinning.cacheWeights(cards, _meshStorage)

    useRepose = tpose.reposerExists()
    if useRepose:
        log.debug('Reposer Exists')
        realJoints = []  # This is a list of the joints that are ACTUALLY built in this process
        bindPoseJoints = []  # Matches realJoints, the cards that are bound
        tempBindJoints = []  # Super set of bindPoseJoints, including the hierarchy leading up to the bindBoseJoints
        
        estRealJointCount = len(cmds.ls( '*.realJoint' ))
        
        with pdil.ui.progressWin(title='Build Bones', max=estRealJointCount * 3 + len(cards)) as prog:
            # Build the tpose joints
            with tpose.matchReposer(cardBuildOrder):
                for card in cardBuildOrder:
                    if card in cards:
                        newJoints = card.buildJoints_core(nodeApi.fossilNodes.JointMode.tpose)
                        realJoints += newJoints
                        
                        accessoryFixup(newJoints, card)
                        
                    prog.update()
            
                # The hierarchy has to be built to determine the right bindZero, so build everything if all cards
                # are being made, otherwise target just a few
                if len(cardBuildOrder) == len(cards):
                    bindCardsToBuild = cardBuildOrder
                else:
                    bindCardsToBuild = getRequiredHierarchy(cards)
            
            # Temp build the bind pose joints
            for card in bindCardsToBuild:
                joints = card.buildJoints_core(nodeApi.fossilNodes.JointMode.bind)
                tempBindJoints += joints
                if card in cards:
                    bindPoseJoints += joints
            
            with tpose.goToBindPose():
                # Setup all the constraints first so joint order doesn't matter
                constraints = []
                prevTrans = []
                for bind, real in zip(bindPoseJoints, realJoints):
                    #with core.dagObj.Solo(bind):
                    #    bind.jo.set( real.jo.get() )
                    
                    prevTrans.append(real.t.get())
                    constraints.append(
                        [orientConstraint( bind, real ), pointConstraint( bind, real )]
                    )
                    
                    real.addAttr( 'bindZero', at='double3' )
                    real.addAttr( 'bindZeroX', at='double', p='bindZero' )
                    real.addAttr( 'bindZeroY', at='double', p='bindZero' )
                    real.addAttr( 'bindZeroZ', at='double', p='bindZero' )
                    prog.update()
                    #real.addAttr( 'bindZeroTr', at='double3' )
                    #real.addAttr( 'bindZeroTrX', at='double', p='bindZeroTr' )
                    #real.addAttr( 'bindZeroTrY', at='double', p='bindZeroTr' )
                    #real.addAttr( 'bindZeroTrZ', at='double', p='bindZeroTr' )
                    
                    #real.bindZero.set( real.r.get() )
                
                # Harvest all the values
                for real in realJoints:
                    real.bindZero.set( real.r.get() )
                    #real.bindZeroTr.set( real.t.get() )
                    prog.update()
                    
                # Return the real joints back to their proper location/orientation
                for constraint, real, trans in zip(constraints, realJoints, prevTrans):
                    delete(constraint)
                    real.r.set(0, 0, 0)
                    real.t.set(trans)
                    prog.update()
        
        root = node.getTrueRoot()
        topJoints = root.listRelatives(type='joint')
        
        for jnt in topJoints:
            try:
                index = realJoints.index(jnt)
                real = jnt
                bind = bindPoseJoints[index]

                real.addAttr( 'bindZeroTr', at='double3' )
                real.addAttr( 'bindZeroTrX', at='double', p='bindZeroTr' )
                real.addAttr( 'bindZeroTrY', at='double', p='bindZeroTr' )
                real.addAttr( 'bindZeroTrZ', at='double', p='bindZeroTr' )
                
                delta = bind.worldMatrix[0].get() * real.worldInverseMatrix[0].get()
                real.bindZeroTr.set(delta[3][:3])

            except ValueError:
                pass
        
        if removeTempBind:
            delete( tempBindJoints )
    
    else:
        log.debug('No reposer')
        # Only build the selected cards, but always do it in the right order.
        with pdil.ui.progressWin(title='Build Bones', max=len(cards)) as prog:
            for card in cardBuildOrder:
                if card in cards:
                    newJoints = card.buildJoints_core(nodeApi.fossilNodes.JointMode.default)
                    accessoryFixup(newJoints, card)
                    prog.update()
    
    
    if useRepose:
        with tpose.goToBindPose():
            skinning.loadCachedWeights(_meshStorage)
    else:
        skinning.loadCachedWeights(_meshStorage)
    
    select(cards)


def buildRig(cards=None):
    '''
    Makes the rig, saving shapes and removing the old rig if needed.
    '''
    # &&& Need to move find.cardJointBuildOrder to util and make selectedCards() use it.
    if not cards:
        cards = set(util.selectedCards())
    
    mode = 'Use Rig Info Shapes'
    
    if not cards:
        pdil.ui.notify( m='No cards to selected to operate on.' )
        return
    
    # &&& BUG, need to ONLY check against joints under the root, since other non-joint objects might have the same name
    
    # allJoints = ...
            
    cardMissingJoints = []
    for card in cards:
        joints = card.getOutputJoints()
        if joints and card.rigData.get('rigCmd', '') != 'Group':  # Group doesn't build joints
            if len(cmds.ls(joints)) != len(joints): # &&& This is a bad check, a reference mesh joints can mess it up.
                cardMissingJoints.append(card)
                
    # &&& Ideally this prompts to build joints
    if cardMissingJoints:
        print('Cards that do not have built joints:')
        print('\n'.join(str(c) for c in cardMissingJoints))
        if len(cardMissingJoints) == 1:
            pdil.ui.notify(m='{} does not have joints built.'.format(cardMissingJoints[0]) )
        elif len(cardMissingJoints) < 10:
            pdil.ui.notify(m='{} cards do not have joints built:\n{}'.format(
                len(cardMissingJoints), '\n'.join(str(c) for c in cardMissingJoints)
            ) )
        else:
            pdil.ui.notify(m='{} cards do not have joints built.\nSee script editor for full list'.format(
                len(cardMissingJoints), '\n'.join(str(c) for c in cardMissingJoints)
            ) )
        raise Exception('Joints not built')
    
    a = pdil.debug.Timer('Overall build')
            
    cardBuildOrder = find.cardJointBuildOrder()
    
    with tpose.matchReposer(cardBuildOrder) if tpose.reposerExists() else nothing():
        
        with pdil.ui.progressWin(title='Building', max=len(cards) * 3 ) as pr:
            
            for card in cardBuildOrder:
                if card not in cards:
                    continue
                pr.update(status=card.name() + ' prep')
                if mode == 'Use Current Shapes':
                    card.saveShapes()
                
                # If this being rebuilt, also restore the if it's in ik or fk
                switchers = [controllerShape.getSwitcherPlug(x[0]) for x in card._outputs()]
                prevValues = [ (s, getAttr(s)) for s in switchers if s]

                card.removeRig()
                pr.update(status=card.name() + ' build')
                _buildRig([card])
                
                pr.update(status=card.name() + ' build')
                if mode != 'Use Rig Info Shapes':
                    card.restoreShapes()
                    
                # Restore ik/fk-ness
                for switch, value in prevValues:
                    if objExists(switch):
                        setAttr(switch, value)
                
    tpose.markBindPose(cards)
    
    select(cards)
    a.stop()


if 'raiseErrors' not in globals():
    raiseErrors = False


def _buildRig(cards):
    '''
    Build the rig for the given cards, defaulting to all of them.
    '''
    global raiseErrors  # Testing hack.
    errors = []
    
    #if not cards:
    #    cards =
    
    #print( 'Building Cards:\n    ', '    \n'.join( str(c) for c in cards ) )
    
    # Ensure that main and root motion exist
    main = node.mainGroup()
    
    rootMotion = find.rootMotion(main=main)
    if not rootMotion:
        rootMotion = node.rootMotion(main=main)
        space.addMain(rootMotion)
        space.addTrueWorld(rootMotion)
    
    # Build all the rig components
    for card in cards:
        if card.rigData.get('rigCmd'):
            try:
                isAccessory = card.rigData.get('accessory', False)
                
                rigComponent = cardRigging.registeredControls[ card.rigData.get('rigCmd') ]
                fk = not isAccessory if isAccessory and rigComponent.ik_ else True # Skip fk for ik accessories
                rigComponent.build(card, buildFk=fk )
            except Exception:
                print( traceback.format_exc() )
                errors.append( (card, traceback.format_exc()) )
                
    # Afterwards, create any required space switching that comes default with that card
    for card in cards:
        if card.rigData.get('rigCmd'):
            func = cardRigging.registeredControls[ card.rigData.get('rigCmd') ]
            if func:
                func.postCreate(card)
    
    space.attemptDelayedSpaces()
    
    if errors:
    
        for card, err in errors:
            print( pdil.text.writeInBox( str(card) + '\n' + err ) )
    
        print( pdil.text.writeInBox( "The following cards had errors:\n"
            + '\n'.join([str(card) for card, err in errors]) ) ) # noqa e127
        
        pdil.ui.notify( m='Errors occured!  See script editor for details.' )
        
        if raiseErrors:
            raise Exception( 'Errors occured on {0}'.format( errors ) )


def validateBoneNames(cards):
    '''
    Returns a list of any name issues building the given cards.
    '''
    issues = []
    allJoints = { c: c.getOutputJoints() for c in find.blueprintCards()}

    untestedCards = list(allJoints.keys())

    for current in cards:
        
        untestedCards.remove(current)

        currentJoints = set( allJoints[current] )
        if len(currentJoints) != len( allJoints[current] ):
            if current.isCardMirrored() and not current.findSuffix():
                issues.append(current.name() + ' will mirror but needs a "Side" assignment')
            else:
                issues.append(current.name() + ' does not have unique internal names')
        
        if 'NOT_ENOUGH_NAMES' in currentJoints:
            issues.append( '{} does not have enough names'.format(current) )

        for otherCard in untestedCards:
            overlap = currentJoints.intersection( allJoints[otherCard] )
            if overlap:
                issues.append( '{} and {} overlap {}'.format( current, otherCard, overlap ))

    return issues


def getRequiredHierarchy(cards):
    hierachy = find.cardHierarchy()
    parentLookup = {child: parent for parent, children in hierachy for child in children}
    
    required = set()
    
    for card in cards:
        c = card
        while c:
            if c in required:
                break
            required.add(c)
            c = parentLookup[c]

    return [c for c, children in hierachy if c in required]


def accessoryFixup(newJoints, card):
    ''' Place the topmost joints in a separate group so they aren't exported.
    '''
    
    if not newJoints: # CtrlGroup doesn't make joints so just leave
        return
    
    newJoints = set(newJoints)
    
    if card.rigData.get('accessory'):
        
        # Freeform and mirrored joints have several the need parent fixup
        for jnt in newJoints:
            parent = jnt.getParent()
            if parent not in newJoints:
                jnt.setParent( node.accessoryGroup() )
                
                jnt.addAttr('fossilAccessoryInfo', dt='string')
                jnt.fossilAccessoryInfo.set( json.dumps( {'parent': parent.longName()} ) )


@contextmanager
def nothing():
    yield


def deleteBones(cards=None):
    global _meshStorage
    if not cards:
        cards = util.selectedCards()
    
    # &&& Figure out what the children cards are since they implictly get deleted too.
    
    skinning.cacheWeights(cards, _meshStorage)
    
    with pdil.ui.progressWin(title='Deleting Bones', max=len(cards)) as prog:
        for card in cards:
            card.removeBones()
            prog.update()