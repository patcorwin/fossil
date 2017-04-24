'''
Utilities to manage and use space switching.

..  todo:
    TEST rotate only space!  Might use same group as position only.
    Function to rename enums
'''
from __future__ import print_function, absolute_import

import collections
import operator

from pymel.core import *

from ...add import simpleName, shortName, cardPath
from ... import core
from ... import lib


from . import util
from . import log as skelLog
from . import settings

globalSettings = core.ui.Settings(
    "space switching",
    {
        "autoEuler": False,
        "singleSwitchEuler": False,
    })

SpaceTarget = collections.namedtuple( 'SpaceTarget', 'name target type extra' )
        
ENUM_ATTR = 'space'


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
    EXTERNAL = -1           # Here for taking advantage of the get group code.
    ROTATE_TRANSLATE = 0    # Acts just like a child of the target
    TRANSLATE = 1           # If the target translates, it follows but not if the target rotates
    ROTATE = 2              # Only follows rotation, not translation.  Probably only ever for rotate only controls
    ALT_ROTATE = 3          # Acts as a child of the target positionally but is rotationally follows the second target

    POINT_ORIENT = 4        # Does a point and orient, which is only relevant if doing non-enum attr
    DUAL_PARENT = 5         # ParentConstraint to two objs
    DUAL_FOLLOW = 6         # A point and orient to two objs (aka position is alway linearly interpreted between points regardless of target rotation)
    MULTI_PARENT = 7        # The base of a "rivet"
    MULTI_ORIENT = 8        # Only has an orient constraint

    FREEFORM = 10           # Allows several targets in different configurations, I do what I want!

    values = {}
    _classmap = {}

    @classmethod
    def buildReverseLookup(cls):
        for k, v in cls.__dict__.items():
            if isinstance(v, int) and k.isupper():
                cls.values[v] = k
                if k in globals():
                    cls._classmap[v] = globals()[k]

    @classmethod
    def build(cls, mode, *args, **kwargs):
        return cls._classmap[mode].build(*args, **kwargs)

    @classmethod
    def getTargets(cls, mode, *args, **kwargs):
        return cls._classmap[mode].getTargets(*args, **kwargs)


class ROTATE_TRANSLATE(object):

    @staticmethod
    def build(target, spaceName, spaceContainer, rotateTarget, control, space):
        return target, spaceName

    @staticmethod
    def getTargets(target):
        extra = None
        constraint = None
        return target, extra, constraint


class TRANSLATE(object):

    @staticmethod
    def build(target, spaceName, spaceContainer, rotateTarget, control, space):
        if not spaceName:
            spaceName = simpleName(target) + '_pos'
    
        for child in spaceContainer.listRelatives():
            if target in pointConstraint(child, q=True, tl=True):
                trueTarget = child
                break
        else:
            trueTarget = group(em=True, name=simpleName(target, '{0}_posOnly'), p=spaceContainer)
            pointConstraint( target, trueTarget )

        return trueTarget, spaceName

    @staticmethod
    def getTargets(target):
        target = pointConstraint(target, q=True, tl=True)[0]
        extra = None
        constraint = None
        return target, extra, constraint
    

class ROTATE(object):

    @staticmethod
    def build(target, spaceName, spaceContainer, rotateTarget, control, space):
        if not spaceName:
            spaceName = simpleName(target) + '_rot'

        trueTarget = group(em=True, name=simpleName(target, '{0}_rotOnly'), p=spaceContainer)
        
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
    

class ALT_ROTATE(object):

    @staticmethod
    def build(target, spaceName, spaceContainer, rotateTarget, control, space):
        if not spaceName:
            spaceName = simpleName(target) + '_altRot'
            
        trueTarget = group(em=True, name=simpleName(target, '{0}_split'), p=spaceContainer)
        
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
        

class DUAL_PARENT(object):

    @staticmethod
    def build(target, spaceName, spaceContainer, rotateTarget, control, space):
        if not spaceName:
            spaceName = simpleName(target) + '_' + simpleName(rotateTarget) + '_parent'
        
        trueTarget = group(em=True, name=simpleName(target, '{0}_dualParent'), p=spaceContainer)
        core.dagObj.matchTo(trueTarget, control)
        
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


