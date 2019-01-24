from __future__ import absolute_import
import importlib
import os

from pymel.core import about

# Load in alt and path for convenience use in other modules
from ..add import alt           # noqa
from ..add import path          # noqa

# Load all available python files
_thisDir = os.path.dirname(__file__)
for _f in os.listdir( _thisDir ):
    if os.path.isfile( _thisDir + '/' + _f) and _f.lower().endswith('.py'):
        globals()[_f[:-3]] = importlib.import_module('pdil.core.' + _f[:-3])


def version(includeBitVersion=False):
    '''
    Returns the year, and optionally a tuple of (year, bit)
    '''
    
    year = about(v=True)[:4]
    
    if includeBitVersion:
        return (int(year), 64 if about(v=True).count('x64') else 32  )
    else:
        return int(year)