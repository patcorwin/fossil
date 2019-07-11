from __future__ import print_function, division, absolute_import

import importlib
import itertools
import json
import logging
import numbers
import os
import time

from pymel.core import addAttr, annotate, Attribute, attributeQuery, circle, cmds, createNode, delete, \
    disconnectAttr, duplicate, hasAttr, hide, ls, listAttr, mel, parent, PyNode, \
    scale, select, spaceLocator, viewFit, xform

from ....add import meters
from .... import core
from .... import lib

from .. import ui

try:  # Py3 anticipation
    xrange  # noqa
except NameError:
    xrange = range

try:  # Py3 anticipation
    reload  # noqa
except NameError:
    from importlib import reload


log = logging.getLogger(__name__)


if 'global_scale' not in globals():
    global_scale = 1.0


# This isn't really used, but it could be.  As of 2019, most (mabye all?) game engines don't respect rotate order anyway.
ROTATE_ORDER = ['xyz', 'yzx', 'zxy', 'xzy', 'yxz', 'zyx']


# These are really used, but still could be so will be kept around.
class ControlType(object):
    IK          = 'ik'
    POLEVECTOR  = 'polevector'
    SPLINE      = 'spline'
    TRANSLATE   = 'translate'
    ROTATE      = 'rotate'


# Populated by `reloadShapeBuilders()`
SHAPES = {}


def reloadShapeBuilders():
    '''
    Reads in all the `build()` functions from the adjacent *.py files.
    '''
    global SHAPES
    SHAPES.clear()
    
    pyFiles = [f for f in os.listdir( os.path.dirname(__file__) ) if not f.startswith('_') and f.endswith('.py')]
    
    for pyFile in pyFiles:
        shapeName = pyFile.split('.')[0]
        module = importlib.import_module( '.' + shapeName, 'pdil.tool.fossil.controllerShape' )
        reload(module)
        
        if hasattr(module, 'build'):
            SHAPES[shapeName] = module.build
        else:
            pass
            print('Did not find build() function in', pyFile)


reloadShapeBuilders()


def listShapes():
    global SHAPES
    return sorted( list(SHAPES.keys()) )


def build(name, spec, type=''):
    '''
    Note: visGroup is a setting that is applied in the defaultspec decorator
        AFTER the control has been fully created.  This allows the ik/fk
        switcher to control vis directly and connect the visGroup to the
        parent <*>_space group.
    '''
    global SHAPES
    
    settings = {'shape': 'sphere',
                'size': 1,
                'color': 'blue 0.5',
                'visGroup': None,
                'align': 'y',
                'rotOrder': 'xyz',
                }
    
    settings.update(spec)
    
    # Default to the sphere.
    if settings['shape'] not in SHAPES:
        settings['shape'] = 'sphere'
        
    shapeConsturctor = SHAPES[ settings['shape'] ]

    ctrl = shapeConsturctor( name, settings['size'] * global_scale, settings['color'], type=type, align=settings['align'] )
    addAttr( ctrl, ln='shapeType', dt='string' )
    ctrl.shapeType.set( settings['shape'] )
    
    ctrl.visibility.setKeyable(False)
    
    ctrl.rotateOrder.set( ROTATE_ORDER.index(settings['rotOrder']) )
    
    addDisplayAttr(ctrl)
    if lib.sharedShape.get():
        # Not sure if just punting is the right action but this makes this more versatile, and can always be added later.
        lib.sharedShape.use( ctrl )
    return ctrl


