'''
A collection of helper functions to construct pymel node factories (i.e. custom pynodes).

The main appeal is providing direct access (via *Access) instead of get/set, so it only
makes sense if the attribute isn't animatable.

Additionally there is a helper that allows connecting a single object and another
for automatically deserializing json strings.

ex:

    class MySpecialJoint(nt.Joint):
        
        @classmethod
        def _isVirtual(cls, obj, name):
            fn = pymel.api.MFnDependencyNode(obj)
            try:
                if fn.hasAttribute('fossilMirror'):
                    return True
            except:  # .hasAttribute doesn't actually return False but errors, lame.
                pass
            return False

        mirror  = SingleConnectionAccess('fossilMirror')
        data    = JsonAccess('fossilData')
        
    pymel.internal.factories.registerVirtualClass( MySpecialJoint )
    
    j = joint()
    j.addAttr('fossilMirror', at='message')
    j.addAttr('fossilData', dt='string')
    j = PyNode(j)  # Must recast to get identified as a MySpecialJoint
    
    someOtherJoint = joint()
    print( j.mirror )
    # Result: None
    
    j.mirror = someOtherJoint
    print( j.mirror )
    # Result: joint2
    
    j.mirror = None
    print( j.mirror )
    # Result: None
    
    print( j.data )
    # Result: {}
    
    j.data = {'canned': 'goods' }
    print( j.data, type(j.data) )
    # Result: {'canned': 'goods' } <type 'dict'>
    
    print( j.fossilData.get(), type(j.fossilData.get()) )
    # Result: {"canned": "goods"} <type 'unicode'>

'''

import collections
import contextlib
import json

from pymel.core import hasAttr
from pymel.core.general import PyNode

try:
    basestring
except NameError:
    basestring = str

__all__ = [
    'editAsJson',
    'getSingleConnection',
    'setSingleConnection',
    'getStringAttr',
    'setStringAttr',
    'setJsonAttr',
    'getJsonAttr',
    'messageAttr',
    'FakeAttribute',
    'DeprecatedAttr',
    'StringAccess',
    'SingleConnectionAccess',
    'SingleStringConnectionAccess',
    'Json',
    'JsonAccess',
    'IntAccess',
    'FloatAccess',
]


@contextlib.contextmanager
def editAsJson(plug):
    data = json.loads(plug.get(), object_pairs_hook=collections.OrderedDict)
    yield data
    plug.set( json.dumps(data) )
    

# Attribute access utilities --------------------------------------------------
# They all have to use .node() in case it's a sub attr, like sequence[0].data


def getSingleConnection(obj, attrName):
    '''
    If connected, return the single entry, otherwise none.
    '''
    if not obj.node().hasAttr(attrName):
        return None
    
    connections = obj.attr(attrName).listConnections()
    if connections:
        return connections[0]
    else:
        return None


def setSingleConnection(obj, attrName, value):
    if value:
        if isinstance(value, basestring):
            PyNode(value).message >> messageAttr( obj, attrName )
        else:
            value.message >> messageAttr( obj, attrName )
    else:
        if hasAttr(obj.node(), attrName):
            obj.attr(attrName).disconnect()


def _getSingleStringConnection(obj, attrName):
    '''
    If connected, return the single entry, otherwise checks if a string val is set, returning that.
    '''
    if not obj.node().hasAttr(attrName):
        return ''
    
    connections = obj.attr(attrName).listConnections()
    if connections:
        return connections[0]
    else:
        return obj.attr(attrName).get()


def _setSingleStringConnection(obj, attrName, value):
    if value:
        if isinstance(value, basestring):
            if obj.node().hasAttr(attrName) and obj.attr(attrName).listConnections():
                obj.attr(attrName).disconnect()
                
            setStringAttr(obj, attrName, value)
        else:
            setStringAttr(obj, attrName, None)
            value.message >> obj.attr( attrName )
    else:
        if hasAttr(obj.node(), attrName):
            obj.attr(attrName).disconnect()
            obj.attr(attrName).set('')


def getStringAttr(obj, attrName):
    if obj.node().hasAttr(attrName):
        return obj.attr(attrName).get()
    return ''


def setStringAttr(obj, attrName, val):
    if not obj.node().hasAttr(attrName):
        obj.addAttr( attrName, dt='string' )
    if val is not None:
        obj.attr(attrName).set(val)
    
    
def setJsonAttr(obj, attrName, val):
    setStringAttr(obj, attrName, json.dumps(val))


def getJsonAttr(obj, attrName, ):
    return json.loads( getStringAttr(obj, attrName), object_pairs_hook=collections.OrderedDict)


def _getIntAttr(obj, attrName):
    if obj.node().hasAttr(attrName):
        return obj.attr(attrName).get()
    return -666


