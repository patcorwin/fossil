from __future__ import print_function, absolute_import

import os

from pymel.core import confirmDialog

from ._add import *  # noqa

from . import (
    anim,
    capi,
    constraints,
    dagObj,
    debug,
    factory,
    image,
    keyModifier,
    layer,
    math,
    names,
    pubsub,
    shader,
    shape,
    text,
    time,
    ui,
    weights,
)

from ._core import version, undoBlock

from ._lib import sharedShape  # noqa

from . import vendor

    
def _addIconPath():
    pdilIcons = os.path.normpath( os.path.normcase( os.path.dirname(__file__) + '/icons' ) )
    iconPaths = os.path.normpath( os.path.normcase( os.environ['XBMLANGPATH'] ) )
    
    if pdilIcons not in iconPaths:
        os.environ['XBMLANGPATH'] += ';' + pdilIcons


_addIconPath()


class core:
    
    class _alt:
        
        def __getattr__(self, member):
            confirmDialog(m="""Code was restructured and this function was moved,
(but I don't expect it to move again).

Please update shelf items.

If you're technically inclined, see the script editor for how to edit the code.
(It's actually pretty easy)

Sorry for the inconvenience.
""")
            print('---- How To Update ---')
            print('Remove "core" so "pdil.core.alt" becomes "pdil.alt".  That is it.')
            print('Sorry for the inconvenience.')
            return getattr(alt, member)

    alt = _alt()