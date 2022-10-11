# fossileNodes defines pymel factories that fossil needs, so make sure it is loaded.
from ...nodeApi import fossilNodes  # noqa

from ._core import config # noqa
from ._core import find # noqa
from ._core import ids # noqa
from ._lib import boneGroups # noqa
from ._lib.ids2 import * # noqa Adds nothing to namespace but registers additional IdSpecs
from ._lib import proxyskel # noqa Probably not actually needed here
from ._lib import space # noqa
from ._lib import visNode # noqa
from ._lib import tpose # noqa
from ._lib2 import card # noqa
from ._lib2 import controllerShape # noqa

from . import node # noqa

from .enums import * # noqa

# Load the rigging components
from .rigging import ctrlGroup # noqa
from .rigging import dogFrontLeg # noqa
from .rigging import dogHindLeg # noqa
from .rigging import fkChain # noqa
from .rigging import foot # noqa
from .rigging import freeform # noqa
from .rigging import ikChain # noqa
from .rigging import splineChest # noqa
from .rigging import splineNeck # noqa
from .rigging import splineTwist # noqa
from .rigging import squashStretch # noqa
from .rigging import surfaceFollow # noqa
from .rigging import twistHelper # noqa