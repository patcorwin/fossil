from __future__ import print_function, absolute_import

from pymel.core import addAttr, cmds, currentTime, group, hide, keyframe, filterCurve, parentConstraint, orientConstraint, pointConstraint, listRelatives, xform, duplicate

import pdil

from ..._core import find
from ..._core import ids
from ... import enums
from ... import node

__all__ = ['getNames', 'setNames', 'get', 'ENUM_ATTR', 'SPACE_TYPE_NAME']


globalSettings = pdil.ui.Settings(
    "space switching",
    {
        "autoEuler": False,
        "singleSwitchEuler": False,
    })


ENUM_ATTR = 'space'
SPACE_TYPE_NAME = 'spaceTypeName'


def isBidirectional(ctrl):
    if not ctrl.hasAttr('space'):
        return False
        
    for cond in ctrl.space.listConnections(type='choice'):
        return True
        #if cond.hasAttr('fossilData') and cond.fossilData.get() == 'bidirectional':
        #    return True
    return False
    

def get(ctrl):
    ''' Returns the name of the current space.
    '''
    return getNames(ctrl)[ctrl.attr(ENUM_ATTR).get()]


def getNames(ctrl):
    ''' Returns a list of the spaces a control has.
    '''
    if not ctrl.hasAttr(ENUM_ATTR):
        return []
        
    return cmds.addAttr( ctrl.attr(ENUM_ATTR).name(), q=True, enumName=True ).split(':')


def setNames(ctrl, names):
    '''
    Updates the enum names and storage of the names.
    '''
    addAttr( ctrl.attr(ENUM_ATTR), e=True, enumName=':'.join(names) )
    

def toCamel(s):
    return s.title().replace('_', '')


def getGroup(modeName, main=None, checkOnly=False):
    ''' Returns the group that contains the space's proxy target, i.e. the node the zero space is actually constrained to.
    
    Args:
        modeName: str = One of the target modes, ex: 'PARENT', 'POINT_ORIENT', etc.
        main: PyNode = The main controller in case the scene has multiple.
        checkOnly: bool = If True, won't build the space and returns None if not found.
    '''
    modeName = toCamel(modeName)
    if not main:
        main = find.mainGroup()
    
    for child in main.listRelatives():
        if pdil.simpleName(child) == '__spaces__':
            spaceContainer = child
            break
    else:
        spaceContainer = group(em=True, n='__spaces__', p=main)
        hide(spaceContainer)
        
    for child in spaceContainer.listRelatives():
        if pdil.simpleName(child) == modeName:
            spaceGroup = child
            break
    else:
        if checkOnly:
            return None
        else:
            spaceGroup = group(em=True, name=modeName, p=spaceContainer)
    
    return spaceGroup


def switchRange(control, targetSpace, range=(None, None)):
    '''
    Switch the `control` into the targetSpace across the given range
    (includes) endpoints.  This alters the keyframes
    '''
    attrs = [ENUM_ATTR] + [t + a for t in 'tr' for a in 'xyz']
    curTime = currentTime(q=True)
    times = keyframe( control, at=attrs, q=True, tc=True)
    times = sorted(set(times))
    if range[0] is not None and range[1] is not None:
        times = [ t for t in times if range[0] <= t <= range[1] ]
    elif range[0]:
        times = [ t for t in times if range[0] <= t ]
    elif range[1]:
        times = [ t for t in times if t <= range[1] ]
    
    if not times:
        switchToSpace( control, targetSpace )
        return
    
    # Set initial keys if needed so insert=True works later
    for attr in attrs:
        if not keyframe( control.attr(attr), q=True, tc=True ):
            control.attr(attr).setKey(t=times[0])
            control.attr(attr).setKey(t=times[-1])
    
    for t in times:
        control.t.setKey(insert=True, t=t )
        control.r.setKey(insert=True, t=t )
        control.attr(ENUM_ATTR).setKey(insert=True, t=t )
        
    for t in times:
        currentTime(t)
        
        switchToSpace( control, targetSpace )
        
        control.attr( ENUM_ATTR ).setKey()
        control.t.setKey()
        control.r.setKey()
        
    currentTime(curTime)
    
    if globalSettings.autoEuler:
        filterCurve(control)


