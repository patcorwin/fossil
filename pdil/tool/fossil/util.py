from __future__ import print_function

import functools
import json
import re
import traceback

from pymel.core import annotate, confirmDialog, cmds, createNode, evalDeferred, group, hide, ls, PyNode, scriptJob, spaceLocator, select, selected, textFieldButtonGrp, warning, polyCylinder, delete, polyPlane

from pymel.core import makeIdentity, xform, scale, aimConstraint, objExists

import pdil

from . import _core as core
from ... import nodeApi


def parse( names ):
    '''
    Given a string, divides it into the naming chunks.  One name can be marked
    with a '*' to denote it repeats.
    '''

    head = []
    repeat = ''
    tail = []

    names = names.split()
    
    invalid = []
    # Find a repeater, if any, verifying there is only one.
    for name in names:
        if name.endswith( '*' ):
            if repeat:
                raise Exception('Multiple names were marked as repeating with a "*", only can repeat.')
            repeat = name

        else:
            if not re.search( '^[a-zA-Z_][a-zA-Z0-9_]*$', name ):
                invalid.append(name)
            
    if invalid:
        raise Exception( ' '.join(invalid) + ' contain invalid characters' )
            
    if not repeat:
        # If there is no repeating section, the whole thing is the head
        head = names
    else:
        if repeat == names[-1]:
            head = names[:-1]
        elif repeat == names[0]:
            tail = names[1:]
        else:
            i = names.index(repeat)
            head = names[:i]
            tail = names[i + 1:]
        
    if repeat:
        repeat = repeat[:-1]
        
    return head, repeat, tail


def old_isMirrored(jnt):
    '''
    If any parent joint or card is mirrored, it is returned else False.
    '''
    
    if jnt.cardCon.node().mirror not in (None, False):
        return jnt.cardCon.node()
    elif jnt.parent:
        # Walk up joints (just in case it's freeform)
        return isMirrored(jnt.parent)
    else:
        return False


def isMirrored(jnt):
    '''
    If any parent joint or card is mirrored, it is returned else False.
    '''
    
    return jnt.cardCon.node().isCardMirrored()

    
def isAsymmetric(jnt):
    '''
    If the given joint is mirrored but lacks a suffix.
    
    ..  todo::
        Mirror/asymetry is messy right now, there needs to be a check if a joint
        is part of a mirror chain, which is different from if the joint should
        actually be mirrored or not.
    '''
    if jnt.cardCon.node().mirror is False:
        return True
    
    if not jnt.cardCon.node().suffix.get() and jnt.cardCon.node().mirror is None:
        return True
        
    return False

    
def canMirror(jnt):
    '''
    Returns True if the joint is in a mirrored hierarchy and not marked as asymmetric.
    "Consumer" version of isMirrored and isAsymmetric
    '''
    return isMirrored(jnt) and not isAsymmetric(jnt)


def preserveSelection(func):
    '''
    Decorator to keep selection after the function is ran.
    '''
    
    def newFunc(*args, **kwargs):
        sel = selected()
        output = func(*args, **kwargs)
        select( sel )
        return output
        
    functools.update_wrapper( newFunc, func )
    return newFunc


def strToPairs(s):
    '''
    Given a comma separated list of pairs, return as list of pairs.
    Ex: "a b, x y" -> [ ['a','b'], ['x', 'y'] ]
    '''
    
    return [ pair.strip().split() for pair in s.strip().split(',') ]


def findTempJoint(name):
    '''
    Given an output name, searches for a temp joint that will output that joint.
    
    Returns the BPJoint and True *I THINK* if the joint is a single, and False if it could be mirrored
    '''
    
    for card in core.find.blueprintCards():
        for data in card.output():
            if name in data:
                
                if data.index(name) == 1:
                    return data[0], True
                else:
                    return data[0], False


def listTempJoints(includeHelpers=False):
    # Gross hack, this funciton needs to be moved elsewhere

    temps = [j for j in ls(type='joint') if isinstance(j, nodeApi.BPJoint)]
    if includeHelpers:
        return temps
    else:
        return [j for j in temps if not j.isHelper]


def annotateSelectionHandle(obj, text, pos=None):
    '''
    Make an annotation of the `obj`'s selection handle, optionally specifying
    the position of the handle as well.
    '''

    obj.displayHandle.set( True )
    
    if pos:
        obj.selectHandle.set( pos )

    loc = spaceLocator()
    
    ann = annotate(loc, text=text).getParent()
    ann.setParent( obj )
    ann.t.set(obj.selectHandle.get())
    ann.r.lock()
    ann.s.lock()
    
    loc.setParent(ann)
    loc.t.set(0, 0, 0)
    hide(loc)
    
    add = createNode( 'plusMinusAverage' )
    
    ann.t >> add.input3D[0]
    add.input3D[1].set( 0, 1, 0 )
    add.output3D >> obj.selectHandle


