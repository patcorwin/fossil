
from ....vendor import Qt
from .... import core
from .. import space

from pymel.core import Callback, MeshVertex, scriptJob, select, selected, warning, promptDialog


def getSpaceName(prevName=''):
    # &&& This needs to prompt for a name
    name = ''
    msg = 'Enter a name'
    while not name:
        res = promptDialog(m=msg, t='Space Name', tx=prevName, b=['Enter', 'Cancel'])
        if res == 'Cancel':
            return None
        
        name = promptDialog(q=True, text=True)
    
    return name


def addMultiSpace():
    sel = selected()
    if isinstance(sel[1], MeshVertex):
        space.rivetSpace(sel[0], sel[1], getSpaceName())
    else:
        space.add(sel[0], sel[1:], getSpaceName(), space.Mode.MULTI_PARENT)
    select(sel)


def addMultiOrientSpace():
    sel = selected()
    space.add(sel[0], sel[1:], getSpaceName(), space.Mode.MULTI_ORIENT)


def addSpace(mode):
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
        # &&& Gross, need to rework this so getSpaceName() isn't duplicated with the exit.
        name = getSpaceName()
        if name is None:
            return
        space.add( sel[0], sel[1], name, space.Mode.ALT_ROTATE )

    elif mode == '#USER':
        name = getSpaceName()
        if name is None:
            return
        space.addUserDriven( sel[0], name)

    elif mode == space.Mode.ALT_ROTATE:
        if len(sel) != 3:
            warning('You must have 2 targets selected')
            return
        
        name = getSpaceName()
        if name is None:
            return
        space.add(sel[0], sel[1], name, mode, rotateTarget=sel[2])

    else:
        if len(sel) < 2:
            return
        name = getSpaceName()
        if name is None:
            return
        space.add( sel[0], sel[1], name, mode )
    select(sel)


