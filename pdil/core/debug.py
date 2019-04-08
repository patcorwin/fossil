from __future__ import print_function

from pymel.core import PyNode, dt, xform


def numf(num):
    # display numbers in a way nicer way
    return '{0:>5.2f}'.format(num)
    
    
def matrixDisplay(o, ws=False):
    if isinstance(o, PyNode):
        m = xform(o, q=True, ws=ws, m=True)
    elif isinstance(o, dt.Matrix):
        m = list(o[0]) + list(o[1]) + list(o[2]) + list(o[3])
    else:
        m = o
    
    print( '[' + ', '.join([numf(n) for n in m[0:4]]) + ']' )
    print( '[' + ', '.join([numf(n) for n in m[4:8]]) + ']' )
    print( '[' + ', '.join([numf(n) for n in m[8:12]]) + ']' )
    print( '[' + ', '.join([numf(n) for n in m[12:16]]) + ']' )