# Just in case there are different standard substitutions, have this be a table.
# NOTE:  All keys are assumed to be a single character.
# &&& HOW IS THIS USED?  Ugg, past me is lame.
_suffixSubstTable = {
    'L': ('_L', '_R'),
    'R': ('_R', '_L'),
}


def identifySubst(name, subst):
    '''
    Given a name and a list of (old, new) pairs, figure out which one applies, else None.
    '''
    
    for old, new in subst:
        if name.count(old):
            return (old, new)
    
    return None


class BLANK:
    pass


def FIND(name, cardId=BLANK):
    '''
    A fancier wrapper for PyNode to make it easier to find objects by other
    critieria.
    
    The currently only use is looking up cards by their ids but in case it needs
    to be more flexible, it can be.
    
    ..  todo::
        Use the matching library to find closest matches
        This is AT ODDS with weapon attachments!  Due to the gluing, attachments
        could come up instead.  Maybe all cards prioritizes non-attachments stuff?
    '''
    
    if cardId is not BLANK:
        cards = []
        names = []
        for c in core.find.blueprintCards():
            data = c.rigData
            if 'id' in data and data['id'] == cardId:
                return c
            else:
                cards.append(c)
            
            names.append(c.name())
        
        for c in cards:
            if c.name() == name:
                return c

    else:
        for c in core.find.blueprintCards():
            if c.name() == name:
                return c

    
class GetNextSelected(object):
    '''
    Needs a function that takes a single input of a selected item and returns
    True if processing was successful, signifying the reselect the previously
    selection.
    '''

    def __init__(self, setFunction, clearFunction, extraMenus=None, **kwargs):
        self.field = textFieldButtonGrp(bc=pdil.alt.Callback(self.setup), bl='Get', **kwargs)
        self.menu = []
        cmds.popupMenu()

        def clear():
            self.field.setText('')
            clearFunction()
            
        cmds.menuItem(l='Clear', c=pdil.alt.Callback(clear) )
        
        if extraMenus:
            for label, action in extraMenus:
                self.menu.append(cmds.menuItem(l=label, c=pdil.alt.Callback(action, self.field) ))
        
        self.set = setFunction
        self.clear = clearFunction
    
    def setMenu(self, extraMenus):
        for mi, (label, action) in zip(self.menu, extraMenus):
            cmds.menuItem(mi, e=True, l=label, c=pdil.alt.Callback(action, self.field) )
    
    def setup(self):
        scriptJob( ro=True, e=('SelectionChanged', pdil.alt.Callback(self.getNextSelection)) )
        self.current = selected()
        
    def getNextSelection(self):
        #sel = selectedJoints()
        sel = selected()
        if sel:
            print( 'Passing', sel[0] )
            if self.set( sel[0] ):
                print( 'GOODS' )
            evalDeferred( pdil.alt.Callback(select, self.current) )


def getSelectedCards():
    return [c for c in selected() if c.__class__.__name__ == 'Card']


def saveCardStates():
    '''
    Helper to transfer state from one card to another
    '''
    cardStateInfo = {}

    cards = getSelectedCards()
    
    if not cards:
        cards = core.find.blueprintCards()

    for c in cards:
        name = c.name()
        cardStateInfo[name] = {}
        cardStateInfo[name]['fossilRigState'] = c.fossilRigState.get()

        for side in ('Left', 'Center', 'Right'):
            for kinematic in ('ik', 'fk'):
                shapeAttr = 'outputShape' + side + kinematic
                if c.hasAttr( shapeAttr ):
                    cardStateInfo[name][ shapeAttr ] = c.attr( shapeAttr ).get()
    
    pdil.text.clipboard.set( json.dumps(cardStateInfo) )
    
    