def switchFrame(control, targetSpace):
    '''
    Space switch a single frame.
    '''
    switchToSpace(control, targetSpace )
    if globalSettings.singleSwitchEuler:
        filterCurve(control)


def switchToSpace(control, targetSpace ):
    '''
    Switches the control to the give targetSpace at the current time, no
    keys are altered.
    '''
    trans = control.getTranslation( space='world' )
    rot = control.getRotation( space='world' )
    
    control.attr( ENUM_ATTR ).set( targetSpace )
    
    control.setTranslation( trans, space='world' )
    control.setRotation( rot, space='world' )
    
    
def getTrueWorld():
    ''' Make a node that stays in world space.
    '''
    main = find.mainGroup()
    if not main:
        return None
    
    for child in main.listRelatives():
        if pdil.shortName(child) == 'trueWorld':
            return child
    
    grp = group(em=True, name='trueWorld')
    for t in 'trs':
        for a in 'xyz':
            grp.attr( t + a).setKeyable(False)
            
    hide(grp)
    grp.setParent( main )
    grp.inheritsTransform.set(False)
    
    return grp
    

class Mode(object):
    '''
    HOW TO ADD NEW MODES

    1) Add an enum to the list
    2) Add a class with the enum name
        a) It must define two functions:
            @staticmethod
            def build(target, spaceName, spaceContainer, rotateTarget, control, space):

            @staticmethod
            def getTargets(target):

        `build()` is used by `add()` and `getTargets()` by `getTargetInfo()`

        getTargets() must return
            target(s), extra info?, constraint if needed by a MULTI space
            IF there are multiple targets, it MUST be a tuple so serialize recognizes it.

    3) If adding multi space, edit `deserializeSpaces()` to recognize it.

    '''
    EXTERNAL = 'EXTERNAL'               # Here for taking advantage of the get group code.
    ROTATE_TRANSLATE = 'ROTATE_TRANSLATE'    # Acts just like a child of the target
    TRANSLATE = 'TRANSLATE'             # If the target translates, it follows but not if the target rotates
    ROTATE = 'ROTATE'                   # Only follows rotation, not translation.  Probably only ever for rotate only controls
    ALT_ROTATE = 'ALT_ROTATE'           # Acts as a child of the target positionally but is rotationally follows the second target

    POINT_ORIENT = 'POINT_ORIENT'       # Does a point and orient, which is only relevant if doing non-enum attr
    DUAL_PARENT = 'DUAL_PARENT'         # ParentConstraint to two objs
    DUAL_FOLLOW = 'DUAL_FOLLOW'         # A point and orient to two objs (aka position is alway linearly interpreted between points regardless of target rotation)
    MULTI_PARENT = 'MULTI_PARENT'       # The base of a "rivet"
    MULTI_ORIENT = 'MULTI_ORIENT'       # Only has an orient constraint

    FREEFORM = 'FREEFORM'               # Allows several targets in different configurations, I do what I want!
    USER = 'USER'                       # User constrains this object as needed
    POINT_ROT = 'POINT_ROT'             # Point rotate

    _classmap = {}

    @classmethod
    def build(cls, modeName, *args, **kwargs):
        return cls._classmap[ getattr(cls, modeName) ].build(*args, **kwargs)

    @classmethod
    def getTargets(cls, mode, *args, **kwargs):
        if not isinstance(mode, int): # 21-11-22 I suspect this will all need to be replumbed for string and I should push conversion higher up.
            return cls._classmap[ getattr(cls, mode) ].getTargets(*args, **kwargs)
            
        return cls._classmap[mode].getTargets(*args, **kwargs)


class RegisterSpaceMode(type):
    def __init__(cls, name, bases, clsdict):
        
        Mode._classmap[name] = cls
        super(RegisterSpaceMode, cls).__init__(name, bases, clsdict)


