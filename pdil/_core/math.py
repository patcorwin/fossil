'''
Utilities to deal with math nodes with ease so it feel more like writing
equations as well as a few other things.

All regular math operations functions (`add`, `divide`, etc.) take two params
which can either be numbers, plugs or mixed and returns the plug of the output.
Examples are better:

    add(someCube.tx, 3) >> somePlane.ry

    ratio = divide( someCurve.length, obj.originalSize )
    multiple( ratio, 3 ) >> someObj.sx
'''
from __future__ import print_function, absolute_import

import ast
import inspect
import math
import numbers

from pymel.core import *


class VECTOR: pass # noqa
class _VECTOR_ATTR(VECTOR): pass # noqa
class _VECTOR_NUMBER(VECTOR): pass # noqa
VECTOR_ATTR = _VECTOR_ATTR() # noqa
VECTOR_NUMBER = _VECTOR_NUMBER() # noqa
class _NUMBER: pass # noqa
class _NUMBER_ATTR: pass # noqa
NUMBER = _NUMBER() # noqa
NUMBER_ATTR = _NUMBER_ATTR() # noqa


def _assignInput( plug, input):
    if isinstance( input, numbers.Number ):
        plug.set( input )
    else:
        input >> plug


def _assignVectorInput(plug, x, y, z, valueType, value):
    ''' plug is compound, x/y/z are the components.
    '''
    if isinstance(valueType, _VECTOR_NUMBER):
        plug.set(value)
        
    elif isinstance(valueType, _VECTOR_ATTR):
        value >> plug
        
    elif isinstance(valueType, _NUMBER):
        plug.set(value, value, value)
        
    else: # Otherwise it's a scalar plug
        value >> x
        value >> y
        value >> z


def getType(data):
    try:
        if len(data) == 3:
            return VECTOR_NUMBER
    except TypeError:
        pass
    
    if isinstance(data, Attribute):
        if data.type().endswith('3'): # double3 and float3 are
            return VECTOR_ATTR
        else:
            return NUMBER_ATTR
    
    return NUMBER
    

def add( a, b, operation=1, name='add' ):
    ''' Add two number, vectors or combo of the two as direct inputs or plugs.  Returning the appropriate plug
    
    Ex
        add( objA.t, objB.t ) >> objC.t
        add( objA.tx, objB.tx ) >> objC.tx
        
        add( objA.tx, (1, 2 ,3) ) >> objC.tx
        
        add( objA.t, 5 ) >> objC.t  # Since the other input is a vector, converts 5 to (5, 5, 5)
    
    '''
    node = createNode('plusMinusAverage')
    node.operation.set( operation )
    node.rename(name)
    
    aType = getType(a)
    bType = getType(b)
    #print(bType, type(bType), isinstance(bType, VECTOR))
    if isinstance(aType, VECTOR) or isinstance(bType, VECTOR):
        
        leftPlug = node.input3D[0]
        _assignVectorInput(leftPlug, leftPlug.input3Dx, leftPlug.input3Dy, leftPlug.input3Dz, aType, a)
        
        rightPlug = node.input3D[1]
        _assignVectorInput(rightPlug, rightPlug.input3Dx, rightPlug.input3Dy, rightPlug.input3Dz, bType, b)
        '''
        if isinstance(aType, _VECTOR_NUMBER):
            node.input3D[0].set(a)
            
        elif isinstance(aType, _VECTOR_ATTR):
            a >> node.input3D[0]
            
        elif isinstance(aType, _NUMBER):
            node.input3D[0].set(a, a, a)
            
        else:
            a >> node.input3D[0].input3Dx
            a >> node.input3D[0].input3Dy
            a >> node.input3D[0].input3Dz
        
        
        if isinstance(bType, _VECTOR_NUMBER):
            node.input3D[1].set(b)
            
        elif isinstance(bType, _VECTOR_ATTR):
            b >> node.input3D[1]
            
        elif isinstance(bType, _NUMBER):
            node.input3D[1].set(b, b, b)
            
        else:
            b >> node.input3D[1].input3Dx
            b >> node.input3D[1].input3Dy
            b >> node.input3D[1].input3Dz
        '''
        return node.output3D
    else:
        _assignInput( node.input1D[0], a )
        _assignInput( node.input1D[1], b )

        return node.output1D