class SpaceTab( object ):
    
    def __init__( self, ui ):
        self.ui = ui

        buttonDirections = [
            ('Rename Space', self.rename, ''),
        
            '---',
        
            ('Add',                 Callback(addSpace, space.Mode.ROTATE_TRANSLATE),
                    'Create a parent constraint'),
            ('Add (Trans Only)',    Callback(addSpace, space.Mode.TRANSLATE),
                    'Create a translate contstraint'),
            ('Add ( No Rot )',      Callback(addSpace, "#NOROT"),
                    'Follow the target as if it a parent constraint but do not inherit rotation'),
            ('Add (No Trans)',      Callback(addSpace, space.Mode.ROTATE),
                    'Create an orient constraint'),
            ('Split Targets',       Callback(addSpace, space.Mode.ALT_ROTATE),
                    'Follow the position of the first target, but the rotation of the second'),
            ('Multi/Vert targets',  Callback(addMultiSpace),
                    ''),
            ('Multi Orient',        Callback(addMultiOrientSpace),
                    ''),
            
            '---',
            
            ('Add Parent',          Callback(addSpace, '#PARENT'),
                    'Convenience to make a space following the actual hierarchical parent'),
            ('Add Main',            Callback(addSpace, '#WORLD'),
                    'Convenience to follow the main controller'),
            ('Add World',           Callback(addSpace, '#TRUEWORLD'),
                    'Convenience to stay in world space'),
            ('Add User Driven',     Callback(addSpace, '#USER'),
                    'Generate a special node you can constrain and manipulate any way you want'),
            
            '---',
            
            ('Remove', Callback(self.remove), ''),
        ]
        
        ROW_SPN = 1
        BTN_COL = 0
        BTN_SPN = 1
        
        USAGE_COL = 1
        USAGE_SPN = 3
        
        DIV_SPN = 4
        
        for row, (label, func, usage) in enumerate(buttonDirections):
            if label == '-':
                divider = Qt.QtWidgets.QLabel(self.ui.space_tab)
                divider.setText('')
                self.ui.spaceQuickButtons.addWidget(divider, row, BTN_COL, ROW_SPN, DIV_SPN)
                continue
            
            button = Qt.QtWidgets.QPushButton(self.ui.space_tab)
            button.setText(label)
            button.clicked.connect( func )
            #button.setObjectName("addSpaceButton")
            self.ui.spaceQuickButtons.addWidget(button, row, BTN_COL, ROW_SPN, BTN_SPN)
            
            usageGuide = Qt.QtWidgets.QLabel(self.ui.space_tab)
            usageGuide.setText(usage)
            #usageGuide.setObjectName("addspaceLabel")
            self.ui.spaceQuickButtons.addWidget(usageGuide, row, USAGE_COL, ROW_SPN, USAGE_SPN)
            
            #button.setText(QtCompat.translate("MainWindow", "Add", None, -1))
            #usageGuide.setText(QtCompat.translate("MainWindow", "TextLabel", None, -1))

            #self.buttons.append(newButton)
        
        self.ui.spaceUp.clicked.connect( self.moveUp )
        self.ui.spaceDown.clicked.connect( self.moveDown )
        self.ui.spaceList.currentRowChanged.connect( self.targetSelected )
        
        self.update()
        
        self.jobId = scriptJob( e=('SelectionChanged', Callback(self.update)))
    
    def close(self):
        try:
            scriptJob(kill=self.jobId)
        except Exception:
            pass
            
    def remove(self):
        #spaces = self.targets.getSelectItem()
        spaces = [str(self.ui.spaceList.currentItem().text())]  # In case I update this to allow multi-select
        
        for obj in selected():
            for _space in spaces:
                if _space in space.getNames(obj):
                    space.remove( obj, _space )
                    
        self.update(keepRow=True)

    def rename(self):
        # Prompt the user for a new space name
        sel = selected(type='transform')
        if sel:
            names = space.getNames(sel[0])
            if names:
                index = self.ui.spaceList.currentRow()
                if index >= 0:
                    newName = getSpaceName(prevName=names[index])
                    if newName:
                        names[index] = newName
                        space.setNames(sel[0], names)
                        self.update(keepRow=True)

    def moveUp(self):
        index = self.ui.spaceList.currentRow()
        if 0 < index < (len(space.getNames(selected()[0]))):
            space.swap(selected()[0], index, index - 1)

            self.update()
            self.ui.spaceList.setCurrentRow(index - 1)
        
    def moveDown(self):
        index = self.ui.spaceList.currentRow()
        if 0 <= index < (len(space.getNames(selected()[0])) - 1):
            space.swap(selected()[0], index, index + 1)
        
            self.update()
            self.ui.spaceList.setCurrentRow(index + 1)

    def update(self, keepRow=False):
        ''' Refreshes the list with the spaces on the currently selected control. '''
        row = self.ui.spaceList.currentRow()
        self.ui.spaceList.clear()
        
        sel = selected(type='transform')

        if sel:
            sel = sel[0]
            names = space.getNames(sel)
            if names:
                self.ui.spaceList.addItems(names)
        
            if row < len(names):
                self.ui.spaceList.setCurrentRow( row )
        

    def targetSelected(self, index):
        '''
        Updates the multi weight table when appropariate
        
        &&& TODO, rebuild when editing the weights.  Old version was bad and simple adjust them like causing drift.
        '''
        
        self.ui.multiWeights.clearContents()
        sel = selected()
        
        if index < 0 or not sel:
            return
        
        targets = space.getTargetInfo(sel[0])
        #targetConstraints = space._targetInfoConstraints[:]
        
        if targets[index].type in [space.Mode.MULTI_PARENT, space.Mode.MULTI_ORIENT]:
            
            state = space.serializeSpaces( sel[0] )[index]
            
            #weights = targetConstraints[index].getWeightAliasList()
            
            self.ui.multiWeights.setRowCount( len(state['targets']) )
            
            for t_i, (target, val) in enumerate(zip(state['targets'], state['extra'])):
                
                
                self.ui.multiWeights.setItem(t_i, 0, Qt.QtWidgets.QTableWidgetItem(target[0])) # target is a pair, name and cardpath
                
                self.ui.multiWeights.setItem(t_i, 1, Qt.QtWidgets.QTableWidgetItem(str(val)))