class Space(pdil.vendor.six.with_metaclass(RegisterSpaceMode)):
    pass


class ROTATE_TRANSLATE(Space):

    @staticmethod
    def build(target, spaceName, spaceContainer, rotateTarget, control, space):
        return target, spaceName

    @staticmethod
    def getTargets(target):
        extra = None
        constraint = None
        return target, extra, constraint


class USER(Space):

    @staticmethod
    def build(target, spaceName, spaceContainer, rotateTarget, control, space):
        #trueTarget = group(em=True, name=pdil.simpleName(control) + '_' + spaceName)
        #trueTarget.setParent( getGroup('USER_TARGET') )
        return target, spaceName

    @staticmethod
    def getTargets(target):
        mainData = pdil.constraints.fullSerialize(target, ids.getIdSpec)
        alignData = pdil.constraints.fullSerialize(target.getParent(), ids.getIdSpec)
        extra = {'main': mainData if mainData else {},
                'align': alignData if alignData else {} }
        #extra = None
        constraint = None
        return target, extra, constraint


class TRANSLATE(Space):

    @staticmethod
    def build(target, spaceName, spaceContainer, rotateTarget, control, space):
        if not spaceName:
            spaceName = pdil.simpleName(target) + '_pos'
    
        for child in spaceContainer.listRelatives():
            if target in pointConstraint(child, q=True, tl=True):
                trueTarget = child
                break
        else:
            trueTarget = group(em=True, name=pdil.simpleName(target, '{0}_posOnly'), p=spaceContainer)
            pointConstraint( target, trueTarget )

        return trueTarget, spaceName

    @staticmethod
    def getTargets(target):
        target = pointConstraint(target, q=True, tl=True)[0]
        extra = None
        constraint = None
        return target, extra, constraint
    

class ROTATE(Space):

    @staticmethod
    def build(target, spaceName, spaceContainer, rotateTarget, control, space):
        if not spaceName:
            spaceName = pdil.simpleName(target) + '_rot'

        trueTarget = group(em=True, name=pdil.simpleName(target, '{0}_rotOnly'), p=spaceContainer)
        
        xform( trueTarget, ws=1, t=xform(control, q=True, ws=True, t=True))
        
        # parentConstraint translate to it's parent so it remains in position and lets us do a full parentConstraint later
        parentConstraint( space.getParent(), trueTarget, mo=True, sr=['x', 'y', 'z'] )
        
        parentConstraint( target, trueTarget, mo=True, st=['x', 'y', 'z'] )

        return trueTarget, spaceName

    @staticmethod
    def getTargets(target):
        target = parentConstraint(target.rx.listConnections(s=True)[0], q=True, tl=True)[0]
        extra = None
        constraint = None
        return target, extra, constraint
    

class ALT_ROTATE(Space):

    @staticmethod
    def build(target, spaceName, spaceContainer, rotateTarget, control, space):
        if not spaceName:
            spaceName = pdil.simpleName(target) + '_altRot'
            
        trueTarget = group(em=True, name=pdil.simpleName(target, '{0}_split'), p=spaceContainer)
        
        xform( trueTarget, ws=1, t=xform(control, q=True, ws=True, t=True))
        
        trans = parentConstraint( target, trueTarget, mo=True, sr=['x', 'y', 'z'] )
        
        # An explicit target can be given, otherwise it ends up being the main controller in effect.
        if rotateTarget:
            rot = parentConstraint( rotateTarget, trueTarget, mo=True, st=['x', 'y', 'z'] )
            trans.addAttr('transTarget', at='bool', dv=True)
            rot.addAttr('rotTarget', at='bool', dv=True)

        return trueTarget, spaceName

    @staticmethod
    def getTargets(target):
        constraints = listRelatives(target, type='parentConstraint')
        if len(constraints) == 1:
            target = parentConstraint(target, q=True, tl=True)[0]
        else:
            rot, trans = constraints if constraints[0].hasAttr('rotTarget') else (constraints[1], constraints[0])
            target = (  parentConstraint(trans, q=True, tl=True)[0],
                        parentConstraint(rot, q=True, tl=True)[0])
        extra = None
        constraint = None
        return target, extra, constraint
        