# &&& RENAME this to addIkFkSwitch
def ikFkSwitch(name, ikRigController, ikPlugs, fkRigController, fkPlugs):
    '''
    Adds "<name>_Switch" attr to the shared shape, controlling the given ik
    and fk plugs (which are expected to be 0=off and 1.0=on)
    
    ..  todo::
        * Verify an existing switch doesn't exist
    '''
    
    # When adding the switcher shape, re-add the shared shape to ensure it is last.
    lib.sharedShape.remove(ikRigController)
    shape = lib.sharedShape._makeSharedShape(ikRigController, '%s_FKIK_SWITCH' % name, 'kinematicSwitch')
    lib.sharedShape.use(ikRigController)

    for key, obj in itertools.chain( ikRigController.subControl.items(), fkRigController.subControl.items()):
        cmds.parent( shape, obj.longName(), add=True, shape=True )
        lib.sharedShape.remove(obj)
        lib.sharedShape.use(obj)
        
    cmds.parent( shape, fkRigController.longName(), add=True, shape=True )
    lib.sharedShape.remove(fkRigController)
    lib.sharedShape.use(fkRigController)
    
    attrName = name + "_Switch"
    
    if not cmds.objExists( shape + '.' + attrName ):
        cmds.addAttr( shape, longName=attrName, at='double', min=0.0, max=1.0, k=True )
    
    plug = Attribute( shape + '.' + attrName )
        
    if ikPlugs and fkPlugs:
        # Optionally skip in case retrofitting, where these connections are made elsewhere
        for ikPlug in ikPlugs:
            plug >> ikPlug
        if not ikRigController.visibility.isDestination():
            plug >> ikRigController.visibility
            ikRigController.visibility.setKeyable(False)
        for name, ctrl in ikRigController.subControl.items():
            if not ctrl.visibility.isDestination():
                plug >> ctrl.visibility
                ctrl.visibility.setKeyable(False)
            
        opposite = core.math.opposite(plug)
        
        for fkPlug in fkPlugs:
            opposite >> fkPlug
        if not fkRigController.visibility.isDestination():
            opposite >> fkRigController.visibility
            fkRigController.visibility.setKeyable(False)
        for name, ctrl in fkRigController.subControl.items():
            if not ctrl.visibility.isDestination():
                opposite >> ctrl.visibility
                ctrl.visibility.setKeyable(False)

    return plug
    

def getSwitcherPlug(obj):
    '''
    Will return either a string like "Arm_L_FKIK_SWITCH" or empty string if no
    switcher is found.
    
    Can't use pymel to avoid warnings of invalid node (nurbs with no cvs).
    This also means listRelatives returns None instead of []. Lame.
    '''
    shapes = cmds.listRelatives( str(obj), type='nurbsCurve', f=True)
    if shapes:
        for shape in shapes:
            if cmds.objExists( shape + '.kinematicSwitch' ):
                attr = cmds.listAttr(shape, ud=1, st='*_Switch')
                return cmds.ls(shape, l=False)[0] + '.' + attr[0] # noqa
    return ''


def addDisplayAttr(obj):
    '''
    Adds an attr (if needed) to control displaying the full shape or not.
    '''
    attrName = 'display'
    
    shapes = core.shape.getShapes(obj)
    curves = ls(shapes, type='nurbsCurve')
    surfaces = ls(shapes, type='nurbsSurface')
    
    if curves and surfaces:
        if not hasAttr(obj, attrName):
            obj.addAttr( attrName, at='enum', enumName='outline:full:surface', k=False, dv=1 )

        curveVis = createNode('condition')

        obj.attr(attrName) >> curveVis.firstTerm
        curveVis.secondTerm.set(2)
        curveVis.operation.set(4)
        curveVis.colorIfTrueR.set(1)
        curveVis.colorIfFalseR.set(0)

        for curve in curves:
            curveVis.outColorR >> curve.visibility

        obj.attr(attrName).set(cb=True)
        for surface in surfaces:
            obj.attr(attrName) >> surface.visibility




def boundingBox(obj):
    '''
    Maya's boundingBox returns something that contains the object, not necessarily the tighetest fitting box, but
    we need the tightest!
    '''
    x = []
    y = []
    z = []
    for shape in core.shape.getShapes(obj):
        if shape.type() == 'nurbsSurface':
            for u in xrange(shape.numCVsInU()):
                for v in xrange(shape.numCVsInV()):
                    p = xform(shape.cv[u][v], q=True, os=True, t=True)
                    x.append(p[0])
                    y.append(p[1])
                    z.append(p[2])
            
        if shape.type() == 'nurbsCurve':
            for i in xrange(shape.numCVs()):
                p = xform(shape.cv[i], q=True, os=True, t=True)
                x.append(p[0])
                y.append(p[1])
                z.append(p[2])
    
    # If there is no existing nurbs data, default to 1 unit
    if not x and not y and not z:
        return -.5, -.5, -.5, .5, .5, .5
    
    return min(x), min(y), min(z), max(x), max(y), max(z)


