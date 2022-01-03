''' CANNOT DO THIS YET, cycle errors with importing MetaControl
from . import ctrlGroup # noqa
from . import dogHindLeg # noqa
from . import foot # noqa
from . import freeform # noqa
from . import ikChain # noqa
from . import splineChest # noqa
from . import splineNeck # noqa
from . import splineTwist # noqa
from . import squashStretch # noqa
from . import surfaceFollow # noqa
from . import twistHelper # noqa
'''


'''
TODO: Clearify how each rig has a list of criteria so it's easy to test if rigging will actually work or not.

These sub modules are where rigs are actually made.

When defining controls, they must all follow this pattern:

```python
@defaultspec( {'shape': control.box,    'size': 10, 'color':'green 0.22' },
           pv={'shape': control.sphere, 'size': 5,  'color':'green 0.92' } )

def someControl(startJoint, endJoint, <keyword Args altering behavior>, name='', groupName='', controlSpec={} ):

    return control, container

```

Args:
`name`: (Likely for most IkControls only) will be name of the control, respecting the suffix.

`groupName`: The optional subgroup the control parts be put under, purely for organization.
    It falls back to the visGroup of the 'main' controller.
`controlSpec`: will be filled and can have parts overridden.  This works
    in conjunction with the `defaultspec` decorator
    
Returns:
`control` is the 'main' control.  Additional controls get added it it
    via control.subControl['some name'] = other control.

`container` is the group that is made to hold all the junk under the main controller.
    
'''