from __future__ import absolute_import, division, print_function

import re

from pymel.core import createNode, listConnections, connectAttr, select, mel

from maya.api import OpenMaya
from maya.cmds import ls

import pdil

from ._lib2 import controllerShape, cardlister


def makePickwalkNode(ikControls=None, fkControls=None):
    '''
    node.ikLinker[*].ikController
                    .ikLeftIndexIk
                    .ikLeftIndexFk
                    .ikRightIndexIk
                    .ikRightIndexFk
    '''

    ikControls = ikControls if ikControls else []
    fkControls = fkControls if fkControls else []

    obj = createNode('network')

    obj.addAttr('up', at='message')
    obj.addAttr('down', at='message')

    obj.addAttr('switcher', at='double', dv=0)

    mobj = pdil.capi.asMObject(obj)
    
    for xk in ['ik', 'fk']:

        cattr = OpenMaya.MFnCompoundAttribute()
        mattr = OpenMaya.MFnMessageAttribute()
        nattr = OpenMaya.MFnNumericAttribute()

        controlLinker = cattr.create(xk + 'Linker', xk)
        cattr.array = True

        controller = mattr.create(xk + 'Controller', xk + 'ctrl' )
        left = mattr.create(xk + 'Left', xk + 'l')
        right = mattr.create(xk + 'Right', xk + 'r')

        leftIndexIk = nattr.create(xk + 'LeftIndexIk', xk + 'lii', OpenMaya.MFnNumericData.kInt, -1)
        leftIndexFk = nattr.create(xk + 'LeftIndexFk', xk + 'lif', OpenMaya.MFnNumericData.kInt, -1)
        rightIndexIk = nattr.create(xk + 'RightIndexIk', xk + 'rii', OpenMaya.MFnNumericData.kInt, -1)
        rightIndexFk = nattr.create(xk + 'RightIndexFk', xk + 'rif', OpenMaya.MFnNumericData.kInt, -1)
        
        cattr.addChild(controller)
        cattr.addChild(left)
        cattr.addChild(right)
        cattr.addChild(leftIndexIk)
        cattr.addChild(leftIndexFk)
        cattr.addChild(rightIndexIk)
        cattr.addChild(rightIndexFk)

        mobj.addAttribute(controlLinker)

    for i, ctrl in enumerate(fkControls):
        print(ctrl, type(ctrl))
        ctrl.message >> obj.fkLinker[i].fkController

    for i, ctrl in enumerate(ikControls):
        ctrl.message >> obj.ikLinker[i].ikController

    return obj



def getIkControlList(ik):
    if not ik:
        return []
        
    return [ctrl for name, ctrl in ik.subControl.items()] + [ik]


def getFkControlList(fk):
    if not fk:
        return []
    
    return [fk] + [ctrl for name, ctrl in fk.subControl.items()]


def setSide(srcPicker, sourceXk, destPicker, destXk, side):
    
    src = srcPicker.attr( sourceXk + 'Linker' )
    dest = destPicker.attr( destXk + 'Linker' )
    
    srcMax = src.numElements() - 1
    destMax = dest.numElements() - 1
    
    targets = [int(round( (i / srcMax) * destMax )) for i in range( srcMax + 1 )]
    print(targets)
    plug = '{xk}Linker[{{i}}].{xk}{Side}Index{dxk}'.format(xk=sourceXk, dxk=destXk.title(), Side=side)
    
    for i, target in enumerate(targets):
        srcPicker.attr( plug.format(i=i) ).set( target )
    

def setLeft(srcPicker, destPicker):
    
    setSide(srcPicker, 'ik', destPicker, 'ik', 'Left')
    setSide(srcPicker, 'ik', destPicker, 'fk', 'Left')
    setSide(srcPicker, 'fk', destPicker, 'ik', 'Left')
    setSide(srcPicker, 'fk', destPicker, 'fk', 'Left')

    setSide(destPicker, 'ik', srcPicker, 'ik', 'Right')
    setSide(destPicker, 'ik', srcPicker, 'fk', 'Right')
    setSide(destPicker, 'fk', srcPicker, 'ik', 'Right')
    setSide(destPicker, 'fk', srcPicker, 'fk', 'Right')

    for plug in srcPicker.ikLinker:
        destPicker.message >> plug.ikLeft

    for plug in srcPicker.fkLinker:
        destPicker.message >> plug.fkLeft

    for plug in destPicker.ikLinker:
        srcPicker.message >> plug.ikRight

    for plug in destPicker.fkLinker:
        srcPicker.message >> plug.fkRight