def connectingLine(src, dest):
    '''
    Draw an annotation arrow from the src to the dest.
    '''
    loc = spaceLocator()
    line = annotate(loc, tx='').getParent()
    line.setParent(src)
    line.t.set(0, 0, 0)
    shape = line.getShape()
    shape.overrideEnabled.set(True)
    shape.overrideDisplayType.set(1)
    
    loc.setParent( dest )
    loc.t.set(0, 0, 0)
    loc.t.lock()
    hide(loc.listRelatives())


def scaleAllCVs(obj, scaleFactor=1.0, space='object'):
    '''
    Handles the annoying-ness of scaling the cvs of a multishape obj
    '''
    
    if isinstance(scaleFactor, numbers.Number):
        scaleFactor = [scaleFactor] * 3  # Must provide all axes.
    
    kwargs = {'os': True} if space == 'object' else {'ws': True}
    
    for shape in core.shape.getShapes(obj):
        scale(shape.cv, scaleFactor, r=True, **kwargs)


def setShape(obj, newShapeName):
    '''
    :param PyNode obj: The obj to get the shape
    :param newShapeName: String, ex 'shape', available options listed from `listShapes()`.
    '''

    global SHAPES

    if newShapeName not in SHAPES:
        return # Can't do anything, shape doesn't exist

    shapeConsturctor = SHAPES[newShapeName]

    #bounds = obj.boundingBox()
    #size = max( bounds.height(), bounds.width(), bounds.depth() )
    bb = boundingBox(obj)
    size = max( bb[3] - bb[0], bb[4] - bb[1], bb[5] - bb[2] )
    
    # Spheres and discs have troublesome shapes that are ~25 larger so must be accounted for
    if obj.hasAttr('shapeType'):
        if obj.shapeType.get() in ('sphere',) and shapeConsturctor not in ('sphere', ):
            size *= 1.0 / 1.17
        elif obj.shapeType.get() not in ('sphere', 'disc') and shapeConsturctor in ('sphere', 'disc'):
            #size *= 1.3
            pass
    
    color = getShader( obj )
    if not color:
        color = (.5, .5, .5, .5)
       
    delete( core.shape.getShapes(obj) )

    temp = shapeConsturctor( 'TEMP', size, color )

    for shape in core.shape.getShapes(temp):
        shape.setParent( obj, s=True, add=True )
    
    if not obj.hasAttr('shapeType'):
        addAttr( obj, ln='shapeType', dt='string' )
    obj.shapeType.set(newShapeName)
    
    # Reapply the shared shape if it exists to ensure it is at the end
    if lib.sharedShape.find(obj):
        lib.sharedShape.remove(obj)
        lib.sharedShape.use(obj)
    
    addDisplayAttr(obj)
    delete(temp)
    
    
    @staticmethod
    def circle(radius=1, orientPosRef=None):
        '''
        Make a circle, matching the orientation and position of the `orientPosRef` object if given.
        '''
        ctrl = circle(r=meters(radius), nr=[0, 0, 1])[0]
        
        if orientPosRef:
            ctrl.setTranslation( orientPosRef.getTranslation( space='world' ), space='world' )
            ctrl.setRotation( orientPosRef.getRotation( space='world' ), space='world' )
        
        return ctrl


def getShader(ctrl):
    '''
    Given a control, if a shader is being used, returns a the color and transparency.
    '''
    for shape in core.shape.getShapes(ctrl):
        try:
            shader = shape.listConnections( type='shadingEngine' )[0].surfaceShader.listConnections()[0]
            return list(shader.outColor.get()) + [1 - shader.outTransparency.get()[0]]
        except Exception:
            pass
            
    return None


