from __future__ import print_function

import itertools
import json
import os
import re

from pymel.core import *


from ...add import meters
from ... import core
from ... import lib

from . import space


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
            obj.addAttr( attrName, at='enum', enumName='outline:full', k=False, dv=1 )

        obj.attr(attrName).set(cb=True)
        for surface in surfaces:
            obj.attr(attrName) >> surface.visibility


#available_controls = set()
class control(object):
    '''
    All the nurbs control related commands are collected here.
    
    ..  todo::
        Probably wrap adding the control type into a decorator or something like that.
    '''

    CONTROL_TYPE_NAME = 'motigaCtrlType'

    # Control types
    IK = 'ik'
    POLEVECTOR = 'polevector'
    SPLINE = 'spline'
    TRANSLATE = 'translate'
    ROTATE = 'rotate'
    
    #available_controls = set()
    
    rotOrderEnum = ['xyz', 'yzx', 'zxy', 'xzy', 'yxz', 'zyx']
    
    class CirclePoints:
        '''
        These points are used to make a 1 unit diameter circle by the sphere and disc.
        '''
        major = 0.4924 * 0.9
        minor = 0.0999 * 0.9
        terminal = [0, 0, -.5 * 0.9]
        
        body = [[-0.3918 * 0.9, 0, -0.3918 * 0.9],
                [-0.5540 * 0.9, 0, 0],
                [-0.3918 * 0.9, 0, 0.3918 * 0.9],
                [ 0,                   0, 0.5540 * 0.9], # noqa
                [0.3918 * 0.9,  0, 0.3918 * 0.9], # noqa
                [0.5540 * 0.9,  0, 0], # noqa
                [0.3918 * 0.9,  0, -0.3918 * 0.9]] # noqa
    
    @classmethod
    def build(cls, name, spec, type=''):
        '''
        Note: visGroup is a setting that is applied in the defaultspec decorator
            AFTER the control has been fully created.  This allows the ik/fk
            switcher to control vis directly and connect the visGroup to the
            parent <*>_space group.
        '''
        settings = {'shape': cls.sphere,
                    'size': 1,
                    'color': 'blue 0.5',
                    'visGroup': None,
                    'align': 'y',
                    'rotOrder': 'xyz',
                    }
        
        settings.update(spec)
        
        if isinstance( settings['shape'], basestring ):
            try:
                settings['shape'] = getattr(cls, settings['shape'])
            except Exception:
                settings['shape'] = cls.sphere

        ctrl = spec['shape']( name, settings['size'], settings['color'], type=type, align=settings['align'] )
        addAttr( ctrl, ln='shapeType', dt='string' )
        ctrl.shapeType.set(settings['shape'].__name__)
        
        ctrl.visibility.setKeyable(False)
        
        ctrl.rotateOrder.set( cls.rotOrderEnum.index(settings['rotOrder']) )
        
        addDisplayAttr(ctrl)
        
        lib.sharedShape.use( ctrl )
        return ctrl
    
    @classmethod
    def boundingBox(cls, obj):
        '''
        Maya's boundingBox returns something that contains the object, not necessarily the tighetest fitting box, but
        we need the tightes!
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
        
        return min(x), min(y), min(z), max(x), max(y), max(z)
    
    @classmethod
    def setShape(cls, obj, newShape):
        '''
        :param PyNode obj: The obj to get the shape
        :param newShape: Either a direct reference to a shape on this class,
            ex control.sphere or a string of the name of a shape, ex 'sphere'.
        '''
    
        if isinstance(newShape, basestring):
            if hasattr(cls, newShape):
                newShape = getattr(cls, newShape)
            else:
                return  # Can't do anything, shape doesn't exist

        #bounds = obj.boundingBox()
        #size = max( bounds.height(), bounds.width(), bounds.depth() )
        bb = cls.boundingBox(obj)
        size = max( bb[3] - bb[0], bb[4] - bb[1], bb[5] - bb[2] )
        
        # Spheres and discs have troublesome shapes that are ~25 larger so must be accounted for
        if obj.hasAttr('shapeType'):
            if obj.shapeType.get() in ('sphere',) and newShape.__name__ not in ('sphere', ):
                size *= 1.0 / 1.17
            elif obj.shapeType.get() not in ('sphere', 'disc') and newShape.__name__ in ('sphere', 'disc'):
                #size *= 1.3
                pass
        
        color = getShader( obj )
        if not color:
            color = (.5, .5, .5, .5)
           
        delete( core.shape.getShapes(obj) )

        temp = newShape( 'TEMP', size, color )
    
        for shape in core.shape.getShapes(temp):
            shape.setParent( obj, s=True, add=True )
        
        if not obj.hasAttr('shapeType'):
            addAttr( obj, ln='shapeType', dt='string' )
        obj.shapeType.set(newShape.__name__)
        
        # Reapply the shared shape if it exists to ensure it is at the end
        if lib.sharedShape.find(obj):
            lib.sharedShape.remove(obj)
            lib.sharedShape.use(obj)
        
        addDisplayAttr(obj)
        delete(temp)
    
    def _commonArgs(func):
        '''
        A decorator to manage all control alterations.
        '''
        #global available_controls
        #available_controls.add(func.__name__)
        
        def controlArgs(cls, name, size, color, type='', align='y'):
            '''
            Ensures all controls are built with the same params.
            
            :param string color: A color name and optional transparency, ex "blue 0.90"
            '''
            ctrl = func(cls)
            
            if align == 'x':
                ctrl.rz.set(90)
            if align == 'nx':
                ctrl.rz.set(-90)
                
            if align == 'ny':
                ctrl.rx.set(180)
                
            if align == 'z':
                ctrl.rx.set(90)
            if align == 'nz':
                ctrl.rx.set(-90)
                
            makeIdentity( ctrl, a=True, r=True )
            
            ctrl.rename( name )
            
            for shape in ctrl.getShapes():
                if shape.type() in ['nurbsCurve', 'nurbsSurface']:
                    scale( shape.cv[:], [size] * 3 )
            
            ctrl.addAttr( cls.CONTROL_TYPE_NAME, dt='string' )
            ctrl.attr( cls.CONTROL_TYPE_NAME ).set( type )
            
            if isinstance(color, basestring):
                color = core.shader.parseStr(color)
            core.shader.assign(ctrl, color)
            
            return ctrl
        
        functools.update_wrapper( controlArgs, func, assigned=('__name__',) )
        
        return controlArgs

    @classmethod
    def listShapes(cls):
        shapes = []
        for d in dir(cls):
            func = getattr(cls, d)
            goodSpec = inspect.getargspec(cls.box)
            if d[0] != '_' and inspect.ismethod(func):
                if inspect.getargspec(func) == goodSpec:
                    shapes.append(d)
        return shapes
        
    @classmethod
    @_commonArgs
    def sphere(cls):
        '''
        It takes extra work to draw circle with a single line.  This is accomplished
        by having the terminal point exactly where the curve must pass through
        and points very near it to give it the (almost) correct bend.
        
        This is repeated 3x, then that same technique is used to make a quarter
        arc, then an additional hoop.  The first 3 hoops and transition are
        made vertical, which puts the transition ending back on the ground plane,
        where the 4th hoop remains.
        '''
        ctrl = sphere( ax=[0, 1, 0], ssw=0, esw=360, r=0.49 * 0.9, d=3, s=6, nsp=4 )[0]
        
        major = cls.CirclePoints.major
        minor = cls.CirclePoints.minor
        body = cls.CirclePoints.body
        terminal = cls.CirclePoints.terminal
        
        s = [-minor, 0, -major]
        e = [minor, 0, -major]
        
        hoop = [terminal, s, s] + body + [e, e, terminal]
        count = len(hoop)
        
        transArc = [terminal] + \
            [[-minor, 0, -major]] * 2 + \
            [body[0]] + \
            [[-major, 0, -minor]] * 2 + \
            [[-.5 * 0.9, 0, 0]]
        
        line = curve(p=hoop * 3 + transArc + hoop, d=3 )
        
        rotate( line.cv[:count * 3 + len(transArc) - 1], [90, 0, 0] )
        rotate( line.cv[count:count * 2], [0, 60, 0] )
        rotate( line.cv[count * 2:count * 3], [0, -60, 0] )
        rotate( line.cv[count * 3 + len(transArc):], [0, 90, 0] )
        
        line.rename('outline')
        line.getShape().setParent(ctrl, add=True, shape=True)
        
        delete(line)
        
        return ctrl
    
    @classmethod
    @_commonArgs
    def box(cls):

        p = [   [0, -0.49, 0],
            [-0.49, -0.49, 0.49],
            [-0.49, 0.49, 0.49],
            [0, 0.49, 0] ]
        temp = curve( p=p, d=1 )
        ctrl = revolve( temp, ssw=0, esw=360, d=1, ax=[0, 1, 0], s=4 )[0]
    
        points = [  [-0.5, 0.5, 0.5],
                    [-0.5, -0.5, 0.5],
                    [-0.5, -0.5, -0.5],
                    [-0.5, 0.5, -0.5],
                    [-0.5, 0.5, 0.5],
                    [0.5, 0.5, 0.5],
                    [0.5, 0.5, -0.5],
                    [-0.5, 0.5, -0.5],
                    [-0.5, -0.5, -0.5],
                    [0.5, -0.5, -0.5],
                    [0.5, 0.5, -0.5],
                    [0.5, -0.5, -0.5],
                    [0.5, -0.5, 0.5],
                    [0.5, 0.5, 0.5],
                    [0.5, -0.5, 0.5],
                    [-0.5, -0.5, 0.5] ]
                        
        line = curve(p=points, d=1)
        line.rename('outline')
        
        line.getShape().setParent( ctrl, add=True, shape=True )
            
        delete(line, temp)
        
        return ctrl
    
    @classmethod
    @_commonArgs
    def pin(cls):
        defaults = {'ax': (0, 1, 0), 'ssw': 0, 'esw': 360, 'd': 3, 'ut': 0, 'tol': 0.02, 'ch': False}
        ctrl = sphere( p=(0, 0.8333333, 0), r=0.166667, s=6, nsp=4, **defaults)[0]
        cyl = cylinder( p=(0, 0.345, 0), r=.08333333, hr=8.333333, s=4, nsp=1, **defaults )[0]
        cyl.rename('tube')
    
        points = [
            # shaft
            [0, 0, 0],
            [0, 0.666667, 0],
            # circle
            [-0.11785101234662772, 0.71548248765337219, 0],
            [-0.166667, 0.833333, 0],
            [-0.11785101234662777, 0.95118451234662771, 0],
            [0, 1, 0],
            [0.1178510123466277, 0.95118451234662771, 0],
            [0.166667, 0.833333, 0],
            [0.11785101234662779, 0.71548248765337241, 0],
            [0, 0.666667, 0],
            # cross line
            [0.11785101234662779, 0.71548248765337241, 0],
            [-0.11785101234662777, 0.95118451234662771, 0],
            # transition
            [-0.166667, 0.833333, 0],
            # cross line
            [-0.11785101234662772, 0.71548248765337219, 0],
            [0.1178510123466277, 0.95118451234662771, 0],
        ]
    
        line = curve( p=points, d=1 )
        line.rename('outline')

        line.getShape().setParent( ctrl, add=True, shape=True )
        cyl.getShape().setParent( ctrl, add=True, shape=True )
        
        delete(line, cyl)

        return ctrl
    
    @classmethod
    @_commonArgs
    def disc(cls):
        crv = curve( d=1, p=((0, 0, 0), (0, 0, .5 * 0.9)))
        ctrl = revolve( crv, ch=False, ssw=0, esw=360, degree=3, ax=[0, 1, 0] )[0]
        
        major = cls.CirclePoints.major
        minor = cls.CirclePoints.minor
        body = cls.CirclePoints.body
        terminal = cls.CirclePoints.terminal
        
        s = [-minor, 0, -major]
        e = [minor, 0, -major]
        
        hoop = [terminal, s, s] + body + [e, e, terminal, terminal, terminal]
        cross = [(0, 0, 0.5 * 0.9)]*3 + [(0, 0, 0)]*3 + [(0.5 * 0.9, 0, 0)]*3 + [(-0.5 * 0.9, 0, 0)]*3  # noqa
        
        offset = 0.001
        
        upper = [ (x, offset, z) for x, y, z in hoop + cross ]
        lower = [ (x, -offset, z) for x, y, z in hoop + cross ]
        
        line = curve( p=upper + [(0, offset, 0)] * 3 + [lower[0]] * 2 + lower )
        line.rename('outline')
        line.getShape().setParent( ctrl, add=True, shape=True )
        
        delete(line, crv)
        
        return ctrl
        
    @classmethod
    @_commonArgs
    def plane(cls):
        #crv = curve( d=1, p=((0, 0, 0), (0, 0, .5)))
        #ctrl = revolve( crv, ch=False, ssw=0, esw=360, degree=3, ax=[0, 1, 0] )[0]
        
        line = curve(d=1, p=[
            (-0.5, 0, 0.5),
            (0.5, 0, 0.5),
            (0.5, 0, -0.5),
            (-0.5, 0, -0.5),
            (-0.5, 0, 0.5),
            ]  # noqa
        )

        line.rename('outline')

        ctrl = nurbsPlane( ax=[0, 1, 0], w=1, d=1, lr=1 )[0]

        line.getShape().setParent( ctrl, add=True, shape=True )
        delete(line)

        return ctrl

    @classmethod
    @_commonArgs
    def band(cls):
        ctrl = cylinder( ax=[0, 1, 0], ssw=0, esw=360, r=0.455, hr=0.455, d=3, ch=0)[0]
        
        major = cls.CirclePoints.major
        minor = cls.CirclePoints.minor
        body = cls.CirclePoints.body
        terminal = cls.CirclePoints.terminal
        
        s = [-minor, 0, -major]
        e = [minor, 0, -major]
        
        top = [terminal, s, s] + body + [e, e, terminal, terminal, terminal]
        bot = [terminal, terminal, terminal, terminal, s, s] + body + [e, e, terminal, terminal, terminal]
        
        line = curve( p=top + bot )
        line.rename( 'outline' )
        move( line.cv[ :len(top) ], [0, .125, 0], r=1)
        move( line.cv[ len(top): ], [0, -.125, 0], r=1)
        line.getShape().setParent( ctrl, add=True, shape=True )
        delete(line)
        
        return ctrl
        
    @classmethod
    @_commonArgs
    def hex(cls):
        ctrl = torus(ax=[0, 1, 0], ssw=30, esw=390, msw=360, r=0.40, hr=0.25, d=1, s=6, nsp=4, ch=False)[0]
        
        line = circle( nr=[0, 1, 0], sw=360, r=0.40, d=1, s=6, ch=False )[0]
        line.rename('outline')
        line.getShape().setParent( ctrl, add=True, shape=True )
        delete(line)
        
        return ctrl
    
    @classmethod
    @_commonArgs
    def arrow(cls):
        ctrl = nurbsPlane(axis=[0, 1, 0], u=2, d=1)[0]
        xform( ctrl.cv[2][0], ws=True, t=[0.5, 0, 0.2] )
        xform( ctrl.cv[0][0], ws=True, t=[-0.5, 0, 0.2] )

        line = curve( d=True, p=[(-0.5, 0, -0.5), (-0.5, 0, 0.2), (0, 0, 0.5), (0.5, 0, 0.2), (0.5, 0, -0.5), (-0.5, 0, -0.5)] )
        line.rename('outline')
        line.getShape().setParent( ctrl, add=True, shape=True )
        delete(line)

        return ctrl

    @staticmethod
    def line(src, dest):
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
        
    @staticmethod
    def scale(ctrl, x=1, y=1, z=1):
        '''
        Handles the annoying-ness of scaling the cvs of a multishape obj
        '''
        shared = lib.sharedShape.find(ctrl)
        shapes = ctrl.getShapes()
        if shared in shapes:
            shapes.remove( shared )
        
        for shape in shapes:
            scale( shape.cv, [x, y, z], r=True )


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


def getShapeInfo(name, controller):
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
            pos = [ cmds.xform(cvStr % i, q=True, os=True, t=True) for i in xrange(shape.numCVs())]
        else:
            cvStr = shape.name() + '.cv[%i][%i]'
            pos = [ cmds.xform(cvStr % (u, v), q=True, os=True, t=True)
                for u in xrange(shape.numCVsInU()) for v in xrange(shape.numCVsInV())]
        
        lines.append( '    ' + shape.type() + ' ' + str(pos) )
    return lines


def saveControlShapes(rigController):
    '''
    Given a RigController, returns a str of all the shape info for itself and
    all sub controls for storage in a file or on a node
    '''

    lines = getShapeInfo('main', rigController)
    
    for name, ctrl in rigController.subControl.items():
        lines += getShapeInfo(name, ctrl)

    text = os.linesep.join( lines )
    text = re.sub('\d\.\d+e-\d+', '0', text)             # Replace close to zero with zero
    text = re.sub( r'(\d\.\d{3})(\d*)', r'\1', text   )  # Limit the decimals
    text = re.sub( r'(\.0+)([,\]\)])', r'\2', text)      # trim to integer if possible
    text = re.sub( r'(\.\d*)(0+)([,\]\)])', r'\1\3', text)  # trim trailing zeros
    text = re.sub( r'(-0)([,\]\)])', r'0\2', text)      # replace -0 with 0
    
    return text


def loadControlShapes(rigControl, lines):
    '''
    Given a `RigControl` and a list of lines (via .split() or file id), parse
    for cv position info and apply.
    
    :param rigControl: The control with sub controls to load the given shape info onto.
    :param lines: An iterable of lines containing data from _saveControlShapes.
    
    ..  todo::
        * Actually apply the color info
    '''
    
    controls = {'main': rigControl}
    for name, ctrl in rigControl.subControl.items():
        controls[name] = ctrl
    
    ctrl = ''
    
    for line in lines:
        temp = line.split(':', 1)
        if len(temp) == 2:
            ctrl = temp[0]
            try:
                extraInfo = json.loads(temp[1])
            except Exception:
                # &&& Old system that I can probably dump by 3/30/2014
                color, opacity = eval(temp[1].strip())
                extraInfo = {'color': list(color) + [ 1.0 - opacity[0] ] }
            
            if ctrl in controls:
                if 'color' in extraInfo and extraInfo['color']:
                    core.shader.assign(controls[ctrl], extraInfo['color'])
                    
                if 'shapeType' in extraInfo:
                    if hasattr( control, extraInfo['shapeType'] ) and \
                        controls[ctrl].hasAttr('shapeType') and \
                        controls[ctrl].shapeType.get() != extraInfo['shapeType']:  # noqa

                        control.setShape(controls[ctrl], extraInfo['shapeType'])
                        
                if 'curveColor' in extraInfo:
                    #controls[ctrl].overrideEnabled.set(True)
                    #controls[ctrl].overrideColor.set(extraInfo['curveColor'])
                    setCurveColor(controls[ctrl], extraInfo['curveColor'])
                        
            continue
            
        line = line.strip()
        if line:
            shapeType, points = line.split(' ', 1)
            points = eval(points)
            
            if ctrl in controls:
                for shape in core.shape.getShapes(controls[ctrl]):
                    if shape.type() == shapeType and len(shape.cv) == len(points):
                        for cv, pos in zip(shape.cv, points):
                            xform( cv, os=True, t=pos )


def setCurveColor(ctrl, colorIndex):
    
    curves = [c for c in cmds.listRelatives(ctrl.name(), type='nurbsCurve', f=True) if core.shape.isValidNurbsCurve(c)]
    
    surfaces = cmds.listRelatives(ctrl.name(), type='nurbsSurface', f=True)
    if surfaces:
        curves += surfaces

    for shape in curves:
        try:
            cmds.setAttr( shape + '.overrideEnabled', bool(colorIndex))
            cmds.setAttr( shape + '.overrideColor', colorIndex )
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
        newShapes.append( parent(shape,dest, s=True, add=True )[0] )  # Might be a 2017 bug that shape.setParent() doesn't return an object
    
    if source.hasAttr('shapeType') and dest.hasAttr('shapeType'):
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
    
    createAttrs = list(itertools.chain(func.motigaDynamicAttrs, ['space']))
    
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