def sub( a, b ):
    return add(a, b, operation=2, name='minus')
    '''
    node = createNode('plusMinusAverage')
    node.operation.set( 2 )
    
    _assignInput( node.input1D[0], a )
    _assignInput( node.input1D[1], b )
    
    node.rename('minus')
    return node.output1D
    '''


def multiply( left, right, operation=1, name='mult' ):
    node = createNode('multiplyDivide')
    node.operation.set( operation )
    node.rename( name )
    
    leftType = getType(left)
    rightType = getType(right)
    
    if isinstance(leftType, VECTOR) or isinstance(rightType, VECTOR):
        
        _assignVectorInput(node.input1,
            node.input1X,
            node.input1Y,
            node.input1Z,
            leftType,
            left)
        
        _assignVectorInput(node.input2,
            node.input2X,
            node.input2Y,
            node.input2Z,
            rightType,
            right)

        return node.output
        
    else:
        _assignInput( node.input1X, left )
        _assignInput( node.input2X, right )
    
        return node.outputX
    
    '''
    
    if isinstance(a, (tuple, list)):
        _assignInput( node.input1X, a[0] )
        _assignInput( node.input1Y, a[1] )
        _assignInput( node.input1Z, a[2] )
    else:
        _assignInput( node.input1X, a )
    
    if isinstance(b, (tuple, list)):
        _assignInput( node.input2X, b[0] )
        _assignInput( node.input2Y, b[1] )
        _assignInput( node.input2Z, b[2] )
    else:
        _assignInput( node.input2X, b )
    '''


def divide(left, right):
    return multiply(left, right, operation=2, name='div')


'''
def divide( a, b ):
    node = createNode('multiplyDivide')
    node.operation.set( 2 )
    
    _assignInput( node.input1X, a )
    _assignInput( node.input2X, b )
    
    node.rename('div')
    return node.outputX
'''


def opposite( a ):
    '''
    Calculates 1-value
    '''
    
    #return add(1, a, operation=2, name='opposite')
    
    node = createNode( 'plusMinusAverage' )
    node.operation.set( 2 )
    
    node.input1D[0].set( 1 )
    _assignInput( node.input1D[1], a )
    
    node.rename('opposite')
    return node.output1D


def condition( a, symbol, b, true=1, false=0 ):
    '''
    Takes 2 input values and string of the condition (for readability), and
    values if the condition is true or false (defaults to 1 and 0 respectively)
    '''
    mapping = {
        '=':  (0, 'EQ'), # noqa e241
        '!=': (1, 'NE'),
        '>':  (2, 'GT'), # noqa e241
        '>=': (3, 'GE'),
        '<':  (4, 'LT'), # noqa e241
        '<=': (5, 'LE'), }
        
    node = createNode( 'condition' )
    node.operation.set( mapping[symbol][0] )
    _assignInput( node.firstTerm, a )
    _assignInput( node.secondTerm, b )
    
    _assignInput( node.colorIfTrueR, true )
    _assignInput( node.colorIfFalseR, false )
    
    node.rename( mapping[symbol][1] )
    return node.outColorR


def isCloseF(a, b, tolerance=0.001):
    # isClose for a single float instead of a vector.
    return (abs(a - b) < tolerance)
    

def isClose(a, b, tolerance=0.001):
    '''
    Return True if each axis of the given vector/3 element list is with a
    tolerance (default to 0.001).  Mainly to resist float error.
    '''
    if (    abs(a[0] - b[0]) < tolerance
        and abs(a[1] - b[1]) < tolerance
        and abs(a[2] - b[2]) < tolerance ):  # noqa e125
        return True

    return False
    