class DUAL_FOLLOW(object):

    @staticmethod
    def build(target, spaceName, spaceContainer, rotateTarget, control, space):
        if not spaceName:
            spaceName = simpleName(target) + '_' + simpleName(rotateTarget) + '_follow'
        trueTarget = group(em=True, name=simpleName(target, '{0}_dualFollow'), p=spaceContainer)
        core.dagObj.matchTo(trueTarget, control)
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


class MULTI_PARENT(object):

    @staticmethod
    def build(target, spaceName, spaceContainer, rotateTarget, control, space):
        #  In this mode, target is a list of targets and rotateTarget is an optional list of weights
        if not spaceName:
            #spaceName = simpleName(target) + '_' + simpleName(rotateTarget) + '_follow'
            spaceName = 'multi_parent'
            
        trueTarget = group(em=True, name=simpleName(target[0], '{0}_multiParent'), p=spaceContainer)
        
        core.dagObj.matchTo(trueTarget, control)  # It's actually important so this can follow correctly.

        proxies = []
        for t in target:
            d = duplicate(trueTarget)[0]
            d.rename( d.name() + '_' + simpleName(t) )
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


class MULTI_ORIENT(object):
    @staticmethod
    def build(target, spaceName, spaceContainer, rotateTarget, control, space):
        #  In this mode, target is a list of targets and rotateTarget is an optional list of weights
        if not spaceName:
            spaceName = 'multi_orient'

        trueTarget = group(em=True, name=simpleName(control, '{0}_multiOrient'), p=spaceContainer)
        
        core.dagObj.matchTo(trueTarget, control)  # It's actually important so this can follow correctly.

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


class FREEFORM(object):
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

        main = core.findNode.mainController(control)

        if main:
            if main.getMotionType().endswith('.ik'):

                if main.getSide() == 'Center' or (settings.toWord(main.card.rigData.get('suffix')) == main.getSide()):
                    parentProxy = main.card.start().real.getParent()

                else:
                    parentProxy = main.card.start().realMirror.getParent()

            else:
                if main.card.rigCommand == 'Group':
                    parentProxy = parentConstraint(main.container, q=True, tl=True)[0]
                else:
                    parentProxy = core.constraints.getOrientConstrainee(control).getParent()

        return parentProxy

    @classmethod
    def build(cls, targets, spaceName, spaceContainer, extraInfo, control, space):
        if not spaceName:
            spaceName = 'freeform'

        trueTarget = group(em=True, name=simpleName(control, '{0}_freeform'), p=spaceContainer)
        core.dagObj.matchTo(trueTarget, control)  # It's actually important so this can follow correctly. (line copied from MULTI_ORIENT)

        # Put proxies in a group that follows the "local" space.  Honestly this math doesn't make
        # sense but it gives the results JH wants, which are sensible.
        proxyGrp = group(em=True, name=simpleName(control, '{0}_freeformProxies'), p=spaceContainer)
        core.dagObj.matchTo(proxyGrp, control)
        parentConstraint(cls.getProxy(control), proxyGrp, mo=True)

        rProxies = []
        tProxies = []
        for t, (mode, w) in zip(targets, extraInfo):
            d = duplicate(trueTarget)[0]
            d.rename(simpleName(t) + '_freeform')
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


# MUST be called after all space types are defined
Mode.buildReverseLookup()


def toCamel(s):
    return s.title().replace('_', '')


modeMap = {}


for var, val in Mode.__dict__.items():
    if var.isupper() and isinstance(val, int):
        modeMap[val] = toCamel(var)


#------------------------------------------------------------------------------
# Because the main group needs root motion, which needs spaces, and spaces
# have helpers to target the main group, they have to live together here.
def getMainGroup(create=True):
    '''
    Wraps lib.anim.getMainGroup() so code that simply needs to obtain the group
    can do so while this function actually builds all the needed parts.
    '''

    existing = lib.getNodes.mainGroup(create=False)
    if existing:
        return existing
    
    if create:
        main = lib.getNodes.mainGroup()
        addRootMotion(main)
        return main


def addRootMotion(main=None):
    rootMotion = lib.getNodes.rootMotion(create=False, main=main)
    
    if not rootMotion:
        rootMotion = core.getNodes.getRootMotion(create=True, main=main)
        core.sharedShape.use(rootMotion)
    
    rootMotion.visibility.setKeyable(False)
    add( rootMotion, getMainGroup(), 'main_transOnly', mode=Mode.ALT_ROTATE, rotateTarget=getTrueWorld())
    addTrueWorld( rootMotion )
    add( rootMotion, getMainGroup(), 'main' )