def buildDefaultNetwork():
    cardHierarchy = cardlister.cardHierarchy()

    for parent, children in cardHierarchy:
        if parent:
            if parent.outputCenter:
                ik = getIkControlList(parent.outputCenter.ik)
                fk = getFkControlList(parent.outputCenter.fk)
                
                makePickwalkNode(ik, fk)
            else:
                
                ikLeft = getIkControlList(parent.outputLeft.ik)
                fkLeft = getFkControlList(parent.outputLeft.fk)
                pickerLeft = makePickwalkNode(ikLeft, fkLeft)
                if ikLeft:
                    switcher = controllerShape.getSwitcherPlug(ikLeft[0])
                    connectAttr(switcher, pickerLeft.switcher)
                
                ikRight = getIkControlList(parent.outputRight.ik)
                fkRight = getFkControlList(parent.outputRight.fk)
                pickerRight = makePickwalkNode(ikRight, fkRight)
                if ikRight:
                    switcher = controllerShape.getSwitcherPlug(ikRight[0])
                    connectAttr(switcher, pickerRight.switcher)
                
                if True:  # Run default linkage of the sides to eachother
                    setLeft(pickerRight, pickerLeft)
                    setLeft(pickerLeft, pickerRight)
                    '''
                    if ikLeft:
                        for i, (left, right) in enumerate(zip(pickerLeft.ikLinker, pickerRight.ikLinker ) ):
                            pickerRight.message >> left.ikLeft
                            left.ikLeftIndexIk.set( i )
                    
                            pickerRight.message >> left.ikRight
                            left.ikRightIndexIk.set( i )
                        
                            pickerLeft.message >> right.ikRight
                            right.ikRightIndexIk.set( i )
                    
                            pickerLeft.message >> right.ikLeft
                            right.ikLeftIndexIk.set( i )
                    
                    if fkLeft:
                        for i, (left, right) in enumerate(zip(pickerLeft.fkLinker, pickerRight.fkLinker ) ):
                            pickerRight.message >> left.fkLeft
                            left.fkLeftIndexFk.set( i )
                    
                            pickerRight.message >> left.fkRight
                            left.fkRightIndexFk.set( i )
                        
                            pickerLeft.message >> right.fkRight
                            right.fkRightIndexFk.set( i )
                    
                            pickerLeft.message >> right.fkLeft
                            right.fkLeftIndexFk.set( i )
                    '''


pickerConnections = set([
    'ikLeftIndexIk',
    'ikLeftIndexFk',
    'ikRightIndexIk',
    'ikRightIndexFk',
    'fkLeftIndexIk',
    'fkLeftIndexFk',
    'fkRightIndexIk',
    'fkRightIndexFk',
])


def getPickerPlug(ctrl):
    ''' Return the picker plug this control is connected to.
    
    Example return: 'network27.fkLinker[1].fkController'
    '''
    for plug in listConnections( ctrl + '.message', p=True, s=False, d=True ):
        if 'kLinker[' in str(plug):
            return plug


def listCon(plug, fallback):
    ''' Wrap listConnections returing the first connection or None
    '''
    cons = listConnections(plug)
    if cons:
        return cons[0]
    else:
        return fallback


