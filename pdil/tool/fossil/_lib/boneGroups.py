'''
Utility to make it easy to select joints by tagging the cards that make them.
'''

from collections import OrderedDict

from pymel.core import select, columnLayout, textScrollList, Callback, button, textField

import pdil

from .. import util
from .._core import find


def addGroup(card, groupName, info=None):
    ''' Add boneGroup `groupName` to card, optionally specifiying a tuple or index
    '''
    
    with card.rigData as data:
        boneGroups = data.setdefault('boneGroups', OrderedDict())
        
        boneGroups[groupName] = info
    
    
def getBoneGroup(groupName):
    
    joints = []
    
    for card in find.blueprintCards():
        boneGroups = card.rigData.get('boneGroups', {})
        
        if groupName in boneGroups:
            info = boneGroups[groupName]
            if info:
                if isinstance(info, int):
                    joints.append( card.joints[info] )
                else:
                    joints += card.joints[ slice(*info) ]
                
            else:
                joints += card.joints
    
    realJoints = []
    
    for j in joints:
        if j.real:
            realJoints.append( j.real )
        if j.realMirror:
            realJoints.append( j.realMirror )
            
    return realJoints


class BoneGroupGui(object):
    
    def __init__(self):
        with pdil.ui.singleWindow('BoneGroups'):
            columnLayout()
            self.lister = textScrollList(dcc=Callback(self.select), sc=Callback(self.setName))
            
            groupNames = set()
            for card in find.blueprintCards():
                boneGroups = card.rigData.get('boneGroups', {})
                groupNames.update( boneGroups.keys() )
                
            self.lister.append( sorted( groupNames ) )
            
            button(l='Add To group', c=Callback(self.addToGroup) )
            self.name = textField()
    
    def refresh(self):
        self.lister.removeAll()
        
        groupNames = set()
        for card in find.blueprintCards():
            boneGroups = card.rigData.get('boneGroups', {})
            groupNames.update( boneGroups.keys() )
        
        self.lister.append( sorted( groupNames ) )
    
    def addToGroup(self):
        groupName = self.name.getText()
        
        if not groupName:
            return
        
        for card in util.selectedCards():
            addGroup(card, groupName)
        
        if groupName not in self.lister.getAllItems():
            self.refresh()
    
    def setName(self):
        pass
        #self.name.setText( self.lister.getSelectItem() )
        #
    
        
    def select(self):
        joints = [getBoneGroup(groupName) for groupName in self.lister.getSelectItem()]
        select(joints)
            