from collections import OrderedDict
import json
import operator

from pymel.core import cmds, objExists, PyNode

import pdil
from pdil.vendor import six

#from . import config


if '_specPlugins' not in globals():
    _specPlugins = OrderedDict()
    _inactiveSpecPlugins = OrderedDict()


def getIdSpec(obj):
    '''
    '''
    global _specPlugins
    for plugin in _specPlugins.values():
        spec = plugin[0].getSpec(obj)
        if spec:
            return spec
            
    return IdSpec.baseSpec(obj)
    
    
def readIdSpec(spec):
    global _specPlugins
    
    #if 'type' in spec: # At some point, say 2024, fully deprecate 'fossil_oldspec'
    #    spec['idtype'] = 'fossil_oldspec'
        
    readers = _specPlugins.get( spec['idtype'], (UnknownSpec,) )
    
    if 'ver' in spec:
        version = spec['ver']
        for reader in readers:
            if reader.version[0] == version[0]:
                break
        else:
            # &&& Is it sensible to default to the latest or error?
            reader = readers[0]
            print(reader, 'reader')
    else:
        reader = readers[0]
    
    # Finally, read the specialized spec but fallback to long, then short names if not found
    obj = reader.readSpec(spec)
    if not obj:
        if objExists(spec['long']):
            return PyNode(spec['long'])
        
        if objExists(spec['short']):
            return PyNode(spec['short'])
    
    return obj


_baseSpecType = 'unknown'


class RegisterSpec(type):
    def __init__(cls, name, bases, clsdict):
        global _specPlugins
        global _inactiveSpecPlugins
        
        if cls.specType != _baseSpecType:
            assert 'version' in clsdict, 'version (property to compare for latest version) not implemented on {}'.format(name)
            assert 'getSpec' in clsdict, 'getSpec(obj) (method taking obj and creating a dict) not implemented on {}'.format(name)
            assert 'readSpec' in clsdict, 'readSpec(spec) (method taking dict made from getSpec) not implemented on {}'.format(name)
            assert 'specType' in clsdict, 'specType (string) not implemented on {}'.format(name)
            
            if cls.specType not in _inactiveSpecPlugins:
                # Specs are listed so latest is first
                if cls.specType in _specPlugins:
                    for i, plugin in enumerate(_specPlugins[cls.specType]):
                        if plugin.version == cls.version:
                            _specPlugins[cls.specType][i] = cls
                            break
                    else:
                        _specPlugins[cls.specType].append( cls )
                        _specPlugins[cls.specType].sort(key=operator.attrgetter('version'), reverse=True)
                else:
                    _specPlugins[cls.specType] = [cls]
        
        super(RegisterSpec, cls).__init__(name, bases, clsdict)
    

class IdSpec(six.with_metaclass(RegisterSpec)):
    ''' Abstract Base Class for spec plugins.
    
    Create a dict, and read this dict to track objects by alternatives to names
    in case.  This allows things like a fossil card naming scheme to change but
    the correct joint is returned because the spec knows the card.
    '''
    
    specType = _baseSpecType
    version = (0, 0)
    
    @classmethod
    def getSpec(cls, obj):
        raise NotImplementedError()
    
    @classmethod
    def readSpec(cls, data):
        raise NotImplementedError()

    @classmethod
    def baseSpec(cls, obj):
        spec = OrderedDict()
        spec['idtype'] = _baseSpecType
        spec['short'] = pdil.shortName(obj)
        spec['long'] = obj.longName()
        spec['ver'] = cls.version
        return spec


class SubControllerSpec(IdSpec):
    specType = 'fossil_sub'
    version = (1, 0)
    
    @classmethod
    def getSpec(self, obj):
        spec = self.baseSpec(obj)
        if obj.__class__.__name__ == 'SubController':
            leadCtrl, key = obj.ownerInfo()
            
            spec['idtype'] = self.specType
            spec['lead'] = getIdSpec(leadCtrl)
            spec['subkey'] = key

            return spec
            
        return None
        
    @classmethod
    def readSpec(self, spec):
        if spec['idtype'] == self.specType:
            lead = readIdSpec( spec['lead'] )
            return lead.subControl[ spec['subkey'] ]
        
        return None
    
    