#------------------------------------------------------------------------------


def getGroup(mode, main=None, checkOnly=False):
    '''
    :param int mode: One of the target modes, ex: EXTERNAL, POINT_ORIENT, etc.
    :param PyNode main: The main controller in caset the scene has multiple.
    :param bool checkOnly: If True, won't build the space and returns None if not found
    '''
    global modeMap
    
    if not main:
        main = getMainGroup()
    
    for child in main.listRelatives():
        if simpleName(child) == '__spaces__':
            spaceContainer = child
            break
    else:
        spaceContainer = group(em=True, n='__spaces__', p=main)
        hide(spaceContainer)
        
    name = modeMap[mode]
    for child in spaceContainer.listRelatives():
        if simpleName(child) == name:
            spaceGroup = child
            break
    else:
        if checkOnly:
            return None
        else:
            spaceGroup = group(em=True, name=name, p=spaceContainer)
    
    return spaceGroup
        
        
def getExternalWorld(main=None, checkOnly=False):
    ext = getGroup(Mode.EXTERNAL, main, checkOnly)
    
    if checkOnly and not ext:
        return None
    
    for child in ext.listRelatives():
        if shortName(child) == 'world':
            return child
    
    g = group(em=True, name='world', p=ext)
    g.addAttr('externalTarget', dt='string')
    g.externalTarget.set(':world:')
    
    return g


def getExternalProxy(proxyName, main=None, checkOnly=False, trans=None, rot=None):
    ext = getGroup(Mode.EXTERNAL, main, checkOnly)
    
    if checkOnly and not ext:
        return None
    
    for child in ext.listRelatives():
        if child.hasAttr('externalTarget') and child.externalTarget.get() == proxyName:
            return child
    else:
        if checkOnly:
            return False
    
    g = group(em=True, name='sp_' + proxyName, p=ext)

    if trans:
        xform(g, ws=True, t=trans)
    if rot:
        xform(g, ws=True, ro=rot)

    g.addAttr('externalTarget', dt='string')
    g.externalTarget.set(proxyName)
    
    return g


def getTrueWorld():
    main = getMainGroup()
    for child in main.listRelatives():
        if shortName(child) == 'trueWorld':
            return child
    
    grp = group(em=True, name='trueWorld')
    for t in 'trs':
        for a in 'xyz':
            #grp.attr( t + a).lock()
            grp.attr( t + a).setKeyable(False)
    hide(grp)
    grp.setParent( main )
    grp.inheritsTransform.set(False)
    return grp


_targetInfoConstraints = []


def getTargetInfo(ctrl):
    '''
    Returns a list of targets allowing for reconstruction the spaces.
    
    Additionally, it fills the _targetInfoConstraints for advanced info/usage.
    '''
    
    global _targetInfoConstraints
    _targetInfoConstraints = {}
    
    if not ctrl.hasAttr(ENUM_ATTR):
        return []
        
    conditions = ctrl.attr(ENUM_ATTR).listConnections( type='condition' )
    
    if conditions:
        for c in conditions:
            constraint = c.outColorR.listConnections()
            if constraint:
                constraint = constraint[0]
                break
    else:
        return []
    
    tempTargets = parentConstraint(constraint, q=True, tl=True )
    plugs = parentConstraint(constraint, q=True, wal=True )
    
    # Map the enum values to targets since the order on the constraint might differ
    targets = {}  # key = index, val=(target, space type)
    for condition in conditions:
        plug = condition.outColorR.listConnections(p=True)
        
        constraint = None   # Other tools need access to the constraint of MULTI_*
        #                     and replicating 90% of the logic is dumb
        order = int(condition.secondTerm.get())
        spaceType = condition.spaceType.get()
        extra = None
        if plug:
            plug = plug[0]
            target = tempTargets[plugs.index(plug)]
            
            target, extra, constraint = Mode.getTargets(spaceType, target)

            if isinstance(target, PyNode) and target.hasAttr('externalTarget'):
                extra = 'external'

            targets[order] = (target, spaceType, extra)
        else:
            targets[order] = (None, spaceType, extra)
        
        _targetInfoConstraints[order] = constraint
        
    targetAndType = [ t for (i, t) in sorted( targets.items(), key=operator.itemgetter(0))]
    _targetInfoConstraints = [ t for (i, t) in sorted( _targetInfoConstraints.items(), key=operator.itemgetter(0))]
    
    return [ SpaceTarget(name, target, type, extra) for name, (target, type, extra) in zip( getNames(ctrl), targetAndType ) ]