def _setIntAttr(obj, attrName, val):
    if not obj.node().hasAttr(attrName):
        obj.addAttr( attrName, dt='long' )
    if val is not None:
        obj.attr(attrName).set(val)
    
    
def _getFloatAttr(obj, attrName):
    if obj.node().hasAttr(attrName):
        return obj.attr(attrName).get()
    return -666.666


def _setFloatAttr(obj, attrName, val):
    if not obj.node().hasAttr(attrName):
        obj.addAttr( attrName, dt='double' )
    if val is not None:
        obj.attr(attrName).set(val)
    
    
def messageAttr( obj, name ):
    '''
    Make the attribute if it doesn't exist and return it.
    '''
    
    if not obj.hasAttr( name ):
        obj.addAttr( name, at='message' )
    return obj.attr(name)


class FakeAttribute(object):
    
    def __init__(self, obj, getter, setter):
        self.obj = obj
        self.getter = getter
        self.setter = setter
    
    def get(self):
        return self.getter(self.obj)
        
    def set(self, val):
        self.setter(self.obj, val)


# Descriptors -----------------------------------------------------------------
class DeprecatedAttr(object):
    '''
    When a regular attribute has been replaced by something, allow for not
    fixing every code reference but route to the new data location.
    '''
    
    def __init__(self, getter, setter, mayaAttr=True):
        self.getter = getter
        self.setter = setter
        self.mayaAttr = mayaAttr
    
    def __get__(self, instance, owner):
        if self.mayaAttr:
            return FakeAttribute(instance, self.getter, self.setter)
        else:
            return self.getter(instance)

    def __set__(self, instance, value):
        # This is never legitimately called for maya attrs
        if not self.mayaAttr:
            self.setter(instance, value)


class StringAccess(object):
    '''
    Provides access to the attribute of the given name, defaulting to an
    empty string if the attribute doesn't exist.
    '''
    
    def __init__(self, attrname):
        self.attr = attrname
    
    def __get__(self, instance, owner):
        return getStringAttr(instance, self.attr)
    
    def __set__(self, instance, value):
        setStringAttr(instance, self.attr, value)
        

class SingleConnectionAccess(object):
    '''
    Returns the object connected to the given attribute, or None if the attr
    doesn't exist or isn't connected.
    '''
    
    def __init__(self, attrname):
        self.attr = attrname
    
    def __get__(self, instance, owner):
        return getSingleConnection(instance, self.attr)

    def __set__(self, instance, value):
        setSingleConnection(instance, self.attr, value)
            
            
class SingleStringConnectionAccess(object):
    '''
    Just like SingleConnection but is also a string for alternate values
    '''
    
    def __init__(self, attrname):
        self.attr = attrname
    
    def __get__(self, instance, owner):
        return _getSingleStringConnection(instance, self.attr)

    def __set__(self, instance, value):
        _setSingleStringConnection(instance, self.attr, value)


class Json(collections.OrderedDict):

    def __init__(self, data, node, attr):
        collections.OrderedDict.__init__(self, data)
        self._node = node
        self._attr = attr
    
    def __enter__(self):
        return self
    
    def __exit__(self, type, value, traceback):
        setStringAttr(self._node, self._attr, json.dumps(self))
        #self._node.attr(self._attr).set( json.dumps(self) )

       
class JsonAccess(object):
    '''
    Auto tranform json data to/from a string.  Call in `with` statement and edit
    the result to automatically assign the changes.
    '''
    
    def __init__(self, attrname, defaults={}):
        self.attr = attrname
        self.defaults = defaults
    
    def __get__(self, instance, owner):
        res = getStringAttr(instance, self.attr)
        if not res:
            return Json(self.defaults.copy(), instance, self.attr)
        return Json(json.loads(res, object_pairs_hook=collections.OrderedDict), instance, self.attr )
            
    def __set__(self, instance, value):
        setJsonAttr(instance, self.attr, value)


class IntAccess(object):
    '''
    Provides access to the attribute of the given name, defaulting to an
    empty string if the attribute doesn't exist.
    '''
    
    def __init__(self, attrname):
        self.attr = attrname
    
    def __get__(self, instance, owner):
        return _getIntAttr(instance, self.attr)
    
    def __set__(self, instance, value):
        _setIntAttr(instance, self.attr, value)
        
        
class FloatAccess(object):
    '''
    Provides access to the attribute of the given name, defaulting to an
    empty string if the attribute doesn't exist.
    '''
    
    def __init__(self, attrname):
        self.attr = attrname
    
    def __get__(self, instance, owner):
        return _getFloatAttr(instance, self.attr)
    
    def __set__(self, instance, value):
        _setFloatAttr(instance, self.attr, value)