class DUAL_PARENT(Space):

    @staticmethod
    def build(target, spaceName, spaceContainer, rotateTarget, control, space):
        if not spaceName:
            spaceName = pdil.simpleName(target) + '_' + pdil.simpleName(rotateTarget) + '_parent'
        
        trueTarget = group(em=True, name=pdil.simpleName(target, '{0}_dualParent'), p=spaceContainer)
        pdil.dagObj.matchTo(trueTarget, control)
        
        # parentConstraint doesn't actually respect maintainOffset regarding rotation
        parentConstraint( [target, rotateTarget], trueTarget, mo=True, sr=['x', 'y', 'z'] )
        orientConstraint( [target, rotateTarget], trueTarget, mo=True )

        return trueTarget, spaceName

    @staticmethod
    def getTargets(target):
        constraints = listRelatives(target, type='parentConstraint')
        target = tuple(parentConstraint(constraints[0], q=True, tl=True))
        extra = None
        constraint = None
        return target, extra, constraint


class DUAL_FOLLOW(Space):

    @staticmethod
    def build(target, spaceName, spaceContainer, rotateTarget, control, space):
        if not spaceName:
            spaceName = pdil.simpleName(target) + '_' + pdil.simpleName(rotateTarget) + '_follow'
        trueTarget = group(em=True, name=pdil.simpleName(target, '{0}_dualFollow'), p=spaceContainer)
        pdil.dagObj.matchTo(trueTarget, control)
        pointConstraint( target, rotateTarget, trueTarget, mo=True )
        orientConstraint( target, rotateTarget, trueTarget, mo=True )

        return trueTarget, spaceName

    @staticmethod
    def getTargets(target):
        constraints = listRelatives(target, type='pointConstraint')
        target = tuple(pointConstraint(constraints[0], q=True, tl=True))
        extra = None
        constraint = None
        return target, extra, constraint


class MULTI_PARENT(Space):

    @staticmethod
    def build(target, spaceName, spaceContainer, rotateTarget, control, space):
        #  In this mode, target is a list of targets and rotateTarget is an optional list of weights
        if not spaceName:
            #spaceName = pdil.simpleName(target) + '_' + pdil.simpleName(rotateTarget) + '_follow'
            spaceName = 'multi_parent'
            
        trueTarget = group(em=True, name=pdil.simpleName(target[0], '{0}_multiParent'), p=spaceContainer)
        
        pdil.dagObj.matchTo(trueTarget, control)  # It's actually important so this can follow correctly.

        proxies = []
        for t in target:
            d = duplicate(trueTarget)[0]
            d.rename( d.name() + '_' + pdil.simpleName(t) )
            parentConstraint(t, d, mo=True)
            proxies.append(d)

        constraint = parentConstraint( proxies, trueTarget, mo=True )
        constraint.interpType.set(2)  # Shorted rotation is probably the most stable
        
        if rotateTarget:
            attrs = constraint.getWeightAliasList()
            for v, attr in zip(rotateTarget, attrs):
                attr.set(v)

        return trueTarget, spaceName

    @staticmethod
    def getTargets(target):
        constraints = listRelatives(target, type='parentConstraint')
        temp = tuple(parentConstraint(constraints[0], q=True, tl=True))
        
        # MULTI_PARENT has proxies rotated like the dest to help prevent flipping
        target = []
        for t in temp:
            target.append(parentConstraint(t, q=True, tl=True)[0])
        target = tuple(target)
        
        extra = [a.get() for a in constraints[0].getWeightAliasList()]
        return target, extra, constraints[0]


