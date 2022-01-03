from __future__ import absolute_import, division, print_function

from functools import partial
import json
import math
import os
import traceback

import PySide2

from pymel.core import Callback, colorEditor, colorIndex, objectType, NurbsCurveCV
from pymel.core import palettePort, PyNode, rotate, select, selected, selectedNodes, warning

import pdil

from pdil.vendor import Qt

from .. import node

from .._core import find
from .._lib2 import controllerShape


if 'SHAPE_DEBUG' not in globals():
    SHAPE_DEBUG = False


class ShapeEditor(object):
    '''
    def __init__(self):
        with columnLayout() as self.main:
            button( l='Select CVs', c=pdil.alt.Callback(self.selectCVs) )
            button( l='Select Pin Head', c=Callback(self.selectPinHead) )
    '''

    NUM_COLS = 4
    
    CURVE_NAME = 'Fossil_Curve_Colorer'
    SURFACE_NAME = 'Fossil_Surface_Colorer'

    def __init__(self, source):
        self.window = source
        self.source = source.ui

        # Not sure this is actually needed yet so keep it hidden.
        self.controlCardList.hide()
        
        if not SHAPE_DEBUG:
            self.shapeDebug.hide()
            
        self.hookupSignals()
        self.buildShapeMenu(source.scaleFactor)
        
        #self.surfaceColorLayout.setObjectName(self.SURFACE_NAME)
        
        #setParent( self.SURFACE_NAME )
        self.surfaceColorer = SurfaceColorEditor(self.source.surfaceColorGrid)
        
        self.curveColorer = CurveColorEditor(self.source.curveColorGrid)
        
        self.refresh()
        """
        self.curveColorLayout.setObjectName( self.CURVE_NAME )
        setParent( self.CURVE_NAME )
        
        
        self.refreshCardList()
        """


    def __getattr__(self, name):
        return getattr( self.source, name)

    
    def hookupSignals(self):
        # Scaling
        self.minus_one.clicked.connect( Callback(self.scaleCvs, 0.99) )
        self.minus_ten.clicked.connect( Callback(self.scaleCvs, 0.90) )
        self.plus_ten.clicked.connect( Callback(self.scaleCvs, 1.10) )
        self.plus_one.clicked.connect( Callback(self.scaleCvs, 1.01) )
        
        # Rotating
        self.rot_local_x.clicked.connect( Callback(self.rotate, 'x', 45, 'local') )
        self.rot_local_y.clicked.connect( Callback(self.rotate, 'y', 45, 'local') )
        self.rot_local_z.clicked.connect( Callback(self.rotate, 'z', 45, 'local') )
        self.rot_world_x.clicked.connect( Callback(self.rotate, 'x', 45, 'world') )
        self.rot_world_y.clicked.connect( Callback(self.rotate, 'y', 45, 'world') )
        self.rot_world_z.clicked.connect( Callback(self.rotate, 'z', 45, 'world') )
        
        # Selecting
        self.select_cvs.clicked.connect( Callback(self.selectCVs) )
        self.select_pin_head.clicked.connect( Callback(self.selectPinHead) )
        self.select_band_edge_1.clicked.connect( Callback(self.bandEdge, 1))
        self.select_band_edge_2.clicked.connect( Callback(self.bandEdge, 2))
        
        
        # Shapes
        self.copyShapes.clicked.connect( Callback(self.transferShape) )
        self.mirrorShapes.clicked.connect( Callback(self.transferShape, mirror=True) )
        self.mirrorSide.clicked.connect( Callback(lambda: mirrorAllKinematicShapes(selected())) )
        
        #self.mirrorSide.setContextMenuPolicy(Qt.QtCore.Qt.CustomContextMenu)
        #self.mirrorSide.customContextMenuRequested.connect(self.XXXcontextMenuEvent)
        
        self.copyToCBBtn.clicked.connect( Callback(self.copyToClipboad) )
        self.pasteLocalBtn.clicked.connect( Callback(self.pasteFromCliboard, 'os') )
        self.pasteWorldBtn.clicked.connect( Callback(self.pasteFromCliboard, 'ws') )
        self.copyColor.clicked.connect( Callback(self.copyColor_) )
    
    def copyColor_(self):
        sel = selected()
        if len(sel) > 1:
            for other in sel[1:]:
                controllerShape.copyColors(sel[0], other)
    
    def copyToClipboad(self):
        try:
            info = controllerShape.getShapeInfo(selected()[0])
            s = json.dumps(info)
            pdil.text.clipboard.set( s )
        except Exception:
            warning('Unable to copy shapes')
        
    def pasteFromCliboard(self, space):
        '''
        Deserialize shape info from the clipboard and apply it, either in space='os', object space, or 'ws', world space.
        '''
        try:
            info = json.loads( pdil.text.clipboard.get() )
            for obj in selected():
                controllerShape.applyShapeInfo(obj, info, space)
        except Exception:
            warning('Unable to paste shapes')
    
    def XXXcontextMenuEvent(self, point):
        menu = Qt.QtWidgets.QMenu(self.mirrorSide)
        menu.addAction('demo')
        menu.addAction('test')
        #menu.addAction(self.pasteAct)
        menu.exec_( self.mirrorSide.mapToGlobal(point) )
    
    
    @staticmethod
    def scaleCvs(val):
        #scaleFactor = [val] * 3  # Scale factor needs to be a 3 vector for all axes.
        
        for obj in selected():
            try:
                controllerShape.scaleAllCVs(obj, val)
            except Exception: # This is to ignore trying to 'scale' the switcher curve
                pass
            #for shape in pdil.shape.getNurbsShapes(obj):
            #    scale(shape.cv, scaleFactor, r=True, os=True)


    @staticmethod
    def selectPinHead():
        sel = selected()
        if not sel:
            return
        
        # No the best method, assuming it's made of a tube and another shape but
        # it works for now.
        tube, outline, head = None, None, None
        
        shapes = pdil.shape.getNurbsShapes(sel[0]) # This culls out switchers/vis shapes
        
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

    
    @staticmethod
    def bandEdge(side):
        sel = selected()
        if not sel:
            return
        
        obj = sel[0]
        
        # If the selection is a cv, it probably means we're selecting the other side so assume the parent is the obj.
        if isinstance(obj, NurbsCurveCV):
            obj = obj.node().getParent()
        
        if not obj.hasAttr('shapeType') or obj.shapeType.get() != 'band':
            return
        
        shapes = pdil.shape.getNurbsShapes(obj)
        
        if shapes[0].type() == 'nurbsSurface':
            surface = shapes[0]
            outline = shapes[1]
        else:
            surface = shapes[1]
            outline = shapes[0]
        
        if side == 1:
            select( outline.cv[0:14], surface.cv[3][0:7] )
        else:
            select( outline.cv[16:32], surface.cv[0][0:7] )

    
    @staticmethod
    def selectCVs():
        sel = selected()
        select(cl=True)
        for obj in sel:
            for shape in pdil.shape.getNurbsShapes(obj):
                select( shape.cv, add=True )
    
    
    @staticmethod
    def rotate(dir, angle, space):
        rot = [0, 0, 0]
        rot[ ord(dir) - ord('x') ] = angle
        
        trans = [ PyNode(obj) for obj in selectedNodes() if objectType(obj) == 'transform' ]
        trans += [ PyNode(obj).getParent() for obj in selectedNodes() if objectType(obj).startswith('nurbs') ]
        
        for obj in set(trans):
            for shape in pdil.shape.getNurbsShapes(obj):
                if space == 'world':
                    rotate( shape.cv, rot, r=True, ws=True )
                else:
                    rotate( shape.cv, rot, r=True, os=True )

    
    @staticmethod
    def transferShape(mirror=False):
        sel = selected()
        if len(sel) > 1:
            for dest in sel[1:]:
                controllerShape.copyShape(sel[0], dest, mirror=mirror)
            select(sel)
    
    
    @staticmethod
    def changeShape(shapeName):
        
        sel = selected()
        if sel:
            for obj in sel:
                #if obj.hasAttr( 'fossilCtrlType' ):
                controllerShape.setShape(obj, shapeName)
            select(sel)
    
    
    def buildShapeMenu(self, scale):
                
        shapeFolder = os.path.dirname( __file__ ).replace('\\', '/') + '/shapes'
        
        shapeNames = controllerShape.listShapes()
        
        """
        Old way had transparent background, but didn't scale the icons if the monitor had a scale set.  New version
        does at the sacrifice of transparent background
        
        temp_style = []
        template = "QPushButton#%s { background-image: url('%s'); border: none; width: 90; height: 90;}"  # padding: 0; margin: 0;
        for name in shapeNames:
            temp_style.append( template % (name, shapeFolder + '/' + name + '.png') )
        
        self.window.setStyleSheet( '\n'.join(temp_style) )
        """
        row = 0
        col = 0

        for f in os.listdir(shapeFolder):
            if f.lower().endswith('.png'):
                shapeName = f[:-4]
                if shapeName in shapeNames:
                    button = Qt.QtWidgets.QPushButton()
                    button.setFixedSize(64 * scale, 64 * scale)
                    
                    #button.setObjectName(f[:-4])
                    
                    img = PySide2.QtGui.QPixmap(shapeFolder + '/' + f)
                    img = img.scaled( PySide2.QtCore.QSize( 64 * scale, 64 * scale ),
                        PySide2.QtCore.Qt.AspectRatioMode.IgnoreAspectRatio,
                        PySide2.QtCore.Qt.TransformationMode.SmoothTransformation )

                    button.setFlat(True)
                    button.setAutoFillBackground(True)
                    
                    button.setIcon( img )
                    button.setIconSize( img.size() )
                    
                    button.clicked.connect( Callback(self.changeShape, shapeName) )
                    
                    self.shape_chooser.addWidget(button, row, col)
                    
                    col += 1
                    if col >= self.NUM_COLS:
                        col = 0
                        row += 1
    
    
    def refreshCardList(self):
        '''
        Form cardLister, use .cardHierarchy() just like it does to refresh it's own list
        # cardOrder = cardHierarchy()
        '''
        return
        cards = find.cardHierarchy()

        cardToItem = {None: self.controlCardList.invisibleRootItem()}

        for parent, children in cards:
            
            for child in children:
                item = Qt.QtWidgets.QTreeWidgetItem([child.name()])
                cardToItem[parent].addChild(item)
                cardToItem[child] = item
                item.setExpanded(True)

    
    def refresh(self):
        self.curveColorer.update()
        if SHAPE_DEBUG:
            try:  # &&& Don't have time for this now..
                temp = selected(type='transform')
                if temp:
                    card = temp[0]
                else:
                    return
                
                if not card.__class__.__name__ == 'Card':  # &&& Not a great verification this is a card node.
                    main = node.leadController(card)
                    if main:
                        card = main.card
                            
                text = ''
                
                try:
                    for attr in ['outputShape' + side + kin for side in ['Left', 'Right', 'Center'] for kin in ['ik', 'fk']]:
                        if card.hasAttr(attr):
                            text += '---- ' + attr + '\n\n'
                            text += pdil.text.asciiDecompress( card.attr(attr).get() ) + '\n\n'
                except Exception:
                    print( traceback.format_exc() )
                
                self.shapeDebug.setPlainText(text)
            except:
                pass
        

