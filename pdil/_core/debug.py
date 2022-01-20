from __future__ import absolute_import, print_function

import collections
from contextlib import contextmanager
import time

from pymel.core import dt, polyColorPerVertex, polyCylinder, polyUnite, PyNode, selected, xform

__all__ = [
    'numf',
    'matrixDisplay',
    'axisWidget',
    'Timer',
    'TimerBasic',
    'TimerAggregate',
]


def numf(num):
    ''' Display floats nicely.
    '''
    return '{0:>5.2f}'.format(num)
    
    
def matrixDisplay(o, ws=False):
    ''' Given an object or matrix, prints it out so it's readable.
    '''
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


class BLANK:
    pass


def axisWidget(parentUnder=BLANK):
    ''' Makes colored object represent the 3 axes (as a child of the selection if possible).
    
    Can take an object to be the parent, or None for no parent.
    '''
    
    sel = selected()
    
    info = {
        'x': [[1, 0, 0], [1, 0, 0, 1]],
        'y': [[0, 1, 0], [1, 1, 0, 1]],
        'z': [[0, 0, 1], [0, 0, 1, 1]],
    }

    cyls = []
    for name, (axis, color) in info.items():
        cyl = polyCylinder(radius=.1, axis=axis)[0]
        cyl.t.set( axis )
        
        polyColorPerVertex(cyl, r=color[0], g=color[1], b=color[2])
        cyl.displayColors.set(True)
        cyls.append(cyl)
        
    obj = polyUnite(cyls, ch=False)[0]
    
    if parentUnder is not None:
        try:
            if parentUnder is BLANK:
                if sel:
                    obj.setParent(sel[0])
            else:
                obj.setParent(parentUnder)
                
            obj.t.set(0, 0, 0)
            obj.r.set(0, 0, 0)
        except Exception:
            pass
    
    return obj


_allTimers = collections.OrderedDict()
_counts = collections.OrderedDict()


class Timer(object):
    ''' Sprinkle this timer in to track, possibly looping, sections.  ex:
    
    t = Timer('setup')
    ... # Perform some setup code
    
    for obj in objs:
        t.split('object prep')
        ...
    
    t.split('cleanup')
    ... # Perform cleanup
    
    t.stop()
    
    t.results() prints
        setup 1 0.2  # setup was called once and took 0.2 seconds
        object prep 8 12.3  # this was called 8 times, totallying 12.3 seconds
        cleanup 1 4.1 # called once and took 4.1 seconds
    
    '''
    
    def __init__(self, key):
        self.start = time.time()
        self.key = key

    def _record(self):
        global _allTimers
        global _counts
        if self.key not in _allTimers:
            _allTimers[self.key] = 0.0
            _counts[self.key] = 0

        _counts[self.key] += 1

        _allTimers[self.key] += time.time() - self.start

    def split(self, key):
        self._record()
        self.start = time.time()
        self.key = key

    def stop(self):
        self._record()


    @staticmethod
    def results():
        global _allTimers
        global _counts

        for k, v in _allTimers.items():
            print(k, _counts[k], v)

    @staticmethod
    def clear():
        global _allTimers
        global _counts

        _allTimers.clear()
        _counts.clear()


class TimerBasic(object):
    
    def __init__(self, tag):
        self.tag = tag
        self.t = time.time()
    
    def ding(self, msg):
        print('#', self.tag, '#', msg, 'Elapsed:', time.time() - self.t)
        self.t = time.time()


class TimerAggregate(object):
    ''' Timer to aggregate results of several operations for comparing which is faster.
    '''
    
    fmt = '{} elapsed for {}'
    
    def __init__(self):
        self.results = []
    
    
    @contextmanager
    def run(self, msg):
        start = time.time()
        yield
        elapsed = time.time() - start
        print( self.fmt.format( elapsed, msg) )
        
        self.results.append( (elapsed, msg) )
        
    
    def report(self):
        print('Results, fastest to slowest')
        for elapsed, msg in sorted(self.results):
            print( self.fmt.format( elapsed, msg) )