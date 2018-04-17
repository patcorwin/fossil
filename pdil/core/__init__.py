from __future__ import absolute_import
import importlib
import os


# Load in alt and path for convenience use in other modules
from ..add import alt           # noqa
from ..add import path          # noqa

# Load all available python files
_thisDir = os.path.dirname(__file__)
for _f in os.listdir( _thisDir ):
    if os.path.isfile( _thisDir + '/' + _f) and _f.lower().endswith('.py'):
        globals()[_f[:-3]] = importlib.import_module('motiga.core.' + _f[:-3])