class SurfaceColorEditor(object):
    WIDTH = 8.0
    
    def __init__(self, grid):
        self.customColor = [1.0, 1.0, 1.0]
        """
        columnLayout(w=100, h=100)
        self.surfacePalette = palettePort(
            dim=(7, 4),
            w=(7 * 20),
            h=(4 * 20),
            td=True,
            colorEditable=False)
        """
        #self.surfacePalette.changeCommand( pdil.alt.Callback(self.changeSurfaceColor) )
        
        #self.surfacePalette.setRgbValue( [0] + self.customColor )
        #for i, (name, c) in enumerate(pdil.shader.namedColors.items()):
        #    self.surfacePalette.setRgbValue( [i + 1] + list(c) )
        
        for i, (name, c) in enumerate(pdil.shader.namedColors.items()):
            col = i % self.WIDTH
            row = math.floor(i / self.WIDTH)
            
            b = PySide2.QtWidgets.QPushButton('    ')
            pal = b.palette()
            pal.setColor(PySide2.QtGui.QPalette.Button, PySide2.QtGui.QColor( c[0] * 255.0, c[1] * 255.0, c[2] * 255.0 ) )
            b.setAutoFillBackground(True)
            b.setPalette(pal)
            
            b.clicked.connect( partial(self.changeSurfaceColor, i) )
            
            grid.addWidget( b, row, col)
        

    def changeSurfaceColor(self, colorIndex):
        #colorIndex = self.surfacePalette.getSetCurCell() - 1

        if colorIndex == -1:
            self.defineSurfaceColor()
            color = self.customColor[:]
        else:
            color = list( list(pdil.shader.namedColors.values())[colorIndex] )

        color.append(0.5)

        sel = selected()
        for obj in sel:
            try:
                pdil.shader.assign(obj, color)
            except Exception:
                pass
        if sel:
            select(sel)

    def defineSurfaceColor(self):
        val = colorEditor(rgb=self.customColor)
        if val[-1] == '1':  # Control has strange returns, see maya docs
            self.customColor = [ float(f) for f in val.split()][:-1]
            self.surfacePalette.setRgbValue( [0] + self.customColor )
            palettePort(self.surfacePalette, e=True, redraw=True)
            return True
        return False