def clean(ctrl):
    
    #missingTargets = []
    for i, spaceTarget in enumerate(getTargetInfo(ctrl)):
        if not spaceTarget.target:
            #missingTargets.append(spaceTarget)
            res = confirmDialog(m='There is nothing connected to %s' % spaceTarget.name, b=['Delete', 'Ignore'] )
            if res == 'Delete':
                conditions = ctrl.attr(ENUM_ATTR).listConnections( type='condition' )
                for condition in conditions:
                    if int(condition.secondTerm.get()) == i and not condition.outColorR.listConnections(p=True):
                        delete(condition)
                        break
    

def get(ctrl):
    return getNames(ctrl)[ctrl.attr(ENUM_ATTR).get()]


def getNames(ctrl):
    '''
    Returns a list of the spaces a control has.
    
    ..  todo::
        Possibly filter out any at the end that are marked for removal.
    '''
    if not ctrl.hasAttr(ENUM_ATTR):
        attrs = [ attr.attrName() for attr in ctrl.listAttr(ud=True, st=ENUM_ATTR + '_*') if re.search( '_t\d+$', attr.attrName())]
        return attrs
    
    return cmds.addAttr( ctrl.attr(ENUM_ATTR).name(), q=True, enumName=True ).split(':')


def setNames(ctrl, names):
    '''
    Updates the enum names and storage of the names.
    '''
    addAttr( ctrl.attr(ENUM_ATTR), e=True, enumName=':'.join(names) )


def remove(control, spaceName, shuffleRemove=False):
    '''
    Remove the space from the control.  If `shuffleRemove` is `True`, keep the
    same number of enum but make the last one marked for delete.  This means
    you can remove referenced things but it's a 3 step process:
        * shuffleRemove
        * move the anim curves to the appropriate connection in ref'ed files
        * Fully remove the end spaces marked for delete.
        
    ..  todo::
        Option to allow specifying the actual space target instead of just the name?
        
    '''

    # Adjust the condition for each one secondTerm to be one earlier
    # Mark or delete the final item
    
    names = getNames(control)
    
    index = names.index(spaceName)
    
    conditionToDelete = None
    plugToDelete = None
    # Find target and shift all the values above down to closes the gap.
    for condition in control.listConnections( type='condition' ):
        if condition.secondTerm.get() == index:
            conditionToDelete = condition
            plugToDelete = condition.outColorR.listConnections(p=True)[0] if condition.outColorR.listConnections() else None
            break
            
    for condition in control.listConnections( type='condition' ):
        if condition.secondTerm.get() > index:  # Shuffle all terms down
            condition.secondTerm.set( condition.secondTerm.get() - 1 )
        
    names.remove( spaceName )
        
    if shuffleRemove:
        names.append( 'DELETE' )
        
    # If the last space was removed, remove the switch attr entirely
    if not names:
        control.deleteAttr(ENUM_ATTR)
    else:
        setNames( control, names )
        
    spaceGrp = core.dagObj.zero(control, apply=False)
    const = PyNode(parentConstraint(spaceGrp, q=True))
    
    # Since the targetList order might not match the enum order, find the
    # correct target by matching up the destination weight plug.
    if plugToDelete:
        for target, plug in zip(const.getTargetList(), const.getWeightAliasList()):
            if plug == plugToDelete:
                parentConstraint( target, const, e=True, rm=True)
                
    if conditionToDelete:
        delete(conditionToDelete)


def removeAll(control):
    '''
    Removes all the spaces from the control.
    '''
    
    names = getNames(control)
    if not names:
        return
    
    spaceGrp = core.dagObj.zero(control, apply=False)
    
    delete( parentConstraint(spaceGrp, q=True) )
    
    '''
    for i, condition in enumerate(control.listConnections( type='condition' )):
        delete(condition)
        target = parentConstraint( spaceGrp, q=True, tl=True )[i]
        parentConstraint( target, spaceGrp, e=True, rm=True)
        '''
    
    if control.hasAttr(ENUM_ATTR):
        control.deleteAttr(ENUM_ATTR)
    else:
        for name in names:
            control.deleteAttr(name)