def getNextNode(plug, d, fallback):
    
    listElement = plug.getParent()
    name = listElement.attrName()
    xk = name[:2]
    picker = plug.node()
    
    if d == 'down':
        count = picker.attr(name).getNumElements()
        index = listElement.index()
        if index < (count - 1):
            index += 1
            #plug.name().replace('[%i]' % count)
            return listCon( re.sub( r'\[\d+\]', '[%i]' % index, str(plug)), fallback)
            
            #return picker.attr(name)[count].?? .listConections()[0]
        else:
            return listCon(picker.down, fallback)
        
    elif d == 'up':
        count = picker.attr(name).getNumElements()
        index = listElement.index()
        if index > 0:
            index -= 1
            
            return listCon( re.sub( r'\[\d+\]', '[%i]' % index, str(plug)), fallback)
            #return picker.attr(name)[count].?? .listConections()[0]
        else:
            return listCon(picker.up, fallback)


    elif d in ('left', 'right'):
        side = d.title()
        otherPicker = listCon( listElement.attr(xk + side), fallback)
        if otherPicker:
            if otherPicker.switcher.get() < 0.5:
                target_index = listElement.attr( xk + side + 'IndexFk' ).get()
                return listCon( otherPicker.fkLinker[ target_index ].fkController, fallback)
            else:
                target_index = listElement.attr( xk + side + 'IndexIk' ).get()
                return listCon( otherPicker.ikLinker[ target_index ].ikController, fallback)


#editMenuUpdate MayaWindow|mainEditMenu;
#string $nameCommandCmd = "nameCommand -ann \"FossilPickWalkUpNameCommand\" -command (\"FossilPickWalkUp\") FossilPickWalkUpNameCommand"; eval($nameCommandCmd);
#// Result: FossilPickWalkUpNameCommand //


def fossilPickWalk(d='down'):
    allControls = set( ls('*.fossilCtrlType', o=True, r=True) )
    selected = set( ls(sl=True) )
    
    if selected.issubset(allControls):
        #maya.cmds.attributeQuery( 'fossil9CtrlType', n='Shoulder_L_ctrl', ex=1 )
        pickerPlugs = [getPickerPlug(ctrl) for ctrl in selected]
        if all(pickerPlugs):
            # All the selection are controls so we can process their special connections
            select( [getNextNode(pickerPlug, d, ctrl) for pickerPlug, ctrl in zip(pickerPlugs, selected)] )
            return
    
    # Fallback of normal pickwalking
    if d == 'down':
        mel.eval('pickWalkDown')
        
    elif d == 'up':
        mel.eval('pickWalkUp')
        
    elif d == 'left':
        mel.eval('pickWalkLeft')
        
    elif d == 'right':
        mel.eval('pickWalkRight')
    

'''
[[None, [nt.Card(u'Pelvis_card')]],
 [nt.Card(u'Pelvis_card'), [nt.Card(u'Hips_card'), nt.Card(u'Spine_card')]],
 [nt.Card(u'Hips_card'), [nt.Card(u'Hip_card')]],
 [nt.Card(u'Hip_card'), [nt.Card(u'Ball_card')]],
 [nt.Card(u'Ball_card'), []],
 [nt.Card(u'Spine_card'), [nt.Card(u'Clavicle_card'), nt.Card(u'Neck_card')]],
 [nt.Card(u'Clavicle_card'), [nt.Card(u'Shoulder_card')]],
 [nt.Card(u'Shoulder_card'),
    [nt.Card(u'Hand_card'), nt.Card(u'Index_card'), nt.Card(u'Middle_card'), nt.Card(u'Pinky_card'), nt.Card(u'Ring_card'), nt.Card(u'Thumb_card')]],
 [nt.Card(u'Hand_card'), []],
 [nt.Card(u'Index_card'), []],
 [nt.Card(u'Middle_card'), []],
 [nt.Card(u'Pinky_card'), []],
 [nt.Card(u'Ring_card'), []],
 [nt.Card(u'Thumb_card'), []],
 [nt.Card(u'Neck_card'), [nt.Card(u'Head_card')]],
 [nt.Card(u'Head_card'), []]] #


    cards = pdil.tool.fossil.cardlister.cardHierarchy()

    for parent, children in cards:

        childPickers = []
        for child in children:
            picker = makePickwalkNode()
            childPickers.append(picker)

            if parent:
                parent.message >> picker.up

        #for prev, nxt in zip( childPickers,  )

        if parent and children:
            childPickers[0].message >> parent.down

'''