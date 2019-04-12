

from .... import core
from .. import space

from pymel.core import button, Callback, columnLayout, connectControl, deleteUI, floatField, frameLayout, layout, \
    MeshVertex, rowColumnLayout, scriptJob, select, selected, text, textFieldButtonGrp, textScrollList, warning


class SpaceLayout( object ):
    def __init__( self ):
        self.main = columnLayout()  # Can't use `with since parent is QT`
        
        with rowColumnLayout(nc=2):
            self.targets = textScrollList(nr=20, sc=Callback(self.targetSelected))
            
            with frameLayout(l='Multi Weights') as self.multiUI:
                pass
    
        with rowColumnLayout(nc=2):
            button( l='   ^   ', c=Callback(self.moveUp))
            button( l='   v   ', c=Callback(self.moveDown))
    
        self.name = textFieldButtonGrp(l='Custom Name', bl='Update Existing')
        button( l='Add', c=Callback(self.addSpace, space.Mode.ROTATE_TRANSLATE) )
        button( l='Add (Trans Only)', c=Callback(self.addSpace, space.Mode.TRANSLATE) )
        button( l='Add ( No Rot )', c=Callback(self.addSpace, "#NOROT") )
        button( l='Add (No Trans)', c=Callback(self.addSpace, space.ROTATE) )
        button( l='Split Targets (pos then rot)', c=Callback(self.addSpace, space.Mode.ALT_ROTATE) )
        button( l='Multi/Vert targets', c=Callback(self.addMultiSpace) )
        button( l='Multi Orient', c=Callback(self.addMultiOrientSpace) )
        text(l='')
        button( l='Add Parent', c=Callback(self.addSpace, '#PARENT') )
        button( l='Add World', c=Callback(self.addSpace, '#WORLD') )
        button( l='Add True World', c=Callback(self.addSpace, '#TRUEWORLD') )
        #button( l='Add External World (For attachments)', c=Callback(self.addSpace, '#EXTERNALWORLD') )
        button( l='Add User Driven', c=Callback(self.addSpace, '#USER') )
        button( l='Remove', c=Callback(self.remove) )
        
        self.update()
        scriptJob( e=('SelectionChanged', Callback(self.update)), p=self.main )


    def targetSelected(self):
        sel = selected()
        targetIndex = self.targets.getSelectIndexedItem()
        if not targetIndex:
            return
        
        i = targetIndex[0] - 1
        
        targets = space.getTargetInfo(sel[0])
        targetConstraints = space._targetInfoConstraints[:]
        
        self.clearMultiTarget()
        if targets[i].type in [space.Mode.MULTI_PARENT, space.Mode.MULTI_ORIENT]:
            
            with rowColumnLayout( nc=2, p=self.multiUI ):
                state = space.serializeSpaces( sel[0] )[i]
                
                weights = targetConstraints[i].getWeightAliasList()
                
                for t_i, (target, val) in enumerate(zip(state['targets'], state['extra'])):
                    text(l=target[0])  # target is a pair, name and cardpath
                    f = floatField(v=val, min=0, max=1)
                    connectControl( f, weights[t_i])
                    
    def moveUp(self):
        sel = textScrollList( self.targets, q=True, sii=True)
        if not sel:
            return
        
        index = sel[0] - 1
        
        if index == 0:
            return
            
        space.swap(selected()[0], index, index - 1)
        
        self.update()
        textScrollList(self.targets, e=True, sii=index)  # tsl is 1-based
        
    def moveDown(self):
        sel = textScrollList( self.targets, q=True, sii=True)
        if not sel:
            return
        
        index = sel[0] - 1
        
        if index == len(space.getNames(selected()[0])) - 1:
            return
            
        space.swap(selected()[0], index, index + 1)
        self.update()
        textScrollList(self.targets, e=True, sii=index + 2)  # tsl is 1-based

    
    def getSpaceName(self):
        # &&& This needs to prompt for a name
        return self.name.getText()

    def addSpace(self, mode):
        sel = selected()
        
        if mode == '#WORLD':
            
            if sel[0].tx.isKeyable():
                space.addWorldToTranslateable( sel[0] )
            else:
                space.addWorld( sel[0] )
            
        elif mode == '#TRUEWORLD':
            space.addTrueWorld( sel[0] )
        elif mode == '#EXTERNALWORLD':
            space.addExternalWorld( sel[0] )
        elif mode == '#PARENT':
            
            if sel[0].fossilCtrlType.get() in ['translate', 'rotate']:

                bindBone = core.constraints.getOrientConstrainee(sel[0])
                if not bindBone:
                    # Handle Group cards
                    try:
                        if sel[0].card.rigData['rigCmd']:
                            side = sel[0].getSide()
                            if side == 'Center':
                                parent = sel[0].card.joints[0].parent.real
                            elif side == 'Left':
                                raise Exception('Left side group parent not implemented yet')
                            elif side == 'Right':
                                raise Exception('Right side group parent not implemented yet')
                    except:
                        raise
                else:
                    parent = bindBone.getParent()

                space.add( sel[0], parent, 'parent', space.Mode.ROTATE_TRANSLATE )
        
        elif mode == '#NOROT':
            space.add( sel[0], sel[1], self.getSpaceName(), space.Mode.ALT_ROTATE )

        elif mode == '#USER':
            space.addUserDriven( sel[0], self.getSpaceName())

        elif mode == space.Mode.ALT_ROTATE:
            if len(sel) != 3:
                warning('You must have 2 targets selected')
                return
            
            space.add(sel[0], sel[1], self.getSpaceName(), mode, rotateTarget=sel[2])

        else:
            if len(sel) < 2:
                return
            space.add( sel[0], sel[1], self.getSpaceName(), mode )
        select(sel)
        
    def addMultiSpace(self):
        sel = selected()
        if isinstance(sel[1], MeshVertex):
            space.rivetSpace(sel[0], sel[1], self.getSpaceName())
        else:
            space.add(sel[0], sel[1:], self.getSpaceName(), space.Mode.MULTI_PARENT)
            
    def addMultiOrientSpace(self):
        sel = selected()
        space.add(sel[0], sel[1:], self.getSpaceName(), space.Mode.MULTI_ORIENT)
        
    def remove(self):
        spaces = self.targets.getSelectItem()
        
        for obj in selected():
            for _space in spaces:
                if _space in space.getNames(obj):
                    space.remove( obj, _space )
                    
        self.update()
        
    def update(self):
        self.targets.removeAll()
        
        sel = selected(type='transform')
        #self.clearMultiTarget()
        if sel:
            sel = sel[0]
            names = space.getNames(sel)
            if names:
                for name in names:
                    self.targets.append(name)
                    
    def clearMultiTarget(self):
        children = layout(self.multiUI, q=True, ca=True)
        if children:
            deleteUI(children)