def loadCardStates():
    try:
        cardStateInfo = json.loads( pdil.text.clipboard.get() )
    except Exception:
        print( 'Valid json was not found in the clipboard' )
        return
    
    selectedCards = getSelectedCards()
    
    # If there is a single card, just apply the data
    if len(cardStateInfo) == 1 and len(selectedCards) == 1:
        info = cardStateInfo.values()[0]
        cardAndInfo = [(selectedCards[0], info)]
    
    # Otherwise apply data to as many cards with the same names
    else:
        cardAndInfo = [(PyNode(card), info) for card, info in cardStateInfo.items() if objExists(card)]
                
        
    for card, info in cardAndInfo:
        if 'fossilRigState' in info:
            card.fossilRigState.set( info['fossilRigState'] )
            
        for side in ('Left', 'Center', 'Right'):
            for kinematic in ('ik', 'fk'):
                shapeAttr = 'outputShape' + side + kinematic
                if shapeAttr in info:
                    card.attr( shapeAttr ).set( info[ shapeAttr ] )
                  

def selectedCardsSoft(single=False):
    '''
    Returns selected cards as well as the cards of the selected joints.
    
    If `single` is True, the first card is returned, else None
    '''
    if single:
        cards = selectedCards()
        if cards:
            return cards[0]
        
        for jnt in selectedJoints():
            return jnt.card
        
        return None
        
    else:
        cards = selectedCards()
        temp = set(cards)
        for jnt in selectedJoints():
            if jnt.card not in temp:
                temp.add(jnt.card)
                cards.append(jnt.card)
        return cards
                    
                    
def selectedCards():
    cards = [ o for o in selected(type='transform') if type(o) == nodeApi.Card ]
    
    if not cards:
        bpjs = [ o for o in selected(type='transform') if type(o) == nodeApi.BPJoint ]
        cards = list(set(bpj.card for bpj in bpjs))
    
    return cards
    
    
def selectedJoints():
    sel = selected(type='transform')
    if not sel:
        return []
        
    try:
        # Component don't have .hasAttr but this is easy.
        return [ j for j in sel if j.hasAttr( 'realJoint' ) ]
    except Exception:
        return []


def runOnEach(func, message=''):

    sel = selectedCards()
    if not sel:
        confirmDialog( m='No cards selected' )
        return
    
    with pdil.ui.progressWin(title=message, max=len(sel) ) as prog:
        
        errors = core.exceptions.FossilMultiError()

        #errors = {}
        for i, card in enumerate(sel):
            try:
                func( card )

            except core.exceptions.FossilMultiError as multiError:
                errors.errors += multiError.errors

            except Exception:
                #print( traceback.format_exc() )
                #errors[card] = traceback.format_exc()
                errors.append('Issue on card %s' % card.shortName(), traceback.format_exc())
            prog.update()
        
    if not errors:
        print('No Errors')
        print( message + ' Completed' )
    else:
        for card, text in errors.errors:
            print(card, '-' * 80)
            print( text )
        
        warning( 'Error count={}, see above for the errors'.format(len(errors.errors)) )
        confirmDialog(m='Error count={}, see script editor.'.format(len(errors.errors)) )


def makeFakeBone():
    ''' Used by polySkeleton '''
    bone = polyCylinder()[0]
    bone.ty.set(1)
    makeIdentity(bone, t=True, apply=True)
    xform(bone, ws=True, piv=(0, 0, 0))
    #scale -r -p -1.19209e-07cm 2cm -1.78814e-07cm 0.0229933 0.0229933 0.0229933 ;
    scale( bone.vtx[20:39], (0, 0, 0), r=True, p=(0, 2, 0) )
    return bone


def polySkeleton(cards=None):
    ''' Make cylinders to represent a skeleton (for use in zbrush).
    '''

    if not cards:
        cards = core.find.blueprintCards()

    jointGroup = group(em=True, n='jointGroup')
    # Make cylinders to represent joints
    made = {}
    for card in cards:
        
        for j in card.joints:
            p = j.parent
            
            if p:
                bone = makeFakeBone()
                pdil.dagObj.moveTo(bone, p)
                s = pdil.dagObj.distanceBetween(j, p) * 0.5
                bone.sy.set(s)
                delete(aimConstraint(j, bone, aim=(0, 1, 0), u=(0, 0, 1)))
                makeIdentity(bone, apply=True, s=True)
                made[j] = bone

    # Setup fake joints parentage since they all exist
    for j, bone in made.items():
        p = j.parent
        if p in made:
            bone.setParent( made[p] )
        else:
            bone.setParent( jointGroup )

        
    # Make polygon cards
    cardGroup = group(em=True, n='jointGroup')
    for card in cards:
        points  = [ xform( x, q=True, ws=True, t=True) for x in card.cv ]
        
        poly = polyPlane(sh=True, sw=True)[0]
        poly.setParent(cardGroup)
        
        pdil.dagObj.matchTo(poly, card)
        
        for p, v in zip(points, poly.vtx):
            xform(v, ws=True, t=p)