def getShapeInfo_DEPRECATED(name, controller):
    '''
    Returns a list of strings representing the shape of the given controller
    '''
    
    extraInfo = {'color': getShader(controller)}
    
    for shape in core.shape.getShapes(controller):
        extraInfo['curveColor'] = shape.overrideColor.get()
    
    if controller.hasAttr( 'shapeType' ):
        extraInfo['shapeType'] = controller.shapeType.get()
    
    lines = [ name + ':' + json.dumps(extraInfo) ]
    for shape in core.shape.getShapes(controller):
        # pos = [xform(cv, q=True, os=True, t=True) for cv in shape.cv]
        # Iterating cvs in mel is 2-6x faster
        if shape.type() == 'nurbsCurve':
            cvStr = shape.name() + '.cv[%i]'
            localPos = [ cmds.xform(cvStr % i, q=True, os=True, t=True) for i in xrange(shape.numCVs())]
            worldPos = [ cmds.xform(cvStr % i, q=True, ws=True, t=True) for i in xrange(shape.numCVs())]
        else:
            cvStr = shape.name() + '.cv[%i][%i]'
            localPos = [ cmds.xform(cvStr % (u, v), q=True, os=True, t=True)
                for u in xrange(shape.numCVsInU()) for v in xrange(shape.numCVsInV())]
            worldPos = [ cmds.xform(cvStr % (u, v), q=True, ws=True, t=True)
                for u in xrange(shape.numCVsInU()) for v in xrange(shape.numCVsInV())]
        
        lines.append( '    ' + shape.type() + '|os ' + str(localPos) )
        lines.append( '    ' + shape.type() + '|ws ' + str(worldPos) )
    return lines


def getShapeInfo(controller):
    
    info = {}
    
    extraInfo = {'color': getShader(controller)}
    
    for shape in core.shape.getShapes(controller):
        extraInfo['curveColor'] = shape.overrideColor.get()
    
    if controller.hasAttr( 'shapeType' ):
        extraInfo['shapeType'] = controller.shapeType.get()

    info['colors'] = extraInfo

    cmds_xform = cmds.xform

    def truncateZero(vector):
        for i, v in enumerate(vector):
            if abs(v) < 0.000000001:
                vector[i] = 0
        return vector

    for shape in core.shape.getShapes(controller):
        # pos = [xform(cv, q=True, os=True, t=True) for cv in shape.cv]
        # Iterating cvs in mel is 2-6x faster
        if shape.type() == 'nurbsCurve':
            cvStr = shape.name() + '.cv[%i]'
            localPos = [ truncateZero(cmds_xform(cvStr % i, q=True, os=True, t=True)) for i in xrange(shape.numCVs())]
            worldPos = [ truncateZero(cmds_xform(cvStr % i, q=True, ws=True, t=True)) for i in xrange(shape.numCVs())]
            
        else:
            cvStr = shape.name() + '.cv[%i][%i]'
            localPos = [ truncateZero(cmds_xform(cvStr % (u, v), q=True, os=True, t=True))
                for u in xrange(shape.numCVsInU()) for v in xrange(shape.numCVsInV())]
            worldPos = [ truncateZero(cmds_xform(cvStr % (u, v), q=True, ws=True, t=True))
                for u in xrange(shape.numCVsInU()) for v in xrange(shape.numCVsInV())]
            
        count = len(localPos)
        info[ '{}.{}|os'.format(shape.type(), count) ] = localPos
        info[ '{}.{}|ws'.format(shape.type(), count) ] = worldPos
    
    return info


def saveControlShapes(rigController):
    '''
    Given a RigController, returns a str of all the shape info for itself and
    all sub controls for storage in a file or on a node
    '''
    
    data = {'main': getShapeInfo(rigController)}

    for name, ctrl in rigController.subControl.items():
        data[name] = getShapeInfo(ctrl)

    return json.dumps(data)

    '''
    # Old crappy homebrew parsing way, deprecated 3/2019
    lines = getShapeInfo_DEPRECATED('main', rigController)
    
    for name, ctrl in rigController.subControl.items():
        lines += getShapeInfo_DEPRECATED(name, ctrl)

    text = os.linesep.join( lines )
    text = re.sub('\d\.\d+e-\d+', '0', text)             # Replace close to zero with zero
    text = re.sub( r'(\d\.\d{3})(\d*)', r'\1', text   )  # Limit the decimals
    text = re.sub( r'(\.0+)([,\]\)])', r'\2', text)      # trim to integer if possible
    text = re.sub( r'(\.\d*)(0+)([,\]\)])', r'\1\3', text)  # trim trailing zeros
    text = re.sub( r'(-0)([,\]\)])', r'0\2', text)      # replace -0 with 0
    
    return text
    '''