def _applyDefaults(kwargs, **defaults):
    '''
    Helper for convenience space adding attrs to process inputs and only apply
    values if the user didn't specify anything.  For example, addParent() adds
    a space called 'parent' by default but the user can specify something else.
    '''
    for k, v in defaults.items():
        if k not in kwargs:
            kwargs[k] = v


def addParent(control, **kwargs):
    '''
    Convenience function to add a space of the parent of the joint that the
    given control is controlling.
    '''
    
    bindBone = core.constraints.getOrientConstrainee(control)
    parent = bindBone.getParent()
    
    _applyDefaults( kwargs, mode=Mode.ROTATE_TRANSLATE, spaceName='parent' )
    
    add( control, parent, **kwargs )


def addWorld(control, *args, **kwargs):
    '''
    Convenience func for adding world space, has same args as `add()`
    '''
    add( control, getMainGroup(), 'world', *args, **kwargs )


def addExternalWorld(control, *args, **kwargs):
    '''
    Convenience func for adding world space, has same args as `add()`
    '''
    add( control, getExternalWorld(), external=True, *args, **kwargs )


def addExternalTarget(control, targetName, trans=None, rot=None, *args, **kwargs):
    add( control, getExternalProxy(targetName, trans=trans, rot=rot), external=True, *args, **kwargs )


def addTrueWorld(control, *args, **kwargs):
    '''
    Convenience func for adding world space, has same args as `add()`
    '''
    add( control, getTrueWorld(), 'trueWorld', *args, **kwargs )


def add(control, target, spaceName='', mode=Mode.ROTATE_TRANSLATE, enum=True, rotateTarget=None, external=None):
    '''
    Concerns::
        Does rotate only handle being applied repeatedly without issues?
    
    ..  todo:
        * Had to change Rotate only, does translate only need the same?
            * Are certain settings for certain controls nonsense?
                * PV can be position only
                * Weapons can be rotate only
        * Possibly make a custom switch node to replace all the conditions?
        * Add test to confirm that junk names are discarded
        * Validate the name will be unique
        * When adding a space, there probably should be a more robust way to
            check for the index to add, not just using the length of existing targets.
    '''

    # Early outs
    if not target:
        print( "No target specified")
        return

    for targetInfo in getTargetInfo(control):
        if targetInfo.type == mode and targetInfo.target == target:
            print( "Target already exists", mode, target)
            return
    # End early outs

    rotateLocked = False
    translateLocked = False
    # If the control can't translate, make sure the mode is rotate-only.
    if control.tx.isLocked() and control.ty.isLocked() and control.tz.isLocked():
        if mode is not Mode.MULTI_ORIENT:
            mode = Mode.ROTATE
        translateLocked = True

    if control.rx.isLocked() and control.ry.isLocked() and control.rz.isLocked():
        rotateLocked = True
    
    with core.dagObj.TemporaryUnlock(control, trans=not translateLocked, rot=not rotateLocked):
        space = core.dagObj.zero(control, apply=False)
        spaceContainer = getGroup(mode)

        # -----------------------
        # ACTUAL SPACE ADDED HERE
        # Call the appropriate sub function to build the particulars of the space
        trueTarget, spaceName = Mode.build(mode, target, spaceName, spaceContainer, rotateTarget, control, space)
        # -----------------------

        if not spaceName:
            spaceName = simpleName(target)

        existingTargets = parentConstraint( space, q=True, tl=True)

        constraint = parentConstraint( trueTarget, space, mo=True )
        constraintAttr = constraint.getWeightAliasList()[-1]
        
        if enum:
            existingNames = getNames(control) + [spaceName]
            if not control.hasAttr(ENUM_ATTR):
                control.addAttr( ENUM_ATTR, at='enum', enumName='FAKE', k=True )

            setNames(control, existingNames)

            switch = createNode('condition')
            switch.rename( 's_%i_to_%s' % (len(existingTargets), spaceName) )
            switch.secondTerm.set( len(existingTargets) )
            switch.colorIfTrue.set(1, 1, 1)
            switch.colorIfFalse.set(0, 0, 0)
            switch.addAttr( 'spaceType', at='long', dv=mode )
            
            control.attr( ENUM_ATTR ) >> switch.firstTerm
            switch.outColorR >> constraintAttr
            
        else:
            # Add float attr (but alias it to nice name?)
            #raise Exception('This is not implemented yet')
            name = '%s_%s_t%i' % (ENUM_ATTR, spaceName, mode)
            control.addAttr( name, at='float', min=0.0, max=1.0, k=True)
            
            control.attr(name) >> constraintAttr


