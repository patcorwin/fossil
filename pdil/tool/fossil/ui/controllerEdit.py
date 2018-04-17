from __future__ import absolute_import, print_function

from pymel.core import button, Callback, colorEditor, colorIndex, columnLayout, menuItem, objectType, optionMenu
from pymel.core import palettePort, PyNode, rotate, rowColumnLayout, scale, select, selected, selectedNodes, text

from .... import core
from .. import controller


class ShapeEditor(object):
    def __init__(self):
        with columnLayout() as self.main:
            button( l='Select CVs', c=core.alt.Callback(self.selectCVs) )
            button( l='Select Pin Head', c=Callback(self.selectPinHead) )
            text(l='')
            button( l='Rotate X 45', c=core.alt.Callback(self.rotate, 'x', 45) )
            button( l='Rotate Y 45', c=core.alt.Callback(self.rotate, 'y', 45) )
            button( l='Rotate Z 45', c=core.alt.Callback(self.rotate, 'z', 45) )
            text( l='' )
            
    def selectPinHead(self):
        sel = selected()
        if not sel:
            return

        tube, outline, head = None, None, None

        shapes = sel[0].getShapes()
        for shape in shapes[:]:
            if shape.name().count('tube'):
                tube = shape
                shapes.remove(tube)
            elif shape.name().count('outline'):
                outline = shape
                shapes.remove(outline)
            elif shape.name().count('sharedShape'):
                shapes.remove(shape)

        if len(shapes) == 1:
            head = shapes[0]
                
        if tube and outline and head:
            select(head.cv[0:6][0:5], outline.cv[1:14], tube.cv[3][0:3])

    def selectCVs(self):
        sel = selected()
        select(cl=True)
        for obj in sel:
            for shape in core.shape.getShapes(obj):
                select( shape.cv, add=True )
        
    def rotate(self, dir, angle):
        rot = [0, 0, 0]
        rot[ ord(dir) - ord('x') ] = angle
        
        trans = [ PyNode(obj) for obj in selectedNodes() if objectType(obj) == 'transform' ]
        trans += [ PyNode(obj).getParent() for obj in selectedNodes() if objectType(obj).startswith('nurbs') ]
        
        for obj in set(trans):
            for shape in core.shape.getShapes(obj):
                rotate( shape.cv, rot, r=True, os=True )


class Gui(object):
    def __init__(self):
        self.customColor = [1.0, 1.0, 1.0]
        self._colorChangeObjs = []

        with rowColumnLayout('Post_Control_Edit', nc=2):
            with columnLayout():
                self.shapeMenu = optionMenu(l='')  # , cc=core.alt.Callback(self.setOverrides) )
                for shape in controller.control.listShapes():
                    menuItem(l=shape)
                                        
                button('Copy Shape', c=core.alt.Callback(self.copyShape))
                button('Mirror Shape', c=core.alt.Callback(self.copyShape, True))
                button('Copy Colors', c=core.alt.Callback(self.copyColor))
                                
                self.shapeMenu.changeCommand( core.alt.Callback(self.changeShape) )
                
                with rowColumnLayout(nc=2):
                    button(l='+10%', c=core.alt.Callback(self.scaleCvs, 1.10))
                    button(l='+ 1%', c=core.alt.Callback(self.scaleCvs, 1.01))
                    
                    button(l='-10%', c=core.alt.Callback(self.scaleCvs, 0.90))
                    button(l='- 1%', c=core.alt.Callback(self.scaleCvs, 0.99))
            
                ShapeEditor()
                
            with columnLayout():
                text(l='Surface Color')
                
                self.surfacePalette = palettePort(
                    dim=(7, 4),
                    w=(7 * 20),
                    h=(4 * 20),
                    td=True,
                    colorEditable=False)
                self.surfacePalette.changeCommand( core.alt.Callback(self.changeSurfaceColor) )
                
                self.surfacePalette.setRgbValue( [0] + self.customColor )
                for i, (name, c) in enumerate(core.shader.namedColors.items()):
                    self.surfacePalette.setRgbValue( [i + 1] + list(c) )
                
                text(l='')
            
                text(l='Curve Color')
                self.palette = palettePort(
                    dim=(8, 4),
                    w=(8 * 20),
                    h=(4 * 20),
                    td=True,
                    colorEditable=False,
                    transparent=0)
                self.palette.changeCommand( core.alt.Callback(self.changeCurveColor) )
                
                for i in range(1, 32):
                    param = [i] + colorIndex(i, q=True)
                    self.palette.setRgbValue( param )

                self.palette.setRgbValue( (0, .6, .6, .6) )

    def update(self):
        if selected():
            self._colorChangeObjs = selected()

    def changeShape(self):
        newShape = self.shapeMenu.getValue()
        sel = selected()
        if sel:
            for obj in sel:
                if obj.hasAttr( 'fossilCtrlType' ):
                    controller.control.setShape(obj, newShape)
            select(sel)
                
    @staticmethod
    def copyShape(mirror=False):
        sel = selected()
        if len(sel) > 1:
            controller.copyShape(sel[0], sel[1], mirror=mirror)
    
    @staticmethod
    def copyColor():
        sel = selected()
        if len(sel) > 1:
            controller.copyColors(sel[0], sel[1])

    def changeCurveColor(self):
        colorIndex = self.palette.getSetCurCell()
        
        select(cl=True)

        for obj in self._colorChangeObjs:
            controller.setCurveColor(obj, colorIndex)
    
    @staticmethod
    def scaleCvs(val):
        scaleFactor = [val] * 3
        
        for obj in selected():
            for shape in core.shape.getShapes(obj):
                scale(shape.cv, scaleFactor, r=True, os=True)

    def defineSurfaceColor(self):
        val = colorEditor(rgb=self.customColor)
        if val[-1] == '1':  # Control has strange returns, see maya docs
            self.customColor = [ float(f) for f in val.split()][:-1]
            self.surfacePalette.setRgbValue( [0] + self.customColor )
            palettePort(self.surfacePalette, e=True, redraw=True)
            return True
        return False

    def changeSurfaceColor(self):
        colorIndex = self.surfacePalette.getSetCurCell() - 1

        if colorIndex == -1:
            self.defineSurfaceColor()
            color = self.customColor[:]
        else:
            color = list(core.shader.namedColors.values()[colorIndex])

        color.append(0.5)

        sel = selected()
        for obj in sel:
            try:
                core.shader.assign(obj, color)
            except Exception:
                pass
        if sel:
            select(sel)
