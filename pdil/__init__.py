from __future__ import print_function, absolute_import

import os

from pymel.core import confirmDialog

from ._add import *  # noqa
from ._core import *  # noqa
from ._lib import *  # noqa

    
def _addIconPath():
    pdilIcons = os.path.normpath( os.path.normcase( os.path.dirname(__file__) + '/icons' ) )
    iconPaths = os.path.normpath( os.path.normcase( os.environ['XBMLANGPATH'] ) )
    
    if pdilIcons not in iconPaths:
        os.environ['XBMLANGPATH'] += ';' + pdilIcons


_addIconPath()


class core:
    
    class _alt:
        
        def __getattr__(self, member):
            confirmDialog(m="""Code was restructed and this function was moved,
(but I don't expect it to move again).

Please update shelf icons.

If you're technically inclined, see the script editor for how to edit the code.
(It's actually pretty easy)

Sorry for the inconvenience.
""")
            print('---- How To Update ---')
            print('Remove "core" from "pdil.core.alt" so it is just "pdil.alt".  That is it.')
            print('Sorry for the inconvenience.')
            return getattr(alt, member)

    alt = _alt()