def applyShapeInfo(obj, info, space):
    '''
    Given `info` created by `getShapeInfo()`, apply it to `obj`.  `space` is either 'os' for using object space
    or 'ws' to use world.
    
    You would use 'os' if rebuilding after adjusting the joint location or 'ws' because the you changed the joint's
    orientation.
    '''
    
    colorInfo = info.get('colors', {})
    
    surfaceColor = colorInfo.get('color')
    curveColor = colorInfo.get('curveColor')
    shapeType = colorInfo.get('shapeType')
        
    if shapeType is not None:
        existingShapeType = obj.shapeType.get() if obj.hasAttr('shapeType') else None
        
        if shapeType in SHAPES and existingShapeType != shapeType:
            setShape(obj, shapeType)
    
    if surfaceColor is not None:
        core.shader.assign(obj, surfaceColor)
    
    if curveColor:
        setCurveColor(obj, curveColor)

    for shape in core.shape.getShapes(obj):
        # build up matches by type and cv count
        
        cvCount = shape.numCVs() if shape.type() == 'nurbsCurve' else shape.numCVsInU() * shape.numCVsInV()
        key = '{}.{}|{}'.format(shape.type(), cvCount, space)
        log.debug( 'Key is {} found in info={}'.format(key, key in info) )
        if key in info:
            points = info[key]
            if space == 'os':
                for cv, pos in zip(shape.cv, points):
                    xform( cv, os=True, t=pos )
            elif space == 'ws':
                for cv, pos in zip(shape.cv, points):
                    xform( cv, ws=True, t=pos )


def loadControlShapes(rigControl, lines, useObjectSpace=True):
    '''
    Given a `RigControl` and a list of lines (via .split() or file id), parse
    for cv position info and apply.
    
    :param rigControl: The control with sub controls to load the given shape info onto.
    :param lines: An iterable of lines containing data from _saveControlShapes.
    
    ..  todo::
        * Actually apply the color info
    '''
    
    global SHAPES
    
    # Try using the new way first
    try:
        allInfo = json.loads( '\n'.join(lines) )
    except Exception:
        allInfo = None
    
    if allInfo:
        for ctrlKey, info in allInfo.items():
            if ctrlKey == 'main':
                applyShapeInfo(rigControl, info, 'os' if useObjectSpace else 'ws')
            else:
                applyShapeInfo(rigControl.subControl[ctrlKey], info, 'os' if useObjectSpace else 'ws')
        
        return
    
    
    # BELOW Is the old crappy homebrew parsing method of awfulness. Delete along with getShapeInfo_DEPRECATED
    
    controls = {'main': rigControl}
    for name, ctrl in rigControl.subControl.items():
        controls[name] = ctrl
    
    ctrl = ''
    
    for line in lines:
        temp = line.split(':', 1)
        if len(temp) == 2:
            ctrl = temp[0]

            extraInfo = json.loads(temp[1])
            
            if ctrl in controls:
                if 'color' in extraInfo and extraInfo['color']:
                    core.shader.assign(controls[ctrl], extraInfo['color'])
                    
                if 'shapeType' in extraInfo:
                    #if hasattr( control, extraInfo['shapeType'] ) and \
                    if extraInfo['shapeType'] in SHAPES and \
                        controls[ctrl].hasAttr('shapeType') and \
                        controls[ctrl].shapeType.get() != extraInfo['shapeType']:  # noqa

                        setShape(controls[ctrl], extraInfo['shapeType'])
                        
                if 'curveColor' in extraInfo:
                    #controls[ctrl].overrideEnabled.set(True)
                    #controls[ctrl].overrideColor.set(extraInfo['curveColor'])
                    setCurveColor(controls[ctrl], extraInfo['curveColor'])
                        
            continue
            
        line = line.strip()
        if line:
            shapeType, points = line.split(' ', 1)
            
            # Pre 3/12/19 the type was stored in `object space/os`, afterwards `world space/ws` is also saved.
            parts = shapeType.split('|')
            if len(parts) == 1:
                objectSpace = True
            else:
                shapeType = parts[0]
                objectSpace = parts[1] == 'os'
            
            points = eval(points)
            
            if ctrl in controls:
                for shape in core.shape.getShapes(controls[ctrl]):
                    if shape.type() == shapeType and len(shape.cv) == len(points) and useObjectSpace and objectSpace:
                        for cv, pos in zip(shape.cv, points):
                            xform( cv, os=True, t=pos )
                    elif shape.type() == shapeType and len(shape.cv) == len(points) and not useObjectSpace and not objectSpace:
                        for cv, pos in zip(shape.cv, points):
                            xform( cv, ws=True, t=pos )


