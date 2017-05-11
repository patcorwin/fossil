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

import math
import numbers

from pymel.core import *


def _assignInput( plug, input):
    if isinstance( input, numbers.Number ):
        plug.set( input )
    else:
        input >> plug


def add( a, b ):
    node = createNode('plusMinusAverage')
    node.operation.set( 1 )
    
    _assignInput( node.input1D[0], a )
    _assignInput( node.input1D[1], b )

    node.rename('add')
    return node.output1D


def sub( a, b ):
    node = createNode('plusMinusAverage')
    node.operation.set( 2 )
    
    _assignInput( node.input1D[0], a )
    _assignInput( node.input1D[1], b )
    
    node.rename('minus')
    return node.output1D


def divide( a, b ):
    node = createNode('multiplyDivide')
    node.operation.set( 2 )
    
    _assignInput( node.input1X, a )
    _assignInput( node.input2X, b )
    
    node.rename('div')
    return node.outputX


def multiply( a, b ):
    node = createNode('multiplyDivide')
    node.operation.set( 1 )
    
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
    
    node.rename('mul')
    return node.outputX


def opposite( a ):
    '''
    Calculates 1-value
    '''
    node = createNode( 'plusMinusAverage' )
    node.operation.set( 2 )
    
    node.input1D[0].set( 1 )
    _assignInput( node.input1D[1], a )
    
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
    
    
def eulerFromMatrix( matrix, degrees=False ):
    '''
    Returns the euler rotation from a matrix, optionally in degrees.
    '''
    easy = matrix[0][2]
    if easy == 1:
        z = math.pi
        y = -math.pi / 2.0
        x = -z + math.atan2( -matrix[1][0], -matrix[2][0] )
    elif easy == -1:
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