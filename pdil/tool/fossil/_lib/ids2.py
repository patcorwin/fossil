'''
Additional specs that need multiple libraries to decode so live in lib instead of core.

Doesn't import anything, but on running loads all the specs
'''

import pdil

from .._core import config
from .._core import ids
from .._core import find
from .._lib import space

__all__ = []

class MainGroupSpec(ids.IdSpec):
    specType = 'fossil_main'
    version = (1, 0)

    @classmethod
    def getSpec(self, obj):
        spec = self.baseSpec(obj)
        
        if obj.hasAttr( config.FOSSIL_MAIN_CONTROL ):
            spec['idtype'] = self.specType
            return spec
                
        return None

    @classmethod
    def readSpec(self, spec):
        return find.mainGroup()
        
        
class TrueWorldSpec(ids.IdSpec):
    specType = 'fossil_true_world'
    version = (1, 0)

    @classmethod
    def getSpec(self, obj):
        spec = self.baseSpec(obj)
                
        if obj == space.getTrueWorld():
            spec['idtype'] = self.specType
            return spec
                
        return None

    @classmethod
    def readSpec(self, spec):
        return space.getTrueWorld()
        
        
class RootMotionSpec(ids.IdSpec):
    specType = 'fossil_root_motion'
    version = (1, 0)

    @classmethod
    def getSpec(self, obj):
        spec = self.baseSpec(obj)
                
        if pdil.shortName(obj) == 'rootMotion':
            spec['idtype'] = self.specType
            return spec
                
        return None

    @classmethod
    def readSpec(self, spec):
        return find.rootMotion()


class RootJointSpec(ids.IdSpec):
    specType = 'fossil_root_joint'
    version = (1, 0)

    @classmethod
    def getSpec(self, obj):
        spec = self.baseSpec(obj)
        
        if obj == find.rootBone():
            spec['idtype'] = self.specType
            return spec
                
        return None

    @classmethod
    def readSpec(self, spec):
        return find.rootBone()