'''
Some of the shapes share data on how to build.  Those are stored here.
'''

import functools

from pymel.core import makeIdentity, scale

import pdil


try:
    basestring
except NameError:
    basestring = str


CONTROL_TYPE_NAME = 'fossilCtrlType'

def setControlType(ctrl, ctrlType):
    ctrl.addAttr( CONTROL_TYPE_NAME, dt='string' )
    ctrl.attr( CONTROL_TYPE_NAME ).set( ctrlType )


def commonArgs(shapeConstructor):
    '''
    A decorator to manage all control alterations.
    '''
    #global available_controls
    #available_controls.add(func.__name__)
    
    def controlArgs(name, size, color, type='', align='y'):
        '''
        Ensures all controls are built with the same params.
        
        :param string color: A color name and optional transparency, ex "blue 0.90"
        '''
        ctrl = shapeConstructor()
        
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
        
        setControlType(ctrl, type)
        
        if isinstance(color, basestring):
            color = pdil.shader.parseStr(color)
        pdil.shader.assign(ctrl, color)
        
        return ctrl
    
    functools.update_wrapper( controlArgs, shapeConstructor, assigned=('__name__',) )
    
    return controlArgs


class CirclePoints(object):
    '''
    These points are used to make a 1 unit diameter circle by the sphere and disc.
    '''
    major = 0.4924 * 0.9
    minor = 0.0999 * 0.9
    terminal = [0, 0, -.5 * 0.9]
    
    body = [[-0.3918 * 0.9, 0, -0.3918 * 0.9],
            [-0.5540 * 0.9, 0,             0],
            [-0.3918 * 0.9, 0,  0.3918 * 0.9],
            [            0, 0,  0.5540 * 0.9],
            [ 0.3918 * 0.9, 0,  0.3918 * 0.9],
            [ 0.5540 * 0.9, 0,             0],
            [ 0.3918 * 0.9, 0, -0.3918 * 0.9]]
            