def swap(ctrl, spaceAIndex, spaceBIndex):
    '''
    Swap the spaces on `ctrl` by index
    
    ..  todo::
        Possibly rename the condition to reflect the new number.
    '''
    
    if not ctrl.hasAttr(ENUM_ATTR):
        return
        
    names = getNames(ctrl)
    
    if len(names) <= max(spaceAIndex, spaceBIndex):
        return
        
    temp = names[spaceAIndex]
    names[spaceAIndex] = names[spaceBIndex]
    names[spaceBIndex] = temp
    
    setNames( ctrl, names )
        
    conditions = ctrl.attr(ENUM_ATTR).listConnections( type='condition' )
    
    for condition in conditions:
        if condition.secondTerm.get() == spaceAIndex:
            condition.secondTerm.set(spaceBIndex)
            
        elif condition.secondTerm.get() == spaceBIndex:
            condition.secondTerm.set(spaceAIndex)


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


def serializeSpaces(control):
    '''
    Given an object with spaces, return a list, ex:
        [ { 'name': 'Parent',
            'target': ['b_Spine01', 'PyNode("SpineCard").outputCenter.fk'],
            'type': 1},
            { 'name': 'DoubleConstraint',
            'targets': [
                ['b_Spine01', 'PyNode("SpineCard").outputCenter.fk'],
                ['b_Spine02', 'PyNode("SpineCard").outputCenter.fk.subControls["2"]'],
                ]
            'type': 7},
        ]

    Targets are encoded with both the full name and the cardPath if there is one.

    ..  todo:: The external system needs to be fully fleshed out.  Right now you
        can only specify a single external target.  But maybe that's all we'll
        ever need?
    '''
    
    '''
    OLD WAY
    Given an object with spaces, return a list, ex:
        [ ['Parent', 'b_Spine01', 1],
          [<name>, <target>, <type>],]
    '''
    
    ''' # This previous method was irritating because I had to parse multiple targets out.
    targets = []
    for spaceInfo in getTargetInfo(control):
        if not spaceInfo.target:
            raise Exception("{0}'s space {1} doesn't have a target".format(control, spaceInfo.name))
        print spaceInfo.target
        if isinstance(spaceInfo.target, tuple):
            targets.append( [spaceInfo.name, ' '.join([t.name() for t in spaceInfo.target]), spaceInfo.type] )
        else:
            targets.append( [spaceInfo.name, spaceInfo.target.name(),  spaceInfo.type] )
    return targets
    '''

    targets = []
    for spaceInfo in getTargetInfo(control):
        if not spaceInfo.target:
            raise Exception("{0}'s space {1} doesn't have a target".format(control, spaceInfo.name))
        
        if isinstance(spaceInfo.target, tuple):
            targets.append(
                {'name': spaceInfo.name,
                 'targets': [(t.name(), cardPath(t)) for t in spaceInfo.target],
                 'type': spaceInfo.type,
                 'extra': spaceInfo.extra}
            )
        else:
            targets.append(
                {'name': spaceInfo.name,
                 'target': (spaceInfo.target.name(), cardPath(spaceInfo.target)),
                 'type': spaceInfo.type}
            )
            if spaceInfo.extra:
                targets[-1]['extra'] = spaceInfo.extra

    return targets