class RigControllerSpec(IdSpec):
    specType = 'fossil_lead'
    version = (1, 0)
    
    @classmethod
    def getSpec(self, obj):
        spec = self.baseSpec(obj)
        if obj.__class__.__name__ == 'RigController':
            spec['idtype'] = self.specType
            spec['motion'] = obj.getMotionKeys()
            spec['card'] = getIdSpec(obj.card)
            return spec
        
        return None
        
    @classmethod
    def readSpec(self, spec):
        if spec['idtype'] == self.specType:
            
            card = readIdSpec( spec['card'] )
            if not card:
                return None
            
            return card.getLeadControl( spec['motion'][0], spec['motion'][1] )
        
        return None


class CardSpec(IdSpec):
    specType = 'fossil_card'
    version = (1, 0)

    @classmethod
    def getSpec(self, obj):
        spec = self.baseSpec(obj)
        if obj.__class__.__name__ == 'Card':
            spec['idtype'] = self.specType
            
            _id = obj.rigData.get('id', None)
            if _id:
                spec['id'] = _id
            
            return spec
            
        return None
        
    @classmethod
    def readSpec(self, spec):
        
        if 'id' in spec:
            cards = cmds.ls( '*.fossilRigData', o=True, r=True, l=True )
            
            for card in cards:
                data = json.loads( cmds.getAttr( card + '.fossilRigData' ) )
                if spec['id'] == data.get('id', None):
                    return PyNode(card)
        return None


class BPJointSpec(IdSpec):
    specType = 'fossil_bpj'
    version = (1, 0)

    @classmethod
    def getSpec(self, obj):
        spec = self.baseSpec(obj)
        
        if obj.__class__.__name__ == 'BPJoint':
            spec['idtype'] = self.specType
            index = obj.card.joints.index(obj)
            spec['card'] = getIdSpec(obj.card)
            spec['index'] = index
                
            return spec
                
        return None

    @classmethod
    def readSpec(self, spec):
        card = readIdSpec( spec['card'] )
        bpj = card.joints[ spec['index'] ]
        return bpj


class JointSpec(IdSpec):
    specType = 'fossil_joint'
    version = (1, 0)

    @classmethod
    def getSpec(self, obj):
        spec = self.baseSpec(obj)
        
        for connection in obj.message.listConnections(p=True):
            if connection.node().__class__.__name__ == 'BPJoint':
                
                spec['idtype'] = self.specType
                spec['mirror'] = connection.attrName() == 'realJointMirror'
                bpj = connection.node()
                index = bpj.card.joints.index(bpj)
                spec['card'] = getIdSpec(bpj.card)
                spec['index'] = index
                    
                return spec
                
        return None

    @classmethod
    def readSpec(self, spec):
        card = readIdSpec( spec['card'] )
        bpj = card.joints[ spec['index'] ]
        
        if spec['mirror']:
            return bpj.realMirror
        else:
            return bpj.real


class RigNodeSpec(IdSpec):
    specType = 'fossil_rignode'
    version = (1, 0)
    
    @classmethod
    def getSpec(self, obj):
        spec = self.baseSpec(obj)
        
        if obj.hasAttr('fossilNodeData'):
            
            leadCtrl = obj.fossilNodeLink.listConnections()[0]
            
            spec['idtype'] = self.specType
            spec['lead'] = getIdSpec(leadCtrl)
            spec['node_name'] = pdil.factory.getJsonAttr(obj, 'fossilNodeData')['name']
            
            return spec
            
        return None
        
    @classmethod
    def readSpec(self, spec):
        if spec['idtype'] == self.specType:
            lead = readIdSpec( spec['lead'] )
            
            for plug in lead.message.listConnections(d=True, s=False, p=True):
                if plug.attrName() == 'fossilNodeLink':
                    if pdil.factory.getJsonAttr(plug.node(), 'fossilNodeData').get('name', None) == spec['node_name']:
                        return plug.node()
        
        return None


class UnknownSpec(IdSpec):
    ''' Does nothing so readIdSpec falls back to long and short names.
    '''
    specType = _baseSpecType
    version = (0, 0)
    
    @classmethod
    def getSpec(self, obj):
        return None
        
    @classmethod
    def readSpec(self, spec):
        return None