class MULTI_ORIENT(Space):
    @staticmethod
    def build(target, spaceName, spaceContainer, rotateTarget, control, space):
        #  In this mode, target is a list of targets and rotateTarget is an optional list of weights
        if not spaceName:
            spaceName = 'multi_orient'

        trueTarget = group(em=True, name=pdil.simpleName(control, '{0}_multiOrient'), p=spaceContainer)
        
        pdil.dagObj.matchTo(trueTarget, control)  # It's actually important so this can follow correctly.

        proxies = []
        for t in target:
            d = duplicate(trueTarget)[0]
            orientConstraint(t, d, mo=True)
            proxies.append(d)

            # Turn of inheritTransform so we can place it under the trueTarget to keep things tidy w/o cycle errors
            d.inheritsTransform.set(0)
            d.setParent(trueTarget)

        #constraint = orientConstraint( proxies, trueTarget, mo=True )
        #constraint.interpType.set(2)  # Shorted rotation is probably the most stable
        constraint = parentConstraint( proxies, trueTarget, mo=True, st=['x', 'y', 'z'] )
        constraint.addAttr('rotTarget', at='bool', dv=True)
        constraint.interpType.set(2)

        if rotateTarget:
            attrs = constraint.getWeightAliasList()
            for v, attr in zip(rotateTarget, attrs):
                attr.set(v)

        # parentConstraint translate to it's parent so it remains in position and lets us do a full parentConstraint later
        parentConstraint( space.getParent(), trueTarget, mo=True, sr=['x', 'y', 'z'] )

        return trueTarget, spaceName

    @staticmethod
    def getTargets(target):
        constraints = listRelatives(target, type='parentConstraint')
        rotConst = constraints[0] if constraints[0].hasAttr('rotTarget') else constraints[1]

        temp = tuple(parentConstraint(rotConst, q=True, tl=True))
        
        # MULTI_ORIENT has proxies rotated like the dest to help prevent flipping
        target = []
        for t in temp:
            target.append(orientConstraint(t, q=True, tl=True)[0])
        target = tuple(target)
        
        extra = [a.get() for a in rotConst.getWeightAliasList()]
        return target, extra, rotConst


# &&& Is this space actually needed?  I think it's a failed experiment
class POINT_ROT(Space):
    DEFAULT_SPACENAME = 'multi_pointOrient'
    
    @classmethod
    def build(cls, target, spaceName, spaceContainer, constraintWeights, control, space):
        '''  In this mode, target is a list of targets and constraintWeights is an optional list of weights
        Args:
            target: List of targets, but the first is the "fallback" space use to move the whole system
            constraintWegiths: Optional dict of weights for the constraints {'points': [p1, p2, p3], 'orients': [o1, o2, o3]}
        '''
        if not spaceName:
            spaceName = cls.DEFAULT_SPACENAME
        wrapper = group(em=True, name=pdil.simpleName(control, '{0}_wrapMultiPR'), p=spaceContainer)
        #pdil.dagObj.matchTo(wrapper, PyNode(target[0]))  # Not sure if this actually matters
        parentConstraint(target[0], wrapper)
        trueTarget = group(em=True, name=pdil.simpleName(control, '{0}_multiPR'), p=wrapper)
        pdil.dagObj.matchTo(trueTarget, control)  # It's actually important so this can follow correctly.
        if constraintWeights:
            points = constraintWeights.get( 'points', [1.0] * (len(target) - 1) )
            orients = constraintWeights.get( 'orients', [1.0] * (len(target) - 1) )
        else:
            points = [1.0] * (len(target) - 1)
            orients = [1.0] * (len(target) - 1)
        for t, p, o in zip(target[1:], points, orients):
            oc = orientConstraint(t, trueTarget, w=o, mo=True)
            pointConstraint(t, trueTarget, w=p, mo=True)
        oc.interpType.set(2)
        return trueTarget, spaceName
        
    @staticmethod
    def getTargets(target):
        oConst = target.listRelatives(type='orientConstraint')[0]
        pConst = target.listRelatives(type='pointConstraint')[0]
        targets = oConst.getTargetList()
        #wrapper = pdil.constraints.getParentConstrainee( target.getParent() )
        wrapper = parentConstraint(target.getParent(), q=True, tl=True)[0]
        targets.insert(0, wrapper)
        #rotConst = constraints[0] if constraints[0].hasAttr('rotTarget') else constraints[1]
        #temp = tuple(parentConstraint(rotConst, q=True, tl=True))
        extra = {
            'point': [a.get() for a in pConst.getWeightAliasList()],
            'orient': [a.get() for a in oConst.getWeightAliasList()]
        }
        return tuple(targets), extra, (oConst, pConst)


