from __future__ import absolute_import
import contextlib

from pymel.core import about
from maya import cmds

from . import capi  # noqa
from . import constraints  # noqa
from . import dagObj  # noqa
from . import debug  # noqa
from . import factory  # noqa
from . import image  # noqa
from . import keyModifier  # noqa
from . import layer  # noqa
from . import math  # noqa
from . import names  # noqa
from . import pubsub  # noqa
from . import shader  # noqa
from . import shape  # noqa
from . import text  # noqa
from . import time  # noqa
from . import ui  # noqa
from . import weights  # noqa


def version(includeBitVersion=False):
    '''
    Returns the year, and optionally a tuple of (year, bit)
    '''
    
    year = about(v=True)[:4]
    
    if includeBitVersion:
        return (int(year), 64 if about(v=True).count('x64') else 32  )
    else:
        return int(year)
        

@contextlib.contextmanager
def undoBlock(name=''):
    if name:
        cmds.undoInfo(openChunk=True, chunkName=name)
    else:
        cmds.undoInfo(openChunk=True)
    
    yield
    
    cmds.undoInfo(closeChunk=True)