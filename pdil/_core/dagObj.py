from pymel.core import currentUnit, createNode, parent, xform, dt, selected, move, spaceLocator, pointConstraint, distanceDimension, group, hide, PyNode

from .._add import alt, simpleName

try:
    basestring
except NameError:
    basestring = str

__all__ = [
    'Solo',
    'TempWorld',
    'TemporaryUnlock',
    'getPos',
    'getRot',
    'lock',
    'unlock',
    'distanceBetween',
    'measure',
    'matchPosByPivot',
    'moveTo',
    'matchTo',
    'align',
    'zero',
    'rezero',
]


class Solo(object):
    '''
    Context manager for temporarily unparenting any children an object might have.
    '''
    
    def __init__(self, obj):
        self.obj = obj
        
    def __enter__(self):
        self.children = self.obj.listRelatives(type='transform')
        if self.children:
            parent( self.children, w=True )
        
    def __exit__(self, type, value, traceback):
        if self.children:
            parent( self.children, self.obj )

            
class TempWorld(object):
    '''
    Context manager to temporarily put an object on the world level.
    '''
    
    def __init__(self, obj):
        self.obj = obj
        
    def __enter__(self):
        self.parent = self.obj.getParent()
        if self.parent:
            self.obj.setParent(w=True)
    
    def __exit__(self, type, value, traceback):
        if self.parent:
            self.obj.setParent(self.parent)


class TemporaryUnlock(object):
    '''
    Given an object, unlock and optionally zero out transforms, restoring them
    at the end.
    '''

    def __init__(self, obj, zero=True, trans=True, rot=True):
        self.obj = obj
        self.zero = zero
        self.trans = trans
        self.rot = rot
        
        self.relock = []
        self.prevTrans = None
        self.prevRot = None

    def __enter__(self):
        self.relock = []
        
        if self.trans:
            self.prevTrans = self.obj.t.get()
            
            for a in 'xyz':
                attr = self.obj.attr( 't' + a )
                if attr.isLocked():
                    self.relock.append(attr)
                    attr.unlock()
                if self.zero:
                    attr.set(0)

        if self.rot:
            self.prevRot = self.obj.r.get()
            
            for a in 'xyz':
                attr = self.obj.attr( 'r' + a )
                if attr.isLocked():
                    self.relock.append(attr)
                    attr.unlock()
                if self.zero:
                    attr.set(0)
                
    def __exit__(self, type, value, traceback):
        if self.trans:
            self.obj.t.set(self.prevTrans)
        if self.rot:
            self.obj.r.set(self.prevRot)
        
        for attr in self.relock:
            attr.lock()


def getPos( obj ):
    ''' Get worldspace position '''
    return dt.Vector( xform( obj, q=True, ws=True, t=True ) )


def getRot( obj ):
    ''' Get worldspace rotation '''
    return dt.Vector( xform( obj, q=True, ws=True, ro=True ) )

            
def lockRot(obj, hide=True):
    [ (obj.attr('r' + a).lock(), obj.attr('r' + a).setKeyable(False), obj.attr('r' + a).showInChannelBox(not hide)) for a in 'xyz' ]
    return obj

            
def lockTrans(obj, hide=True):
    [ (obj.attr('t' + a).lock(), obj.attr('t' + a).setKeyable(False), obj.attr('t' + a).showInChannelBox(not hide)) for a in 'xyz' ]
    return obj


def lockScale(obj, hide=True):
    [ (obj.attr('s' + a).lock(), obj.attr('s' + a).setKeyable(False), obj.attr('s' + a).showInChannelBox(not hide)) for a in 'xyz' ]
    return obj


def lockAll(obj, hide=True):
    lockRot(obj, hide=hide)
    lockTrans(obj, hide=hide)
    lockScale(obj, hide=hide)
    return obj


def lock(obj, attrs='t r s'):
    ''' Streamlined way of locking attrs.  Ex, `lock(obj)` locks all, `lock(obj, 'tx')` or `lock(obj, 'ty r s')`
    '''

    validAttrs = ['t', 'r', 's'] + [t + a for t in 'trs' for a in 'xyz']
    
    for attr in attrs.split():
        assert attr in validAttrs, 'Only transforms can be locked, not "%s"' % attr
        if attr in 'trs': # setKeyable doesn't work on compound attr
            for axis in 'xyz':
                obj.attr(attr + axis).lock()
                obj.attr(attr + axis).setKeyable(False)
                obj.attr(attr + axis).showInChannelBox(False)
        else:
            obj.attr(attr).lock()
            obj.attr(attr).setKeyable(False)
            obj.attr(attr).showInChannelBox(False)