def deserializeSpaces(control, data):
    '''
    Apply spaces obtained from `serializeSpaces()` to the given control.
    '''
    errors = []

    def parseTarget(target):
        if objExists(target[0]):
            return PyNode(target[0])
        elif target[1]:
            obj = util.fromCardPath(target[1])
            if obj:
                return obj
        return None

    for spaceInfo in data:
        if isinstance(spaceInfo, dict):
            name = spaceInfo['name']
            type = spaceInfo['type']

            if 'target' in spaceInfo:
                external = None
                if 'extra' in spaceInfo and spaceInfo['extra'] == 'external':
                    target = getExternalProxy(spaceInfo['target'][0])
                    external = True
                else:
                    target = parseTarget(spaceInfo['target'])

                if target:
                    add( control, target, name, mode=type, external=external )
                else:
                    errors.append( str(spaceInfo['target']) )

            elif type in [Mode.MULTI_PARENT, Mode.MULTI_ORIENT, Mode.FREEFORM]:
                targets = [parseTarget(t) for t in spaceInfo['targets']]
                add( control, targets, name, mode=type, rotateTarget=spaceInfo['extra'] )
            else:
                target1 = parseTarget(spaceInfo['targets'][0])
                target2 = parseTarget(spaceInfo['targets'][1])
                
                if target1 and target2:
                    add( control, target1, name, mode=type, rotateTarget=target2 )
                else:
                    errors.append( 'MultiTarget:' + ' '.joint(spaceInfo['targets'])  )
                
        else:
            # OLD GROSSER WAY
            name, target, type = spaceInfo
            if objExists(target):
                add( control, PyNode(target), name, mode=type )
            elif target == 'trueWorld':
                addTrueWorld( control, mode=type )
            elif len(target.split()) == 2 and type in [ALT_ROTATE, DUAL_PARENT, DUAL_FOLLOW]:
                try:
                    a, b = target.split()
                    
                    if objExists(a) and objExists(b):
                        add( control, PyNode(a), name, mode=type, rotateTarget=PyNode(b) )
                    else:
                        errors.append( target )
                        continue
                except Exception:
                    errors.append( target )
            else:
                errors.append( target )
    
    if errors:
        skelLog.msg(
            'Error with spaces on ' + str(control) + ' missing Targets:\n    ' +
            '\n    '.join(errors)
        )


def pruneUnused_UNFINISHED():
    # Need to loop through all the groups with targets
    trueTargets = []
    for target in trueTargets:
        if not target.r.listConnections(type='constraint') and target.t.listConnections(type='constraint'):
            delete(target)


def findTargetees(obj):
    for c in ctrls:
        for spaceInfo in getTargetInfo(c):
            if str(obj) in str(spaceInfo.target):
                print( c, spaceInfo)
                
                
def rivetSpace(ctrl, vert, name=''):
    skin = lib.weights.findRelatedSkinCluster(vert.node())
    
    if not skin:
        return
    
    vals = skinPercent(skin, vert, q=True, v=True )
    jnts = skinCluster(skin, q=True, inf=True)

    targets = []
    weights = []

    for v, j in zip(vals, jnts):
        if v:
            targets.append(j)
            weights.append(v)
    
    add( ctrl, targets, spaceName=name, mode=Mode.MULTI_PARENT, enum=True, rotateTarget=weights)
    

def fixUnhookedSpaces(ctrl):
    '''
    Preliminary tool to deal with messed up spaces.
    
    Right now ONLY deals if there is a space name and destination unhookedup.
    FILL IN OTHERS WITH ERROR IN NAME???
    '''
    
    names = getNames(ctrl)
    space = core.dagObj.zero(ctrl, apply=False)
    constraint = PyNode(parentConstraint(space, q=True))
    targetPlugs = constraint.getWeightAliasList()
    
    if len(names) != len(targetPlugs):
        print( 'There are', len(names), 'but', len(targetPlugs), ', you will need to figure out what is right!')
    
    noDriver = {}
    for i, plug in enumerate(targetPlugs):
        cons = plug.listConnections(s=True, d=False)
        if not cons:
            noDriver[i] = plug
            
    #
    connected = {}
    unconnected = []
    conditions = ctrl.attr(ENUM_ATTR).listConnections( type='condition' )
    
    for c in conditions:
        con = c.outColorR.listConnections()
        if con:
            order = c.secondTerm.get()
            connected[order] = con[0]
        else:
            unconnected.append(c)
    
    missingIndex = range(len(targetPlugs))
    for i in connected:
        missingIndex.remove(i)
    
    if len(noDriver) == 1 and len(unconnected) == 1:
        print( noDriver, unconnected )
        print( connected.keys() )
        print( missingIndex )
        
        print( 'Autofixing!', noDriver.values()[0], 'is "%s"' % names[missingIndex[0]] )
        unconnected[0].secondTerm.set(missingIndex[0])
        #print( noDriver.values()[0] )
        unconnected[0].outColorR >> noDriver.values()[0]
    
    if not noDriver and not unconnected:
        print( 'All good!' )
    else:
        print( 'This had some errors' )
        
    'FILL IN OTHERS WITH ERROR IN NAME???'