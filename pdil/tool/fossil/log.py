'''
Utilities for logging things that happen during the skeleton/rig creation so
the users can be warned appropriately.
'''

from pymel.core import cmds, dt, listRelatives

import pdil

from . import node


def findRotatedBones(joints=None):
    '''
    Checks joints (defaulting to the )
    '''

    if not joints:
        obj = node.getTrueRoot()
        joints = listRelatives(obj, ad=True, type='joint')

    rotated = []

    for j in joints:
        if not pdil.math.isClose( j.r.get(), [0, 0, 0] ):
            rotated.append( (j, j.r.get()) )

    #print '{0} rotated of {1} tested'.format(len(rotated), len(joints) )
    
    return rotated


# -----------------------------------------------------------------------------
# SimpleLog is useful for other deeply nested things reporting errors.  This might
# be the better way to do things in general.
_msgs = []


def clear():
    global _msgs
    _msgs = []


def msg(m):
    global _msgs
    _msgs.append(m)


def get():
    global _msgs
    return '\n'.join(_msgs)


class SimpleLog(object):
    def __init__(self, logFunc):
        self.logFunc = logFunc
        self.additionalMessages = []
    
    def append(self, msg):
        if msg:
            self.additionalMessages.append(msg)
    
    def __enter__(self):
        clear()
        return self
        
    def __exit__(self, type, value, traceback):
        msg = get()
        if msg:
            self.additionalMessages.append(msg)
        
        self.logFunc('\n'.join(self.additionalMessages))

# -----------------------------------------------------------------------------


class Reporter(object):
    '''
    Convenience context manager for logs to automatically clear the log at the
    start and pass the results to the given logging function.
    '''
    
    def __init__(self, logFunc):
        self.logFunc = logFunc
        
    def __enter__(self):
        self.clear()
        
    def __exit__(self, type, value, traceback):
        self.logFunc( self.results() )


class MultiReporter(object):
    '''
    Convenience context manager for mutliple `Reporter`s being called in the
    same block.
    '''
    
    def __init__(self, logFunc, *reporters):
        self.logFunc = logFunc
        self.reporters = reporters
    
    def __enter__(self):
        for reporter in self.reporters:
            reporter.clear()

    def __exit__(self, type, value, traceback):
        results = []
        for reporter in self.reporters:
            res = reporter.results()
            if res:
                results.append( res )
        
        self.logFunc( '\n'.join(results) )


class Centerline(Reporter):
    '''
    When a joint is built, check if it is close to the center, which is probably
    an accident and it should be on center.
    
    ..  todo::
        This can probably be adapted to the width of all the cards so the
        guardians have a large number and the rogue has a small one.
        
    '''
    offcenter = []
    tolerance = 4
    zero = 0.0000001
    
    @classmethod
    def clear(cls):
        cls.offcenter = []

    @classmethod
    def check(cls, jnt):
        if cls.zero < abs(cmds.xform(str(jnt), q=True, ws=True, t=True)[0]) < cls.tolerance:
            cls.offcenter.append(jnt)
            
    @classmethod
    def results(cls):
        
        if not cls.offcenter:
            return ''

        return ('These joints are really close to the center, are they supposed to be offcenter?\n    '
                '\n    '.join( [str(j) for j in cls.offcenter] ) )


ZERO_VECTOR = dt.Vector(0, 0, 0)


class Rotation(Reporter):
    '''
    Controls should only be made on joints that are not rotated, so make sure
    the are all not rotated.
    '''
    
    rotatedJoints = []
    
    @classmethod
    def clear(cls):
        cls.rotatedJoints = []
    
    @classmethod
    def check(cls, joints, force=False):
        rotated = findRotatedBones(joints)
        if rotated:
            for jnt, r in rotated:
                cls.rotatedJoints.append(jnt.name())
        
        # Because the slightest of rotations ruin joint orient, force true zero
        if force:
            for jnt in joints:
                if jnt.r.get() != ZERO_VECTOR:
                    jnt.r.set(0, 0, 0)
                
    @classmethod
    def results(cls):
        if not cls.rotatedJoints:
            return ''
        
        return ('The following joints had rotations that were cleared:\n    '
                '\n    '.join(cls.rotatedJoints))
        
        
class PostRigRotation(Reporter):
    '''
    Verifies that making the rig didn't alter any joints.
    '''
    
    issues = set()
    
    @classmethod
    def clear(cls):
        cls.issues.clear()
    
    @classmethod
    def check(cls, joints, card, switchPlug):
        
        if switchPlug:
            prevVal = switchPlug.get()
            
            switchPlug.set(0)
            rotated = findRotatedBones(joints)
            if rotated:
                cls.issues.add(card)
            else:
                switchPlug.set(1)
                rotated = findRotatedBones(joints)
                if rotated:
                    cls.issues.add(card)
            
            if prevVal != switchPlug.get():
                switchPlug.set(prevVal)
        else:
            rotated = findRotatedBones(joints)
            if rotated:
                cls.issues.add(card)
        
    @classmethod
    def results(cls):
        if not cls.issues:
            return ''
        
        return 'These cards alter the joints when rigged:\n    '  + \
               '\n    '.join( [str(c) for c in cls.issues] )
               
               
class TooStraight(Reporter):
    '''
    This operates a bit differently since the location of the check can't know
    what card made it, that operation has to happen externally.
    '''
    
    cards = set()
    
    target = None
    
    @classmethod
    def clear(cls):
        cls.cards.clear()
        
    @classmethod
    def check(cls, angleBetween):
        '''
        Under 2 degrees is a guess, possibly less could work.  Above 2 seems to work fine.
        '''
        if angleBetween < 0.035:  # If we are under 2 degrees, FAIL!
            cls.cards.add( cls.target )
    
    @classmethod
    def targetCard(cls, card):
        cls.target = card

    @classmethod
    def results(cls):
        if not cls.cards:
            return ''
        
        return 'These cards need a small bend put in them for IK to work:\n    ' + \
               '\n    '.join( [str(c) for c in cls.cards] )