@alt.name('Unlock Transform')
def unlock(objs=None):
    if not objs:
        objs = selected()
    
    # Convert input to a list if needed
    if isinstance(objs, PyNode):
        objs = [objs]
    elif isinstance(objs, basestring):
        objs = [PyNode(objs)]
    
    for obj in objs:
        for t in 'trs':
            obj.attr(t).unlock()
            for a in 'xyz':
                obj.attr(t + a).unlock()
                if not obj.attr(t + a).isKeyable():
                    obj.attr(t + a).showInChannelBox(True)


def distanceBetween(a, b):
    '''
    Returns the world space distance between two objects
    '''
    dist = dt.Vector(xform(a, q=True, ws=True, t=True)) - dt.Vector(xform(b, q=True, ws=True, t=True))
    return dist.length()


cmTo = {
    'in': 1 / 2.54,
    'ft': 1 / 30.48,
    'yd': 1 / 91.44,
    'mi': 1 / (30.48 * 5280),
    
    'mm': 10.0,
    'm': 0.01,
    'km': 0.00001,
}


def measure( start, end, name='measureLocs'):
    ''' Returns (distance plug, distanceNode, locator group).
    '''
    
    a = spaceLocator()
    pointConstraint( start, a )
    
    b = spaceLocator()
    pointConstraint( end, b )
    
    dist = distanceDimension( a, b )
    
    units = currentUnit(q=True)
    if units != 'cm':
        mult = createNode('multiplyDivide')
        mult.operation.set( 1 )
        mult.rename('convertCmTo%s' % units)
        dist.distance >> mult.input1X
        mult.input2X.set(cmTo[units])
        
        distPlug = mult.outputX
    else:
        distPlug = dist.distance
        
    hide( a, b, dist)

    grp = group(em=True, name=name)
    grp.inheritsTransform.set(False)
    a.setParent(grp)
    b.setParent(grp)
        
    return distPlug, dist.getParent(), grp

                    
def matchPosByPivot(dest, src):
    pos = xform(src, q=True, ws=True, rp=True)
    move( dest, pos, rpr=True, ws=True )
    
    
def moveTo(recipient, posOrObj):
    '''
    Move the object to the give position or object.
    '''
            
    if isinstance(posOrObj, (str, PyNode)):
        pos = xform(posOrObj, q=True, ws=True, t=True)
    else:
        pos = posOrObj
    
    xform( recipient, ws=True, t=pos )


def matchTo(dest, src, byPivot=False):
    '''
    Move the dest to the position and rotation of the src.
    '''
    if byPivot:
        matchPosByPivot(dest, src)
    else:
        # Pymel keeps changing if this returns 6 numbers or 2 vectors, boo!
        temp = src.getPivots(ws=True)
        if len(temp) == 2:
            trans = temp[0]
        else:
            trans = temp[:3]

        dest.setTranslation( trans, space='world' )
    
    dest.setRotation( src.getRotation(space='world'), space='world' )


#------------------------------------------------------------------------------
'''
Created for rig use, these can provide "cleaned" transform values by making groups.
'''
    

def _contain(obj, suffix, name='', make=True):
    '''
    Make a group around the given object zeroing out its transform.
    ..  todo::
        I think I want to lock and unkey spaces (though keep displayable in attr ed)
    '''
    
    if obj.getParent():
        if obj.getParent().name().endswith(suffix):
            return obj.getParent()
    
    if not make:
        return None
    
    if not name:
        name = simpleName(obj, format='{0}' + suffix)
    else:
        name += suffix
    
    grp = group(em=True)
    matchTo( grp, obj )
    
    if obj.getParent():
        grp.setParent( obj.getParent() )
        
    obj.setParent( grp )
    grp.rename( name )  # Name last instead of on create to hopefully avoid conflicts.
    
    return grp


def align(obj, make=False):
    return _contain(obj, '_align', make=make)


def zero(obj, apply=True, make=True):
    '''
    Wraps the given object in an align and space group.  If apply=False, no
    values are altered, it simply returns the space group.
    '''
    alignGrp = align(obj, make=make)
    if not alignGrp and not make:
        return None
    
    spaceGrp = _contain(alignGrp, '_space', simpleName(obj), make=make)
    if not spaceGrp and not make:
        return None
    
    if apply:
        rezero(obj)
    return spaceGrp


def rezero(obj):
    '''
    The given object, if not already, will get wrapped in an align group so it's
    transforms will be zeroed out.
    '''
    align = obj.getParent()
    if not align:
        return
        
    if not align.name().endswith( '_align' ):
        return
        
    obj.setParent(align.getParent())
    align.t.set( obj.t.get() )
    align.r.set( obj.r.get() )
    obj.setParent( align )