def setCurveColor(ctrl, newColor):
    '''
    newColor can an indexed color or you can specify RGB.
    
    NOTE!!! RGB is NOT currently saved.
    '''
    
    curves = [c for c in cmds.listRelatives(ctrl.name(), type='nurbsCurve', f=True) if core.shape.isValidNurbsCurve(c)]
    
    surfaces = cmds.listRelatives(ctrl.name(), type='nurbsSurface', f=True)
    if surfaces:
        curves += surfaces

    for shape in curves:
        try:
            cmds.setAttr( shape + '.overrideEnabled', True)
            
            if isinstance(newColor, int):
                cmds.setAttr( shape + '.overrideColor', newColor )
                cmds.setAttr( shape + '.overrideRGBColors', False )
            else:
                cmds.setAttr( shape + '.overrideRGBColors', True )
                cmds.setAttr( shape + '.overrideColorRGB', *newColor )
            
        except Exception:
            pass
                            
                            
def copyShape(source, dest, mirror=False):
    '''
    Make a copy of the source's shape for the dest.

    :param bool mirror:  If true, it is build mirrored on the x axis.
    '''
    
    source = duplicate(source)[0]
    
    color = getShader( dest )
    delete( core.shape.getShapes(dest) )

    hasSharedShape = False
    if lib.sharedShape.find(dest):
        hasSharedShape = True
        lib.sharedShape.remove(dest)
    
    srcShapes = []
    newShapes = []
    for shape in core.shape.getShapes(source):
        srcShapes.append(shape)
        newShapes.append( parent(shape, dest, s=True, add=True )[0] )  # Might be a 2017 bug that shape.setParent() doesn't return an object
    
    
    if source.hasAttr('shapeType'):
        if not dest.hasAttr('shapeType'):
            try:
                dest.addAttr('shapeType', dt='string')
            except:
                pass
        
        if source.hasAttr('shapeType'):
            dest.shapeType.set( source.shapeType.get() )
    
    if color:
        core.shader.assign(dest, color)
    
    # Reapply the shared shape if it exists to ensure it is at the end
    if hasSharedShape:
        lib.sharedShape.use(dest)
    addDisplayAttr(dest)
    
    if mirror:
        for srcShape, newShape in zip(srcShapes, newShapes):
            for sCv, dCv in zip(srcShape.cv, newShape.cv):
                pos = xform(sCv, q=True, ws=True, t=True)
                pos[0] *= -1
                xform(dCv, ws=True, t=pos)

    delete(source)

    
def copyColors(source, dest):
    '''
    Copies the shader and outline colors.
    
    DOES NOT SUPPORT RGB COLORS YET!
    '''
    for shape in core.shape.getShapes(source):
        colorIndex = shape.overrideColor.get()
        break

    color = getShader(source)
    setCurveColor(dest, colorIndex)
    core.shader.assign(dest, color)