class FREEFORM(Space):
    ORIENT = 0
    POINT = 1
    PARENT = 2
    POINT_ORIENT = 3
    PARENT_TRANS = 4

    debugMode = {
        ORIENT: 'ORIENT',
        POINT: 'POINT',
        PARENT: 'PARENT',
        POINT_ORIENT: 'POINT_ORIENT',
        PARENT_TRANS: 'PARENT_TRANS'
    }

    constMap = {
        ORIENT: orientConstraint,
        POINT: pointConstraint,
        PARENT: parentConstraint,
    }

    @staticmethod
    def getProxy(control):
        '''
        If there are no rotate targets specified, make one to either the
        parent joint if it's FK or the lead joint of the card if IK


        ..  todo::
            In swift, these fail:
                Wrist_RTwist Wing_F_Connect_ctrl Wing_D_Base_ctrl main rootMotion
                Which are probably Twist and main/root motion
                (Groups are dealt with)

            These should be handled gracefully in some way
        '''

        main = node.leadController(control)

        if main:
            if main.getMotionKeys() == 'ik':

                if main.getSide() == 'Center' or (main.card.rigData.get('mirrorCode', '').title() == main.getSide()):
                    parentProxy = main.card.start().real.getParent()

                else:
                    parentProxy = main.card.start().realMirror.getParent()

            else:
                if main.card.rigData.get( enums.RigData.rigCmd ) == 'Group':
                    parentProxy = parentConstraint(main.container, q=True, tl=True)[0]
                else:
                    parentProxy = pdil.constraints.getOrientConstrainee(control).getParent()

        return parentProxy

    @classmethod
    def build(cls, targets, spaceName, spaceContainer, extraInfo, control, space):
        if not spaceName:
            spaceName = 'freeform'

        trueTarget = group(em=True, name=pdil.simpleName(control, '{0}_freeform'), p=spaceContainer)
        pdil.dagObj.matchTo(trueTarget, control)  # It's actually important so this can follow correctly. (line copied from MULTI_ORIENT)

        # Put proxies in a group that follows the "local" space.  Honestly this math doesn't make
        # sense but it gives the results JH wants, which are sensible.
        proxyGrp = group(em=True, name=pdil.simpleName(control, '{0}_freeformProxies'), p=spaceContainer)
        pdil.dagObj.matchTo(proxyGrp, control)
        parentConstraint(cls.getProxy(control), proxyGrp, mo=True)

        rProxies = []
        tProxies = []
        for t, (mode, w) in zip(targets, extraInfo):
            d = duplicate(trueTarget)[0]
            d.rename(pdil.simpleName(t) + '_freeform')
            d.setParent(proxyGrp)

            if mode == cls.ORIENT:
                orientConstraint(t, d, mo=True)
                rProxies.append((d, w))
            elif mode == cls.POINT:
                pointConstraint(t, d, mo=True)
                tProxies.append((d, w))
            elif mode == cls.PARENT:
                parentConstraint(t, d, mo=True)
                rProxies.append((d, w))
                tProxies.append((d, w))
            elif mode == cls.POINT_ORIENT:
                orientConstraint(t, d, mo=True)
                pointConstraint(t, d, mo=True)
                rProxies.append((d, w))
                tProxies.append((d, w))
            elif mode == cls.PARENT_TRANS:
                parentConstraint(t, d, mo=True, sr=['x', 'y', 'z'])
                tProxies.append((d, w))

        if rProxies:
            rConstraint = parentConstraint( [p[0] for p in rProxies], trueTarget, mo=True, st=['x', 'y', 'z'] )
            rConstraint.addAttr('rotTarget', at='bool', dv=True)
            rConstraint.interpType.set(2)

            attrs = rConstraint.getWeightAliasList()
            for v, attr in zip([p[1] for p in rProxies], attrs):
                attr.set(v)
        else:
            # If there were no rotate targets, use the parent joint or group
            proxy = cls.getProxy(control)
            if proxy:
                const = parentConstraint( proxy, trueTarget, mo=True, st=['x', 'y', 'z'] )
                const.addAttr('mo_ignore', at='bool', dv=True)

        if tProxies:
            tConstraint = parentConstraint( [p[0] for p in tProxies], trueTarget, mo=True, sr=['x', 'y', 'z'] )

            attrs = tConstraint.getWeightAliasList()
            for v, attr in zip([p[1] for p in tProxies], attrs):
                attr.set(v)
        else:
            # If there were no translate targets, use the parent joint or group
            proxy = cls.getProxy(control)
            if proxy:
                const = parentConstraint( proxy, trueTarget, mo=True, sr=['x', 'y', 'z'] )
                const.addAttr('mo_ignore', at='bool', dv=True)

        return trueTarget, spaceName

    @classmethod
    def getConstType(cls, obj):
        if orientConstraint(obj, q=True):
            return cls.ORIENT
        elif pointConstraint(obj, q=True):
            return cls.POINT
        elif parentConstraint(obj, q=True):
            return cls.PARENT

    @classmethod
    def getTargets(cls, target):
        constraints = listRelatives(target, type='parentConstraint')
        if constraints[0].hasAttr('mo_ignore'):
            constraints.remove(constraints[0])
        elif constraints[1].hasAttr('mo_ignore'):
            constraints.remove(constraints[1])

        if len(constraints) == 2:
            rConst, tConst = (constraints[0], constraints[1]) if constraints[0].hasAttr('rotTarget') else (constraints[1], constraints[0])
        else:
            if constraints[0].hasAttr('rotTarget'):
                rConst = constraints[0]
                tConst = None
            else:
                rConst = None
                tConst = constraints[0]

        # Gather the rotation proxies.
        rTargets = []
        rExtra = []
        if rConst:
            temp = parentConstraint(rConst, q=True, tl=True)
            for t in temp:
                type = cls.getConstType(t)
                actualTarget = cls.constMap[type](t, q=True, tl=True )[0]
                rTargets.append( [actualTarget, type] )

            rExtra = [a.get() for a in rConst.getWeightAliasList()]

        # Gather the translate proxies.
        tTargets = []
        tExtra = []
        if tConst:
            temp = parentConstraint(tConst, q=True, tl=True)
            for t in temp:
                type = cls.getConstType(t)
                actualTarget = cls.constMap[type](t, q=True, tl=True )[0]
                tTargets.append( [actualTarget, type] )

            tExtra = [a.get() for a in tConst.getWeightAliasList()]

        targets = []
        weights = []
        modes = []

        for (rT, mode), weight in zip(rTargets, rExtra):
            # Point/Orient const will be in both lists so alter the mdoe
            if rT in [t for t, w in tTargets] and mode == cls.ORIENT:
                targets.append(rT)
                modes.append(cls.POINT_ORIENT)
                weights.append(weight)

                print( rT, cls.debugMode[cls.POINT_ORIENT] )
            # Otherwise it's a regular orient or regular parent
            else:
                targets.append(rT)
                modes.append(mode)
                weights.append(weight)
                print( rT, cls.debugMode[mode] )

        for (tT, mode), weight in zip(tTargets, tExtra):
            # Point+Orient and parent will already have been added
            if tT in [r for r, w in rTargets]:
                continue
            # Since it's not rotation but is Parent, it must be PARENT_TRANS
            elif mode == cls.PARENT:
                targets.append(tT)
                modes.append(cls.PARENT_TRANS)
                weights.append(weight)
                print( tT, cls.debugMode[cls.PARENT_TRANS] )
            # Otherwise it's a regular trans
            else:
                targets.append(tT)
                modes.append(mode)
                weights.append(weight)
                print( tT, cls.debugMode[mode] )

        return tuple(targets), list(zip(modes, weights)), (rConst, tConst)