def clampNode(lower, upper):
    clampNode = createNode('clamp')
    clampNode.min.set(lower)
    clampNode.max.set(upper)
    return clampNode




def clamp(driver, lower, upper):
    
    clampNode = createNode('clamp')
    
    driverType = getType(driver)
    lowerType = getType(lower)
    upperType = getType(upper)

    _assignVectorInput(clampNode.input,
        clampNode.inputR, clampNode.inputG, clampNode.inputB,
        driverType,
        driver)
    
    _assignVectorInput(clampNode.min,
        clampNode.min.inputR, clampNode.min.inputG, clampNode.min.inputB,
        lowerType,
        lower)
        
    _assignVectorInput(clampNode.max,
        clampNode.max.inputR, clampNode.max.inputG, clampNode.max.inputB,
        upperType,
        upper)
        
    
    if isinstance(driverType, VECTOR) or isinstance(lowerType, VECTOR) or isinstance(upperType, VECTOR):
        return clampNode.output
    else:
        return clampNode.outputR


def eulerFromMatrix( matrix, degrees=False ):
    '''
    Returns the euler rotation from a matrix, optionally in degrees.
    '''
    easy = matrix[0][2]
    
    if isCloseF(easy, 1, 0.000000000000001):
        z = math.pi
        y = -math.pi / 2.0
        x = -z + math.atan2( -matrix[1][0], -matrix[2][0] )
        
    elif isCloseF(easy, -1, 0.000000000000001):
        z = math.pi
        y = math.pi / 2.0
        x = z + math.atan2( matrix[1][0], matrix[2][0] )
        
    else:
        y = -math.asin( easy )
        cosY = math.cos( y )

        x = math.atan2( matrix[1][2] * cosY, matrix[2][2] * cosY )
        z = math.atan2( matrix[0][1] * cosY, matrix[0][0] * cosY )

    angles = x, y, z

    if degrees:
        return map( math.degrees, angles )

    return angles



binop = {
    ast.Add: add,
    ast.Sub: sub,
    ast.Mult: multiply,
    ast.Div: divide,
}


def parse(s, objs=None):
    ''' Takes a mathematical expression using the variables defined in the calling scope.
    
    *NOTE* Vector * Vector is piece-wise, like addition, since to allow for minimizing nodes.
    
    Ex `parse('cube.t * 3 + (1, 2, 3)') >> otherCube.t`  The calling scope must
    have PyNode('cube'), each element being multiplied by 3, then adding
    vector(1, 2, 3).
    '''
    lookup = {}
    frame = inspect.currentframe()
    
    if objs:
        lookup.update(objs)
    lookup.update( frame.f_back.f_globals )
    lookup.update( frame.f_back.f_locals )
    
    temp = ast.parse(s.strip())

    return process( temp.body[0].value, lookup )


def process(node, objs):
    '''
    Can take function `clamp(val, min, max)`
    '''
    
    if isinstance(node, ast.BinOp):
        return binop[ type(node.op) ](
            process(node.left, objs),
            process(node.right, objs)
        )

    elif isinstance(node, ast.Num):
        return node.n

    elif isinstance(node, ast.Attribute):
        return objs[node.value.id].attr( node.attr )

    elif isinstance(node, ast.Name):
        return objs[node.id]

    #elif isinstance(node, ast.Str):
    #    if '.' in node.s:
    #        obj, attr = node.s.split('.')
    #        return objs[obj].attr(attr)
    #    else:
    #        return objs[node.s]
    
    elif isinstance(node, ast.Call):
        if node.func.id == 'clamp':
            return clamp(
                process(node.args[0], objs),
                process(node.args[1], objs),
                process(node.args[2], objs)
            )
        
    elif isinstance(node, ast.Tuple):
        return [n.n for n in node.elts]
    
    elif isinstance(node, ast.UnaryOp):
        if isinstance(node.op, ast.USub):
            if isinstance(node.operand, ast.Num):
                return -node.operand.n