def identifyCustomAttrs(control):
    '''
    Returns a list of attributes not made by the tool.
    
    Such attrs include 'space', 'stretch' (on ik) and so forth.
    
    
    :return: {'type': 'double', 'min': -3, 'max': 45}
    '''
    userKeyable = listAttr(control, ud=True, k=True)
    
    mainCtrl = core.findNode.leadController(control)
    
    func = mainCtrl.getCreateFunction()
    
    attrInfo = {}
    
    createAttrs = list(itertools.chain(func.fossilDynamicAttrs, ['space']))
    
    for attr in userKeyable:

        if attr not in createAttrs:

            attrInfo[attr] = {
                'attributeType': attributeQuery(attr, n=control, at=True)
            }
            
            min, max = control.attr(attr).getRange()
    
            if min is not None:
                attrInfo[attr]['min'] = min
            if max is not None:
                attrInfo[attr]['max'] = max
    
    return attrInfo


def restoreAttr(ctrl, info):
    '''
    Compliment to identifyCustomAttrs, building the attr from the given dict.
    '''
    for name, tempKwargs in info.items():
        if not ctrl.hasAttr(name):
            # Can't have unicode when unpacking kwargs, ug.
            kwargs = {}
            for key, val in tempKwargs.items():
                kwargs[str(key)] = val
            
            kwargs['k'] = True
            
            ctrl.addAttr(name, **kwargs)

    
def updateVisGroupConnections():
    '''
    Any controller who's vis is connected directly to the lib.sharedShape gets it
    moved to the zeroGroup.
    
    Skips over things hooked up to switch attrs.
    '''
    
    for ctrl in core.findNode.controllers():
        visCon = cmds.listConnections(ctrl.visibility.name(), p=True, s=True, d=False)
        if visCon:
            node, attr = visCon[0].rsplit('|')[-1].split('.')
            shape = lib.sharedShape.get(create=False)
            if shape and shape.endswith('|' + node) and not attr.endswith('_Switch'):
                
                zero = core.dagObj.zero(ctrl, apply=False, make=False)
                if zero:
                    
                    if ctrl.visibility.isLocked():
                        ctrl.visibility.unlock()
                        relock = True
                    else:
                        relock = False
                        
                    disconnectAttr(visCon[0], ctrl.visibility)
                    
                    cmds.connectAttr(visCon[0], zero.visibility.name(), f=True)
                    
                    ctrl.visibility.set(1)
                    
                    if relock:
                        ctrl.visibility.lock()
                    
                    print( 'fixed', ctrl )
                else:
                    print( 'FAIL', ctrl )


def simpleCircle(radius=1, orientPosRef=None):
    '''
    Make a circle, matching the orientation and position of the `orientPosRef` object if given.
    '''
    ctrl = circle(r=meters(radius), nr=[0, 0, 1])[0]
    
    if orientPosRef:
        ctrl.setTranslation( orientPosRef.getTranslation( space='world' ), space='world' )
        ctrl.setRotation( orientPosRef.getRotation( space='world' ), space='world' )
    
    return ctrl


def screenshotControlShapes():
    '''
    Takes screen shots of all the available controls shapes as `./ui/shapes/<shape_name>_large.png`.
    
    '''
    global SHAPES
    
    cam = PyNode('persp')
    cam.rx.set( -30 )
    cam.ry.set( 45 )

    shapes = listShapes()

    args = ['temp_shape', 1, 'blue 0.5']

    for shape in shapes:
        destfile = os.path.dirname(ui.__file__) + '/shapes/' + shape + '_large.png'
        if os.path.exists(destfile):
            continue
        print('Grabbing', shape)
        obj = SHAPES[shape](*args)
        
        select(obj)
        
        viewFit(f=.95)  # .95 is default
        
        #need to frame 'deal' and zoom by some amount, or just crop in post?
        
        # -viewer 0 to skip fcheck
        result = mel.eval('playblast -startTime 1 -endTime 1  -format image -sequenceTime 0 -clearCache 1 -viewer 0 -showOrnaments 0 -fp 0 -percent 100 -compression "png" -quality 70 -widthHeight 512 512;')
        
        time.sleep(2.5)
        #Need to wait for render
        
        filename = result.replace('####', '1')
        os.rename( filename, destfile)
        delete(obj)
    print('Done')