class CurveColorEditor(object):
    WIDTH = 8
    HEIGHT = 4
    
    def __init__(self, grid):
        self._colorChangeObjs = []
        """
        columnLayout()
        self.curvePalette = palettePort(
            dim=(8, 4),
            w=(8 * 20),
            h=(4 * 20),
            td=True,
            colorEditable=False,
            transparent=0)
        self.curvePalette.changeCommand( pdil.alt.Callback(self.changeCurveColor) )
        
        for i in range(1, 32):
            param = [i] + colorIndex(i, q=True)
            self.curvePalette.setRgbValue( param )
        
        self.curvePalette.setRgbValue( (0, .6, .6, .6) )
        """
    
        for i in range(1, 32):
            col = i % self.WIDTH
            row = math.floor(i / self.WIDTH)
            
            b = PySide2.QtWidgets.QPushButton('    ')
            pal = b.palette()
            color = colorIndex(i, q=True)
            pal.setColor(PySide2.QtGui.QPalette.Button, PySide2.QtGui.QColor( color[0] * 255.0, color[1] * 255.0, color[2] * 255.0 ) )
            b.setAutoFillBackground(True)
            b.setPalette(pal)
            
            b.clicked.connect( partial(self.changeCurveColor, i) )
            
            grid.addWidget( b, row, col)
    
    
    def changeCurveColor(self, colorIndex):
        #colorIndex = self.curvePalette.getSetCurCell()
        
        select(cl=True)

        for obj in self._colorChangeObjs:
            controllerShape.setCurveColor(obj, colorIndex)

    def update(self):
        if selected():
            self._colorChangeObjs = selected()


def mirrorAllKinematicShapes(ctrls):
    '''
    Copies all the shapes for that motion type, ex, ik left -> ik right
    '''
    
    done = set()
    
    for ctrl in selected():
        main = node.leadController(ctrl)
        
        if main in done:
            continue
        
        if not main:
            continue
        
        other = main.getOppositeSide()
        
        if not other:
            continue

        controllerShape.copyShape(main, other, mirror=True)
        for name, ctrl in main.subControl.items():
            controllerShape.copyShape(ctrl, other.subControl[name], mirror=True)
        
        done.add(main)