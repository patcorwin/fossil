'''
This wraps up interfacing rig components onto the card structures.
'''
from __future__ import print_function, absolute_import

import collections
import copy
from functools import partial
import inspect
import re
import shlex
import sys
import traceback

from collections import OrderedDict

from pymel.core import textField, optionMenu, warning, checkBox, intField, floatField, duplicate, move, xform, listRelatives, select, joint, spaceLocator, dt, delete, confirmDialog, selected
#from pymel.core import *

from ...add import shortName, simpleName
from ... import core
from ... import lib

from . import controller
from . import log
from . import rig
from . import settings
from . import space
from . import util


class ParamInfo(object):
    '''
    Used by `commandInput` determine what options to make for the user.
    
    ..  todo::
        I think that I'm storing the extra nodes as:
            kwargs=NODE_0;
            
        or whatever number, thought it currently defaults to 0.
        
        * Add a bool?  Or just hack the UI to use a checkbox if min=0,max=1
    '''

    NODE_0 = 0
    NODE_1 = 1
    NODE_2 = 2
    NODE_3 = 3
    NODE_4 = 4

    NODES = [NODE_0, NODE_1, NODE_2, NODE_3, NODE_4]
    
    INT = -1
    FLOAT = -2
    STR = -3
    BOOL = -4
    ENUM = -5

    numericTypes = (INT, FLOAT, BOOL)

    def __init__(self, name, desc, type, default=None, min=None, max=None, enum=None):
        self.name = name
        self.desc = desc

        #self.types = [types] # REMOVE ALL THIS SHIT
        self.type = type
            
        if default is not None:
            self.default = default
        elif type == self.INT:
            self.default = 0
        elif type == self.FLOAT:
            self.default = 0.0
        elif type == self.STR:
            self.default = ''
        elif type == self.BOOL:
            self.default = False
        elif type == self.ENUM:
            self.default = ''
        else:
            # &&& I think this is because curves need a default?
            self.default = None
        
        self.min = min
        self.max = max
        self.value = default
        self.enum = enum
        self.kwargName = '' # Will get filled in when registered via `MetaControl`.
        
    def validate( self, value ):
        # Given a value, assign it to self.value if it meets the min/max reqs.
        if self.min is not None and value < self.min:
            warning( '{0} was lower than the min of {1}, ignoring'.format( value, self.min ) )
            return False
        if self.max is not None and value > self.max:
            warning( '{0} was higher than the max of {1}, ignoring'.format( value, self.max ) )
            return False
        self.value = value
        return True
        
    def __repr__(self):
        return 'ParamInfo( {0}={1} )'.format(self.name, self.value)
    
    def update(self, inputStr):
        settings = self.toDict( inputStr )
        settings[self.name] = self.value
        return self.toStr( settings )

    def getUIFieldKwargs(self, card):
        kwargs = {}
        
        if self.type in [self.INT, self.FLOAT]:
            if self.default is not None:
                kwargs['value'] = self.default
            if self.min is not None:
                kwargs['min'] = self.min
            if self.max is not None:
                kwargs['max'] = self.max
                
        elif self.type == self.BOOL:
            if self.default:
                kwargs['value'] = self.default
                
        elif self.type == self.STR:
            if self.default:
                kwargs['text'] = str(self.default)
        
        elif self.type == self.ENUM:
            # Use the specified default, else default to the first item in the list.
            if self.default:
                kwargs['text'] = self.default
            else:
                kwargs['text'] = self.enum.values()[0]
                
        cardSettings = self.toDict(card.rigParams)
        # Figure out if this option (possibly with multiple choices) is non-default.
        if self.kwargName in cardSettings:
            type = self.determineDataType(cardSettings[self.kwargName])
            
            if type in self.numericTypes:
                kwargs['value'] = cardSettings[self.kwargName]
            elif type == self.NODE_0:
                if card.extraNode[0]:
                    kwargs['text'] = card.extraNode[0].name()
            else:
                kwargs['text'] = cardSettings[self.kwargName]
                
        return kwargs
    
    # &&& I think toDict and toStr are for the options specific to rigging component.
    @classmethod
    def toDict(cls, s):
        '''
        Given a string of options, returns it as a dict.  Reverse of `toStr`
        '''
        
        def toProperDataType(_val):
            '''
            Turns the value from a string to the proper data type.
            ..  todo::
                Probably needs to handle the NODE_* stuff
                
                Can't the ParamInfo just be used to determine data type?
            '''
            _val = _val.strip()
            if _val.startswith( "'" ) and _val.endswith( "'" ):
                return _val[1:-1]
            
            #if _val.isdigit():
            if re.match( '-?\d+$', _val ):
                return int(_val)
            
            if re.match( '-?(\d{0,}\.\d+$)|(\d+\.\d{0,}$)', _val ):
                return float(_val)
            
            if _val == 'False':
                return False
            if _val == 'True':
                return True
            
            return _val
        
        info = {}
        for nameVal in s.split(';'):
            if nameVal.count('='):
                name, val = [_s.strip() for _s in nameVal.split('=')]
                if name and val:
                    # MUST str() because **unpacking kwargs doesn't like unicode!
                    info[str(name)] = toProperDataType(val)
            
        return info
    
    @classmethod
    def toStr(cls, d):
        '''
        Given a dict of options, returns it as a string, Reverse of `toDict`
        '''
        def quoteIfNeeded(data):
            if isinstance( data, basestring ) and not data.startswith('NODE_'):
                return "'" + data + "'"
            return data
        
        temp = [ '{0}={1}'.format(name, quoteIfNeeded(val)) for name, val in d.items() ]
        return ';'.join(temp)
    
    @classmethod
    def determineDataType(cls, value):
        if isinstance( value, int ):
            type = cls.INT
        elif isinstance( value, float ):
            type = cls.FLOAT
        elif value.startswith( 'NODE_0'):
            type = cls.NODE_0
        else:
            type = cls.STR
        return type

    def buildUI(self, card):
        
        uiFieldKwargs = self.getUIFieldKwargs(card)
        
        if self.type == self.BOOL:
            field = checkBox(l='', **uiFieldKwargs )  # noqa e741
            checkBox( field, e=True, cc=core.alt.Callback(self.setParam, field) )
            
        elif self.type == self.INT:
            field = intField(**uiFieldKwargs)
            intField( field, e=True, cc=core.alt.Callback(self.setParam, field) )
            
        elif self.type == self.FLOAT:
            field = floatField(**uiFieldKwargs)
            floatField( field, e=True, cc=core.alt.Callback(self.setParam, field) )
        
        elif self.type == self.ENUM:
            field = optionMenu(l='')  # noqa e741
            optionMenu(field, e=True, cc=core.alt.Callback(self.setParam, field))
            
            for i, choice in enumerate(self.enum, 1):
                menuItem(l=choice)  # noqa e741
                if self.enum[choice] == uiFieldKwargs['text']:
                    optionMenu(field, e=True, sl=i)
        
        elif self.type == self.STR:
            # &&& Possibly super gross, if the field is "name", use the first joint...
            if 'text' not in uiFieldKwargs and self.kwargName == 'name':
                uiFieldKwargs['text'] = shortName(card.joints[0])
                #default = card.n
                #getDefaultIkName(card) # &&& MAKE THIS so I can use the same logic when building the card.
            
            field = textField( **uiFieldKwargs )
            textField( field, e=True, cc=core.alt.Callback(self.setParam, field) )
            setattr(field, 'getValue', field.getText)  # Hack to allow ducktyping.

        elif self.type == self.NODE_0:
            
            def setExtraNode(extraNode):
                card.extraNode[0] = extraNode

                temp = ParamInfo.toDict( card.rigParams )
                temp[self.kwargName] = 'NODE_0'
                card.rigParams = ParamInfo.toStr(temp)

                return True
                
            def clearExtraNode(extraNode):
                card.extraNode[0] = None
                temp = ParamInfo.toDict( card.rigParams )
                del temp[self.kwargName]
                card.rigParams = ParamInfo.toStr(temp)

                return True
            
            util.GetNextSelected(
                setExtraNode,
                clearExtraNode,
                l='',  # noqa e741
                tx=shortName(card.extraNode[0]) if card.extraNode[0] else '',
                cw=[(1, 1), (2, 100), (3, 20)])
    
    def setParam(self, field):
        card = [ o for o in selected() if o.__class__.__name__ == 'Card' ][0]  # Change this to use
        #card = ui.common.selectedCards()[0]  # As a callback, guaranteed to exist
        v = field.getValue()

        # Convert enums to proper name
        if self.type == self.ENUM:
            v = self.enum[v]

        if self.validate(v):
            temp = self.toDict( card.rigParams )
            temp[self.kwargName] = v
            card.rigParams = self.toStr(temp)
    

def colorParity(side, controlSpec={}):
    '''
    Give a dict (used for control spec), subsitute certain colors depending
    on the side.  Also does alignment.
    
    ..  todo::
        The parity dict needs to be exposed to artists elsewhere
        Align only flips right side, is this fair?
        Verify all axis should be flipped
    '''
    
    parity = {  ('R',       'L'):
                ('green',   'red') }
    
    # Determine if any color substitution needs to happen.
    for sidePairs, colorPairs in parity.items():
        if side in sidePairs:
            index = sidePairs.index( side )
            otherIndex = int(abs( index - 1 ))
            oldColor = colorPairs[index]
            newColor = colorPairs[otherIndex]
            break
    else:
        return controlSpec

    modifiedSpec = {}
    
    for name, spec in controlSpec.items():
        options = {}
        for optionName, value in spec.items():
            if optionName == 'color':
                parts = value.split()
                if parts[0] == oldColor:
                    parts[0] = newColor
                    value = ' '.join(parts)
                
            if optionName == 'align':
                if side == 'R':
                    if value.startswith('n'):
                        value = value[1:]
                    else:
                        value = 'n' + value
            
            options[optionName] = value
            
        modifiedSpec[name] = options
        
    return {'controlSpec': modifiedSpec}


def _argParse(s):
    '''
    Given a string of controllers options, ex "--main -shape box --pv -size 3",
    parse it into a dict, ex:
        {
            'main': {'shape': box, '},
            'pv': {'size': 3}
        }
    
    ..  todo::
        If a failures happens, give the available options.
    '''
    info = {}
    for arg in s.split('-'):
        parts = shlex.split( arg )
        if not parts:
            continue
        name, data = parts[0], parts[1:]
        
        if name == 'shape':
            if hasattr( controller.control, data[0]):
                info['shape'] = getattr(controller.control, data[0])
            else:
                warning( "INVALID SHAPE: {0}  ".format(data[0]) )
                
        elif name == 'color':
            info['color'] = ' '.join(data)
        elif name == 'size':
            info['size'] = float(data[0])
        elif name == 'visGroup':
            info['visGroup'] = data[0]
        elif name == 'align':
            info['align'] = data[0]
        elif name == 'rotOrder':
            info['rotOrder'] = data[0]
        else:
            warning( "UNRECOGNIZED PARAMETER: {0}".format(name) )
            
    return info

    
OutputControls = collections.namedtuple( 'OutputControls', 'fk ik' )

if 'registeredControls' not in globals():
    registeredControls = {}


class RegisterdMetaControl(type):
    def __init__(cls, name, bases, clsdict):
        global registeredControls
        if len(cls.mro()) > 2:
            # Register the class in the list of available classes
            registeredControls[name] = cls
            
            # Backfill the key (kwargName) onto the param infos
            if cls.ikInput:
                for kwargName, paramInfo in cls.ikInput.items():
                    if isinstance(paramInfo, ParamInfo):
                        cls.ikInput[kwargName].kwargName = kwargName
                    else:
                        for i, _pi in enumerate(paramInfo):
                            cls.ikInput[kwargName][i].kwargName = kwargName
                            
            if cls.fkInput:
                for kwargName, paramInfo in cls.fkInput.items():
                    if isinstance(paramInfo, ParamInfo):
                        cls.fkInput[kwargName].kwargName = kwargName
                    else:
                        for i, _pi in enumerate(paramInfo):
                            cls.fkInput[kwargName][i].kwargName = kwargName
            
        super(RegisterdMetaControl, cls).__init__(name, bases, clsdict)


class classproperty(object):

    def __init__(self, fget):
        self.fget = fget

    def __get__(self, owner_self, owner_cls):
        return self.fget(owner_cls)


class MetaControl(object):
    '''
    Nearly every control is going to have an IK and FK component.  This allows
    packaging them both up so their args can be inspected and UI derived from it.
    
    The args are of two types:
        Controls Args: size, shape, color etc for the actual controls the
            animators will use

        Component Args: Generally specific to the control being made, as well
            as any shared between ik and fk, like a name
            
    ..  todo::
        * Have optional min/max requirements for if a card can build
            
    Method of overriding for custom stuff
    1) If you have a fancy IK system that will have an FK component, override
        _buildIk()
    2) If you have a special system with NO fk component, override _buildSide
        &&& But can you just set cls.fk = None and override _buildIk()?
            
    '''
    __metaclass__ = RegisterdMetaControl

    displayInUI = True

    shared = {}
    
    # Only relevant to Ik.  Some things only need the a single joint.  Fk can handle a single joint fine.
    hasEndJointInput = True
    
    # ik and fk must take the start and end joint, ikArgs/fkArgs will then be
    # added along with the control spec.
    ik_ = ''
    fk_ = 'motiga.tool.fossil.rig.fkChain'
    
    ikInput = {}
    fkInput = {}
    
    # If this particular control needs the controls to look/sort differently than default
    # ex, Arm wraps IkChain but defaults vigGroup to armIk and armFk
    ikControllerOptions = {}
    fkControllerOptions = {}
    
    # This is for args that are invariant, like if this collection requires fk to translate
    ikArgs = {}
    fkArgs = {}
    
    @classproperty
    def ik(cls):
        if not cls.ik_:
            return None
        
        module, func = cls.ik_.rsplit('.', 1)
        return getattr(sys.modules[module], func)
            
    @classproperty
    def fk(cls):
        if not cls.fk_:
            return None
        
        module, func = cls.fk_.rsplit('.', 1)
        return getattr(sys.modules[module], func)
    
    def _readKwargs(cls, card, isMirroredSide, sideAlteration=lambda **kwargs: kwargs, kinematicType='ik'):
        ikControlSpec = cls.controlOverrides(card, kinematicType)

        kwargs = collections.defaultdict(dict)
        kwargs.update( getattr(cls, kinematicType + 'Args' ))
        kwargs['controlSpec'].update( getattr(cls, kinematicType + 'ControllerOptions' ) )
        kwargs.update( sideAlteration(**ikControlSpec) )
        
        # Load up the defaults from .ikInput
        for argName, paramInfo in getattr(cls, kinematicType + 'Input').items():
            if isinstance( paramInfo, list ):
                paramInfo = paramInfo[0]
            if paramInfo.default is not None:
                kwargs[argName] = paramInfo.default
        
        userOverrides = ParamInfo.toDict( card.rigParams )
        # Not sure if decoding nodes is best done here or passed through in ParamInfo.toDict
        for key, val in userOverrides.items():
            if val == 'NODE_0':
                userOverrides[key] = card.extraNode[0]
        
        kwargs.update( userOverrides )

        return kwargs
    
    readKwargs = classmethod( _readKwargs )
    readIkKwargs = classmethod( partial(_readKwargs, kinematicType='ik') )
    readFkKwargs = classmethod( partial(_readKwargs, kinematicType='fk') )

    @classmethod
    def validate(cls, card):
        msg = 'Unable to build card {0} because it does not have any connection to the output joints'.format(card)
        assert card.start().real and card.end().real, msg

    @staticmethod
    def sideAlterationFunc(side):
        '''
        Given a side, ether 'L' or 'R', returns a function that makes changes
        to a dict to change colors if appropriate.
        '''
        
        if side == 'L':
            sideAlteration = partial( colorParity, 'L' )
        elif side == 'R':
            sideAlteration = partial( colorParity, 'R' )
        else:
            sideAlteration = lambda **kwargs: kwargs  # noqa e731
            
        return sideAlteration

    @classmethod
    def _buildSide(cls, card, start, end, isMirroredSide, side=None, buildFk=True):
        chain = rig.getChain(start, end)
        log.Rotation.check(chain, True)
        
        ikCtrl = fkCtrl = None
        sideAlteration = cls.sideAlterationFunc(side)
        
        if cls.fk and buildFk:
            fkControlSpec = cls.controlOverrides(card, 'fk')
            fkGroupName = card.getGroupName( **fkControlSpec )
            
            kwargs = collections.defaultdict(dict)
            kwargs.update( cls.fkArgs )
            kwargs['controlSpec'].update( cls.fkControllerOptions )
            kwargs.update( sideAlteration(**fkControlSpec) )
            
            fkCtrl, fkConstraints = cls.fk( start, end, groupName=fkGroupName, **kwargs )
            
            # If ik is coming, disable fk so ik can lay cleanly on top.  Technically it shouldn't matter but sometimes it does.
            if cls.ik:
                for const in fkConstraints:
                    const.set(0)
            
        if cls.ik:
            name, ikCtrl, ikConstraints = cls._buildIk(card, start, end, side, sideAlteration, isMirroredSide)
        
        switchPlug = None
        if cls.ik and cls.fk and buildFk:
            switchPlug = controller.ikFkSwitch( name, ikCtrl, ikConstraints, fkCtrl, fkConstraints )
        
        log.PostRigRotation.check(chain, card, switchPlug)
        
        return OutputControls(fkCtrl, ikCtrl)

    @classmethod
    def _buildIk(cls, card, start, end, side, sideAlteration, isMirroredSide):
        ikControlSpec = cls.controlOverrides(card, 'ik')
        ikGroupName = card.getGroupName( **ikControlSpec )
        
        kwargs = cls.readIkKwargs(card, isMirroredSide, sideAlteration)

        name = rig.trimName(end)

        if 'name' in kwargs and kwargs['name']:
            if side == 'L':
                kwargs['name'] += '_L'
            elif side == 'R':
                kwargs['name'] += '_R'
            name = kwargs['name']

        if name.count(' '):  # Hack for splineIk to have different controller names
            name = name.split()[-1]
        
        if cls.hasEndJointInput:
            ikCtrl, ikConstraints = cls.ik( start, end, groupName=ikGroupName, **kwargs )
        else:
            ikCtrl, ikConstraints = cls.ik( start, groupName=ikGroupName, **kwargs )

        return name, ikCtrl, ikConstraints

    @classmethod
    def build(cls, card, buildFk=True):
        '''
        Builds the control(s) and links them to the card
        '''
        cls.validate(card)
        
        log.TooStraight.targetCard(card)
        
        if not util.canMirror( card.start() ) or card.isAsymmetric():
            suffix = card.findSuffix()
            if suffix:
                ctrls = cls._buildSide(card, card.start().real, card.end().real, False, suffix, buildFk=buildFk)
            else:
                ctrls = cls._buildSide(card, card.start().real, card.end().real, False, buildFk=buildFk)

            if ctrls.ik:
                card.outputCenter.ik = ctrls.ik
            if ctrls.fk:
                card.outputCenter.fk = ctrls.fk
        else:
            # Build one side...
            suffix = card.findSuffix()
            side = settings.letterToWord[suffix]
            ctrls = cls._buildSide(card, card.start().real, card.end().real, False, suffix, buildFk=buildFk)
            if ctrls.ik:
                card.getSide(side).ik = ctrls.ik
            if ctrls.fk:
                card.getSide(side).fk = ctrls.fk
            
            # ... then flip the side info and build the other
            suffix = settings.otherLetter(suffix)
            side = settings.otherWord(side)
            ctrls = cls._buildSide(card, card.start().realMirror, card.end().realMirror, True, suffix, buildFk=buildFk)
            if ctrls.ik:
                card.getSide(side).ik = ctrls.ik
            if ctrls.fk:
                card.getSide(side).fk = ctrls.fk
        
    @classmethod
    def postCreate(cls, card):
        pass
        
    @classmethod
    def controlOverrides(cls, card, kinematicType):
        '''
        Given a card, returns a dict of the override flags for making the controllers.
        
        Must call from the proper inherited class, ex Arm or IkChain NOT MetaControl.
        
        :param str kinematicType: The name of an attr on the class, either 'ik' of 'fk'
        '''
        override = collections.defaultdict( dict )
        
        func = getattr( cls, kinematicType)
        if not func:
            return {}

        rigOptions = getattr(card, kinematicType + 'ControllerOptions' )
        
        # Get the defaults defined by the rig component
        for specName, spec in func.__defaultSpec__.items():
            override[specName] = spec.copy()
        
        # Apply any overrides from the MetaControl
        for specName, spec in getattr(cls, kinematicType + 'ControllerOptions' ).items():
            override[specName].update( spec )
        
        # Apply any overrides from the user
        if rigOptions:
            try:
                temp = rigOptions.split('--')

                if temp:
                    for data in temp:
                        if data:
                            name = re.match( '\w+', data )
                            if not name:
                                name = 'main'
                            else:
                                name = name.group(0)
                                data = data[ len(name): ].strip()
                            
                            if name in override:
                                # &&& I have no idea why passing unicode to shlex fails
                                override[name].update( _argParse( str(data) ) )
                            else:
                                # I think this happens when a control's rig changes
                                # to something with less options
                                override[name] = _argParse( str(data) )
            except Exception:
                warning( 'Error parsing card overrides on {0}'.format(card) )
                print( traceback.format_exc() )

        return {'controlSpec': override}
        
    @classmethod
    def processUniqueArgs(cls, card, funcId):
        #return _argParse( card.getRigComponentOptions(funcId) )
        return {}
        
    @classmethod
    def processSharedArgs(cls, card):
        #return _argParse( card.getRigComponentOptions('shared') )
        return {}

    @classmethod
    def saveState(cls, card):
        pass
        
    @classmethod
    def restoreState(cls, card):
        pass
    

class RotateChain(MetaControl):
    ''' Rotate only controls.  Unless this is a single joint, lead joint is always translatable too. '''
    fkArgs = {'translatable': False}


class TranslateChain(MetaControl):
    ''' Translatable and rotatable controls. '''
    fkArgs = {'translatable': True}


class IkChain(MetaControl):
    ''' Basic 3 joint ik chain. '''
    ik_ = 'motiga.tool.fossil.rig.ikChain'
    ikInput = OrderedDict( [
        ('name', ParamInfo( 'Name', 'Name', ParamInfo.STR, '')),
        ('pvLen', ParamInfo('PV Length', 'How far the pole vector should be from the chain', ParamInfo.FLOAT, default=0) ),
        ('stretchDefault', ParamInfo('Stretch Default', 'Default value for stretch (set when you `zero`)', ParamInfo.FLOAT, default=1, min=0, max=1)),
        ('endOrientType', ParamInfo('Control Orient', 'How to orient the last control', ParamInfo.ENUM, enum=rig.EndOrient.asChoices())),
    ] )
    
    ikArgs = {}
    fkArgs = {'translatable': True}


class IkChain2(MetaControl):
    ''' Basic 3 joint ik chain. '''
    ik_ = 'motiga.tool.fossil.rig.ikChain2'
    ikInput = OrderedDict( [
        ('name', ParamInfo( 'Name', 'Name', ParamInfo.STR, '')),
        #('twists', ParamInfo( 'Twist Dict', 'Temp solution to make twists', ParamInfo.STR, '{0:1, 1:1}')),
        ('pvLen', ParamInfo('PV Length', 'How far the pole vector should be from the chain', ParamInfo.FLOAT, default=0) ),
        ('stretchDefault', ParamInfo('Stretch Default', 'Default value for stretch (set when you `zero`)', ParamInfo.FLOAT, default=1, min=0, max=1)),
        ('endOrientType', ParamInfo('Control Orient', 'How to orient the last control', ParamInfo.ENUM, enum=rig.EndOrient.asChoices())),
    ] )
    
    ikArgs = {}
    fkArgs = {'translatable': True}
    
    @classmethod
    def readIkKwargs(cls, card, isMirroredSide, sideAlteration):
        kwargs = MetaControl.readIkKwargs(card, isMirroredSide, sideAlteration)
        '''
        try:
            kwargs['twists'] = json.loads( kwargs['twists'] )
        except Exception:
            kwargs['twists'] = {}
        
        print( 'Parsed into ' + str(type(kwargs['twists'])) + ' ' + str(kwargs['twists']) )
        '''
        
        # Determine the twist joints
        twists = {}

        primaryIndex = -1
        dividerCount = 0
        for j in card.joints:
            if j.info.get('twist'):
                dividerCount += 1
            else:
                if dividerCount:
                    twists[primaryIndex] = dividerCount
                  
                primaryIndex += 1
                dividerCount = 0
        
        kwargs['twists'] = twists
                
        return kwargs


class SplineChest(MetaControl):
    ''' Spline control for the chest mass.  Currently assumes 5 joints. '''
    ik_ = 'motiga.tool.fossil.rig.splineChest'
    ikInput = OrderedDict( [('name', ParamInfo( 'Name', 'Name', ParamInfo.STR, 'Chest')),
                            ('useTrueZero', ParamInfo( 'Use True Zero', 'Use True Zero', ParamInfo.BOOL, True)),
                            ('numChestJoints', ParamInfo( '# Chest Joints', 'How many joints are part of the chest mass', ParamInfo.INT, 3)),
                            ] )
    
    fkArgs = {'translatable': True}


class SplineChestThreeJoint(MetaControl):
    ''' Spline control for the chest mass for just 3 joints. '''
    ik_ = 'motiga.tool.fossil.rig.splineChestThreeJoint'
    ikInput = OrderedDict( [('name', ParamInfo( 'Name', 'Name', ParamInfo.STR, 'Chest'))] )
    
    fkArgs = {'translatable': True}


class SplineChest4Joint(MetaControl):
    ''' Spline control for the chest mass for just 4 joints. '''
    ik_ = 'motiga.tool.fossil.rig.splineChestFourJoint'
    ikInput = OrderedDict( [('name', ParamInfo( 'Name', 'Name', ParamInfo.STR, 'Chest'))] )
    
    fkArgs = {'translatable': True}


class SplineTwist(MetaControl):
    ''' Spline IK that provides control to twist individual sections. '''
    ik_ = 'motiga.tool.fossil.rig.splineIk'
    ikInput = OrderedDict( [
        ('controlCountOrCrv', [
            ParamInfo( 'CV count', 'How many cvs to use in auto generated curve', ParamInfo.INT, default=4, min=4 ),
            ParamInfo( 'Curve', 'A nurbs curve to use for spline', ParamInfo.NODE_0 ),
            ] ),
        ('simplifyCurve',
            ParamInfo( 'Simplify Curve', 'If True, the curve cvs will space out evenly, possibly altering the postions', ParamInfo.BOOL, default=False) ),
        ('twistInfDist',
            ParamInfo( 'Twist influence', 'How many joints on one side are influenced by the twisting, zero means it is done automatically.', ParamInfo.INT, default=0, min=0) ),
        ('tipBend',
            ParamInfo( 'Tip Bend', 'The tip control should influence the ease out bend', ParamInfo.BOOL, default=True) ),
        ('sourceBend',
            ParamInfo( 'Source Bend', 'The source control should influence the ease in bend', ParamInfo.BOOL, default=True) ),
        ('matchOrient',
            ParamInfo( 'Match Orient', "First and last controller are set to TrueZero'd", ParamInfo.BOOL, default=True) ),
        ('useLeadOrient',
            ParamInfo( 'Lead Orient', 'The controls have the same orientation as the first joint', ParamInfo.BOOL, default=False) ),
        ('allowOffset',
            ParamInfo( 'Allow Offset', 'If you Simplyify Curve, the joints will slightly shift unless you Allow Offset or the joints are straight', ParamInfo.BOOL, default=False) ),
        ('twistStyle',
            ParamInfo( 'Twist', '0 = advanced, 1=x, 2=-x 3=y ...', ParamInfo.INT, default=rig.TwistStyle.ADVANCED) ),
        
        ('name',
            ParamInfo( 'Name', 'Name', ParamInfo.STR, '')),
    ] )
    
    fkArgs = {'translatable': True}
    
    @classmethod
    def readIkKwargs(cls, card, isMirroredSide, sideAlteration=lambda **kwargs: kwargs, kinematicType='ik'):
        '''
        Overriden to handle if a custom curve was given, which then needs to be duplicated, mirrored and
        fed directly into the splineTwist.
        '''

        kwargs = cls.readKwargs(card, isMirroredSide, sideAlteration, kinematicType='ik')
        if isMirroredSide:
            if 'controlCountOrCrv' in kwargs and not isinstance( kwargs['controlCountOrCrv'], int ):
                crv = kwargs['controlCountOrCrv']
                crv = duplicate(crv)[0]
                kwargs['controlCountOrCrv'] = crv
                move( crv.sp, [0, 0, 0], a=True )
                move( crv.rp, [0, 0, 0], a=True )
                crv.sx.set(-1)
                
                kwargs['duplicateCurve'] = False
                
        return kwargs


class Head(MetaControl):
    ''' Probably useless, same as a Rotate Chain but tries to add spaces. '''
    fkArgs = {'translatable': False}
    fkControllerOptions = {'main': {'color': 'blue .5', 'size': 13 }}
    
    '''
    @classmethod
    def postCreate(cls, card):
        for mainCtrl in [card.outputCenter.fk, card.outputLeft.fk, card.outputRight.fk]:
            if mainCtrl:
                mode = space.Mode.ROTATE
                space.add( mainCtrl, card.start().parent.real, 'parent', mode=mode )
                space.add( mainCtrl, card.parentCard.start().parent.real, 'chest', mode=mode )
                space.addWorld( mainCtrl, mode=mode )
    '''
    
    @classmethod
    def postCreate(cls, card):
        for ctrl, side, type in card._outputs():
                
            if side == 'Right':
                neck = card.start().parent.realMirror
                chest = card.parentCard.start().parent.realMirror
            else:
                neck = card.start().parent.real
                chest = card.parentCard.start().parent.real
                
            space.addWorld( ctrl )
            space.add( ctrl, neck, spaceName='clavicle_pos_only' )
            space.add( ctrl, chest, spaceName='chest')
    
    
class Neck(MetaControl):
    ''' DOES NOT DO ANYTHING
    ..  todo:: Here to add space switching
    '''
    pass


class DogHindleg(MetaControl):
    ''' 4 joint dog hindleg. '''
    ik_ = 'motiga.tool.fossil.rig.dogleg'

    ikInput = OrderedDict( [
        ('name', ParamInfo( 'Name', 'Name', ParamInfo.STR, 'Leg')),
        ('pvLen', ParamInfo('PV Length', 'How far the pole vector should be from the chain', ParamInfo.FLOAT, default=0) ),
        ('endOrientType', ParamInfo('Control Orient', 'How to orient the last control', ParamInfo.ENUM, default=rig.EndOrient.TRUE_ZERO_FOOT, enum=rig.EndOrient.asChoices())),
    ] )


class Arm(MetaControl):
    ''' Same as IkChain but tries to add spaces for clavicle and chest. '''
    ik_ = 'motiga.tool.fossil.rig.ikChain'
    ikInput = OrderedDict( [
        ('name', ParamInfo( 'Name', 'Name', ParamInfo.STR, 'Arm')),
        ('pvLen', ParamInfo('PV Length', 'How far the pole vector should be from the chain', ParamInfo.FLOAT, default=0) ),
        ('stretchDefault', ParamInfo('Stretch Default', 'Default value for stretch (set when you `zero`)', ParamInfo.FLOAT, default=1,  min=0, max=1)),
        ('endOrientType', ParamInfo('Control Orient', 'How to orient the last control', ParamInfo.ENUM, default=rig.EndOrient.TRUE_ZERO, enum=rig.EndOrient.asChoices())),
    ] )
    
    fkArgs = {'translatable': True}
    fkControllerOptions = {'main': {'color': 'green .5', 'size': 13 }}

    @classmethod
    def postCreate(cls, card):
        '''
        ..  todo::
            * Despair had the hands to the head to, does that really make sense?
        '''
        
        for ctrl, side, type in card._outputs():
            if type == 'fk':
                continue
                
            socket = ctrl.subControl['socket']
            
            space.addWorld( ctrl )
            space.add( ctrl, socket, spaceName='clavicle_pos_only', mode=space.Mode.TRANSLATE)
            
            # Fixup names from default to be generic for easy default keying
            pv = ctrl.subControl['pv']
            names = space.getNames(pv)
            names[1] = 'arm'
            names[2] = 'arm_pos_only'
            space.setNames(pv, names)
            
            if card.parentCard and card.parentCard.start().parent:
                chest = card.parentCard.start().parent.real
                space.add( ctrl, chest, spaceName='chest')


class Leg(MetaControl):
    ''' Same as IkChain but adds world and parent spaces. '''
    ik_ = 'motiga.tool.fossil.rig.ikChain'
    ikInput = OrderedDict( [
        ('name', ParamInfo( 'Name', 'Name', ParamInfo.STR, 'Leg')),
        ('pvLen', ParamInfo('PV Length', 'How far the pole vector should be from the chain', ParamInfo.FLOAT, default=0) ),
        ('stretchDefault', ParamInfo('Stretch Default', 'Default value for stretch (set when you `zero`)', ParamInfo.FLOAT, default=1,  min=0, max=1)),
        ('endOrientType', ParamInfo('Control Orient', 'How to orient the last control', ParamInfo.ENUM, default=rig.EndOrient.TRUE_ZERO_FOOT, enum=rig.EndOrient.asChoices())),
    ] )
            
    fkArgs = {'translatable': True}
    
    @classmethod
    def postCreate(cls, card):
        '''
        ..  todo::
            * Despair had the hands to the head to, does that really make sense?
        '''
        
        for ctrl, side, type in card._outputs():
            if type == 'fk':
                continue
            
            space.addWorld( ctrl )
            space.add( ctrl, card.start().parent.real )
            
            # Fixup names from default to be generic for easy default keying
            pv = ctrl.subControl['pv']
            names = space.getNames(pv)
            names[1] = 'leg'
            names[2] = 'leg_pos_only'
            space.setNames(pv, names)


class SplineNeck(MetaControl):
    ''' Spline controller with a center control to provide arcing. '''
    ik_ = 'motiga.tool.fossil.rig.splineNeck'
    ikInput = OrderedDict( [
        ('name', ParamInfo( 'Name', 'Name', ParamInfo.STR, '')),
        ('matchEndOrient', ParamInfo( 'DEP-Match Orient', 'Ik Control will match the orientation of the joint last joint', ParamInfo.BOOL, default=False)),
        ('endOrient', ParamInfo('Control Orient', 'How to orient the last control', ParamInfo.ENUM, default=rig.EndOrient.TRUE_ZERO, enum=rig.EndOrient.asChoices())),
        ('curve', ParamInfo( 'Curve', 'A nurbs curve to use for spline', ParamInfo.NODE_0 ) ),
    ] )

    fkArgs = {'translatable': True}

    @classmethod
    def readIkKwargs(cls, card, isMirroredSide, sideAlteration=lambda **kwargs: kwargs, kinematicType='ik'):
        '''
        Overriden to handle if a custom curve was given, which then needs to be duplicated, mirrored and
        fed directly into the splineTwist.
        '''

        kwargs = cls.readKwargs(card, isMirroredSide, sideAlteration, kinematicType='ik')
        if isMirroredSide:
            if 'curve' in kwargs:
                crv = kwargs['curve']
                crv = duplicate(crv)[0]
                kwargs['curve'] = crv
                move( crv.sp, [0, 0, 0], a=True )
                move( crv.rp, [0, 0, 0], a=True )
                crv.sx.set(-1)
                
                kwargs['duplicateCurve'] = False
                
        return kwargs


class TwistHelper(MetaControl):
    ''' Special controller to automate distributed twisting, like on the forearm. '''
    #displayInUI = False

    fk_ = 'motiga.tool.fossil.rig.twist'

    fkInput = OrderedDict( [
        ('defaultPower', ParamInfo( 'Default Power', 'Default automatic twist power', ParamInfo.FLOAT, 0.5)),
    ] )

    @classmethod
    def build(cls, card, buildFk=True):
        '''
        ..  todo::
            Make this actually respect control overrides.
        '''

        #twist(twist, twistDriver, twistLateralAxis=[0,0,1], driverLateralAxis=[0,0,1], controlSpec={}):

        kwargs = cls.readFkKwargs(card, False)

        if not util.canMirror( card.start() ) or card.isAsymmetric():
            ctrl, container = cls.fk(card.joints[0].real, card.extraNode[0].real, **kwargs)
            card.outputCenter.fk = ctrl
        else:
            # Build one side...
            suffix = card.findSuffix()
            side = settings.letterToWord[suffix]
            ctrl, container = cls.fk(card.joints[0].real, card.extraNode[0].real, **kwargs)
            card.getSide(side).fk = ctrl
            
            # ... then flip the side info and build the other
            suffix = settings.otherLetter(suffix)
            side = settings.otherWord(side)
            ctrl, container = cls.fk(card.joints[0].realMirror, card.extraNode[0].realMirror, **kwargs)
            card.getSide(side).fk = ctrl


class SquashStretch(MetaControl):
    ''' Special controller providing translating bones simulating squash and stretch. '''
    displayInUI = False

    ik_ = 'motiga.tool.fossil.rig.squashAndStretch'
    ikInput = OrderedDict( [
        ('rangeMin', ParamInfo( 'Min Range', 'Lower bounds of the keyable attr.', ParamInfo.FLOAT, -5.0)),
        ('rangeMax', ParamInfo( 'Max Range', 'Upper bounds of the keyable attr.', ParamInfo.FLOAT, 5.0)),
        ('scaleMin', ParamInfo( 'Shrink Value', 'When the attr is at the lower bounds, scale it to this amount.', ParamInfo.FLOAT, .5)),
        ('scaleMax', ParamInfo( 'Expand Value', 'When the attr is at the upper bounds, scale it to this amount.', ParamInfo.FLOAT, 2)),
    ] )
    
    #orientAsParent=True, min=0.5, max=1.5
    
    @classmethod
    def build(cls, card):
        '''
        Custom build that uses all the joints, except the last, which is used
        as a virtual center/master control for all the scaling joints.
        '''
        assert len(card.joints) > 2
        pivotPoint = xform(card.joints[-1], q=True, ws=True, t=True)
        joints = [j.real for j in card.joints[:-1]]
    
        ikControlSpec = cls.controlOverrides(card, 'ik')
    
        def _buildSide( joints, pivotPoint, isMirroredSide, side=None ):
            log.Rotation.check(joints, True)
            if side == 'L':
                sideAlteration = partial( colorParity, 'L' )
            elif side == 'R':
                sideAlteration = partial( colorParity, 'R' )
            else:
                sideAlteration = lambda **kwargs: kwargs  # noqa
            
            kwargs = cls.readIkKwargs(card, isMirroredSide, sideAlteration)
            kwargs.update( cls.ikArgs )
            kwargs['controlSpec'].update( cls.ikControllerOptions )
            kwargs.update( sideAlteration(**ikControlSpec) )
            
            ikCtrl, ikConstraints = cls.ik( joints, pivotPoint, **kwargs )
            return OutputControls(None, ikCtrl)
    
        if not util.canMirror( card.start() ) or card.isAsymmetric():
            suffix = card.findSuffix()
            if suffix:
                ctrls = _buildSide(joints, pivotPoint, False, suffix)
            else:
                ctrls = _buildSide(joints, pivotPoint, False)

            card.outputCenter.ik = ctrls.ik
        else:
            ctrls = _buildSide(joints, pivotPoint, False, 'L')
            card.outputLeft.ik = ctrls.ik

            pivotPoint[0] *= -1
            joints = [j.realMirror for j in card.joints[:-1]]
            ctrls = _buildSide(joints, pivotPoint, True, 'R' )
            card.outputRight.ik = ctrls.ik
    
    @staticmethod
    def getSquashers(ctrl):
        '''
        Returns the objs the squasher controls follow, which have the set driven keys.
        Cheesy at the moment because it's just the list of children (alphabetized).
        '''
        squashers = listRelatives(ctrl, type='transform')
        return sorted( set(squashers) )
    
    @classmethod
    def saveState(cls, card):
        sdkInfo = {}
        for ctrl, side, kinematicType in card.getMainControls():
            if kinematicType == 'ik':
                sdkInfo[side] = [ lib.anim.findSetDrivenKeys(o) for o in cls.getSquashers(ctrl) ]
                
        state = card.rigState
        state['squasherSDK'] = sdkInfo
        card.rigState = state
        
    @classmethod
    def restoreState(cls, card):
        state = card.rigState
        if 'squasherSDK' not in state:
            return
        
        for ctrl, side, kinematicType in card.getMainControls():
            if kinematicType == 'ik':
                if side in state['squasherSDK']:
                    curves = state['squasherSDK'][side]
                    squashers = cls.getSquashers(ctrl)
                    for squasher, crv in zip(squashers, curves):
                        lib.anim.applySetDrivenKeys(squasher, crv)


class Weapon(TranslateChain):
    '''
    Use this in the BODY rig as the point that can be attached to.
    Just a translate chain that can only have a single joints.
    
    ..  todo::
        Make it so that it only can have a singe joint.
    '''
    pass
    

class Group(MetaControl):
    ''' A control that doesn't control a joint.  Commonly used as a space for other controls. '''
    fkInput = OrderedDict( [
        ('name', ParamInfo( 'Name', 'Name', ParamInfo.STR, '')),
        ('translatable', ParamInfo( 'Translatable', 'It can translate', ParamInfo.BOOL, default=True)),
        ('scalable', ParamInfo( 'Scalable', 'It can scale', ParamInfo.BOOL, default=False)),
        ('useTrueZero', ParamInfo( 'True Zero', 'Use true zero like ik controls', ParamInfo.BOOL, default=False)),
    ] )

    @classmethod
    def validate(cls, card):
        # &&& Eventually just validate that all it's joints are non-helpers
        pass
    
    @classmethod
    def _buildSide(cls, card, start, end, isMirroredSide, side=None, buildFk=True):
        '''
        Most inputs are ignored because it does it's own thing since the joints
        don't exist.
        
        
        ..  todo:: Will need special attention to deal with twin mode.
        '''
        # DO NOT check rotation on a thing that doesn't exist.
        # log.Rotation.check(rig.getChain(start, end), True)
        
        ikCtrl = None
        
        sideAlteration = cls.sideAlterationFunc(side)
        fkControlSpec = cls.controlOverrides(card, 'fk')
        
        # kwargs = collections.defaultdict(dict)
        # kwargs.update( cls.fkArgs )
        # kwargs['controlSpec'].update( cls.fkControllerOptions )
        # kwargs.update( sideAlteration(**fkControlSpec) )

        kwargs = cls.readFkKwargs(card, isMirroredSide, sideAlteration)

        if not kwargs['name']:
            kwargs['name'] = simpleName(card.start())

        if side == 'L':
            kwargs['name'] += '_L'
        elif side == 'R':
            kwargs['name'] += '_R'

        kwargs.update( sideAlteration(**fkControlSpec) )
        
        position = xform(card.start(), q=True, ws=True, t=True)
        
        # If there is 1 joint, orient as the card (for backwards compatibility)
        # but if there are more, figure out what it's orientation should be
        if len(card.joints) == 1:
            rotation = xform(card, q=True, ws=True, ro=True)
        else:
            lib.anim.orientJoint(card.joints[0], card.joints[1], xform(card.joints[0], q=True, ws=True, t=True) + card.upVector())
            rotation = xform(card.joints[0], q=True, ws=True, ro=True)
        
        if isMirroredSide:
            position[0] *= -1.0
            rotation[1] *= -1.0
            rotation[2] *= -1.0

        if not card.start().parent:
            parent = None
        else:
            if isMirroredSide and card.start().parent.realMirror:
                parent = card.start().parent.realMirror
            else:
                parent = card.start().parent.real
        
        fkCtrl, emptyConstraints = rig.ctrlGroup(parent, position, rotation, **kwargs)
        
        if isMirroredSide:
            space = core.dagObj.zero(fkCtrl, make=False)
            space.rx.set( space.rx.get() + 180 )
        
        return OutputControls(fkCtrl, ikCtrl)


class Freeform(MetaControl):
    ''' A control that doesn't control a joint.  Commonly used as a space for other controls. '''
    fkInput = OrderedDict( [
        ('translatable', ParamInfo( 'Translatable', 'It can translate', ParamInfo.BOOL, default=True)),
    ] )

    @classmethod
    def validate(cls, card):
        pass
    
    @classmethod
    def _buildSide(cls, card, start, end, isMirroredSide, side=None, buildFk=True):
        '''
        Since the joints aren't in a chain, just pass them all along to get sorted out later
        '''
        
        log.Rotation.check(rig.getChain(start, end), True)
        
        ikCtrl = None
        
        sideAlteration = cls.sideAlterationFunc(side)
        fkControlSpec = cls.controlOverrides(card, 'fk')
        
        kwargs = cls.readFkKwargs(card, isMirroredSide, sideAlteration)
        
        #if not kwargs['name']:
        #    kwargs['name'] = simpleName(card.start())
        
        # I think kwargs[name] is totally ignored anyway
        '''
        if side == 'L':
            print "kwargs['name']", kwargs['name']
            kwargs['name'] += '_L'
        elif side == 'R':
            kwargs['name'] += '_R'
        '''

        kwargs.update( sideAlteration(**fkControlSpec) )
                
        if isMirroredSide:
            joints = [j.realMirror for j in card.joints if not j.isHelper]
        else:
            joints = [j.real for j in card.joints if not j.isHelper]
        
        fkCtrl, emptyConstraints = rig.freeform(joints, **kwargs)
        
        return OutputControls(fkCtrl, ikCtrl)


class SplineProxy(MetaControl):
    '''
    Super fancy control that lets you control a daisy chained ik system with a
    spline, like a jaggy tail.
    '''
    
    # Use a modified version of SpineTwist
    ikInput = copy.deepcopy(SplineTwist.ikInput)
    ikInput['tipBend'].value = False
    ikInput['sourceBend'].value = False
    del ikInput['allowOffset']
    del ikInput['useLeadOrient']
    
    # Even though the chainIk is the real function, this is the one we want the
    # options for --though there must be a better way to recognize this as they
    # are already specified in ikInput--
    ik_ = 'motiga.tool.fossil.rig.splineIk'
    
    fkArgs = {'translatable': True}
    
    @classmethod
    def validate(cls, card):
        '''
        This validation is going to be complex
        
        * It needs to have a reference to another card,
        * It also needs to refer to several joints along the chain to make IKs
        * The OTHER card needs to refer to 2x as many, for the P
        '''
        
        assert card.extraNode[0].__class__.__name__ == 'Card'
    
    @classmethod
    def _buildIk(cls, card, start, end, side, sideAlteration, isMirroredSide):
        
        driveCard = card.extraNode[0]
        
        driveChain = driveCard.joints
        
        chain = []
        matchup = {}
        for i, srcJoint in enumerate(driveChain, 1):
            name = srcJoint.name() + "_d%i" % i
            select(cl=True)
            j = joint(  n=name,
                        p=xform(srcJoint, q=True, ws=True, t=True),
                        relative=False)
            chain.append(j)
            matchup[srcJoint] = j
        
        # Set up parents
        for p, jnt in zip( chain[:-1], chain[1:] ):
            jnt.setParent(p)
        
        # This has similiarities with Card.orientJoints but I'm not sure
        # they can share a base.  Most stuff isn't relevaant
        axis = card.upVector()
        upLoc = spaceLocator()
        
        def moveUpLoc(obj, axis=axis):  # Move the upLoc above the given obj
            xform( upLoc, ws=True, t=axis + dt.Vector(xform(obj, q=True, ws=True, t=True)))
    
        upAxis = 'y'
        aim = card.getAimAxis(driveChain[0].suffixOverride)
        
        for i, (jnt, tempJnt, orientTarget) in enumerate(zip(chain, driveChain, chain[1:])):
            aim = card.getAimAxis(tempJnt.suffixOverride)
                        
            moveUpLoc(jnt, card.upVector() )
                        
            lib.anim.orientJoint(jnt, orientTarget, upLoc, aim=aim, up=upAxis)
                        
        joint( chain[-1], e=True, oj='none' )
           
        delete(upLoc)
        
        # &&& This is no good, extra node info can totally stomp on eachother.
        nodes = list(card.extraNode)
        
        handleInfo = []
        for i, node in enumerate(nodes[1:]):
            
            handleInfo.append([
                node,
                matchup[driveCard.extraNode[i * 2]],
                matchup[driveCard.extraNode[ i * 2 + 1 ]]
                ])
        
        # v---
        # &&& This ripped right out of the original _buildIk
        ikControlSpec = cls.controlOverrides(card, 'ik')
        
        kwargs = cls.readIkKwargs(card, isMirroredSide, sideAlteration)

        name = rig.trimName(end)

        if 'name' in kwargs and kwargs['name']:
            if side == 'L':
                kwargs['name'] += '_L'
            elif side == 'R':
                kwargs['name'] += '_R'
            name = kwargs['name']
        # ^---
        
        ctrl, constraints = rig.chainedIk(start, end, chain, handleInfo, splineOptions=kwargs)
        return name, ctrl, constraints


class GlueOrigin(MetaControl):
    '''
        Both this and Glue match up cards by card.rigData['id'].  If gluing to a
        mirrored component, then specify provide a suffix,
        ex: card.rigData['glue'] = 'L'
        (or 'R') to specify the side to glue to.

        On an attachment, there must be exactly one card (the top) tagged as
        GlueOrigin, the rest just are set to Glue.

        ..  todo:: Is it easy/safe for the top card to know it's the top so I can just have Glue as the type?

        OLD:
        attachment.tagForWorldZeroOnExport( GLUE CTRL )  ?? SHOULD BE BY DEFAULT?
    '''
    ik = None

    @classmethod
    def _buildSide(cls, card, start, end, isMirroredSide, side=None, buildFk=True):
        '''
        PaCo *thinks* this should only ever be on a single side, that's the whole point.
        '''

        # Side name not really important but might as well be consistent.
        #if side == 'L':
        #    kwargs['name'] += '_L'
        #elif side == 'R':
        #    kwargs['name'] += '_R'

        fkCtrl, constraints = rig.fkChain(start, start, translatable=True)

        return OutputControls(fkCtrl, None)


class Glue(MetaControl):
    ik = None
    fk = None


class TransZeroed(TranslateChain):
    # Identical to Translate chain but control will zero when attached.
    pass


class WorldOriented(MetaControl):
    '''
    Makes a control forcing the joint to be world oriented so dazed FX don't tilt.
    '''
    fkArgs = {'translatable': False}

    @classmethod
    def postCreate(cls, card):
        for ctrl, side, type in card._outputs():
            space.addTrueWorld(ctrl)
            core.dagObj.lockRot(ctrl)
            ctrl.visibility.set(0)
            #ctrl.visibility.lock()


class Follower(Group):
    '''
    For use in attachment rigs.  This lets you define proxies in the attachment
    rig to use as spaces.  They attach to the joint specified in the follow field.
    '''
    
    fkInput = OrderedDict( [
        ('name', ParamInfo( 'Name', 'Name', ParamInfo.STR, '')),
        ('follow', ParamInfo( 'Follow', 'The joint to follow', ParamInfo.STR, '')),
        ] )

    @classmethod
    def validate(cls, card):
        # &&& Eventually just validate that all it's joints are non-helpers
        pass


# Collect all the controls that can be made and make a nice sorted list of them.
availableControlTypes = {}
    
for _name, _class in locals().items():
    if inspect.isclass( _class ):
        if issubclass( _class, MetaControl ) and _class != MetaControl:
            availableControlTypes[_name] = _class


class Foot(MetaControl):
    
    ik_ = 'motiga.tool.fossil.rig.foot'
    
    @classmethod
    def build(cls, card):
        '''
        '''
        
        #assert len(card.joints) > 2
        
        toe = card.joints[1]
        heel = card.joints[2]
        
        previousJoint = card.joints[0].parent
        assert previousJoint.card.rigCommand in ('Leg', 'IkChain')
        
        legCard = previousJoint.card
        
        if not util.canMirror( card.start() ) or card.isAsymmetric():
            legControl = legCard.outputCenter.ik
            suffix = card.findSuffix()
            if suffix:
                ctrls = cls._buildSide(card, card.joints[0].real, xform(toe, q=True, ws=True, t=True), xform(heel, q=True, ws=True, t=True), legControl, False, suffix)
            else:
                ctrls = cls._buildSide(card, card.joints[0].real, xform(toe, q=True, ws=True, t=True), xform(heel, q=True, ws=True, t=True), legControl, False)

            card.outputCenter.ik = ctrls.ik
            
        else:
            
            toePos = xform(toe, q=True, t=True, ws=True)
            heelPos = xform(heel, q=True, t=True, ws=True)
            
            leftLegControl = legCard.outputLeft.ik
            ctrls = cls._buildSide(card, card.joints[0].real, toePos, heelPos, leftLegControl, True, 'L')
            card.outputLeft.ik = ctrls.ik


            rightLegControl = legCard.outputRight.ik
            toePos[0] *= -1
            heelPos[0] *= -1
            ctrls = cls._buildSide(card, card.joints[0].realMirror, toePos, heelPos, rightLegControl, False, 'R')
            card.outputRight.ik = ctrls.ik
        
        
        
        #pivotPoint = xform(card.joints[-1], q=True, ws=True, t=True)
        #joints = [j.real for j in card.joints[:-1]]
    
        #ikControlSpec = cls.controlOverrides(card, 'ik')
        
    
    @classmethod
    def _buildSide( cls, card, ballJoint, toePos, heelPos, legControl, isMirroredSide, side=None, buildFk=False ):
        
        log.Rotation.check([ballJoint], True)
        if side == 'L':
            sideAlteration = partial( colorParity, 'L' )
        elif side == 'R':
            sideAlteration = partial( colorParity, 'R' )
        else:
            sideAlteration = lambda **kwargs: kwargs  # noqa
            
        if buildFk:
            fkControlSpec = cls.controlOverrides(card, 'fk')
            fkGroupName = card.getGroupName( **fkControlSpec )
            
            kwargs = collections.defaultdict(dict)
            kwargs.update( cls.fkArgs )
            kwargs['controlSpec'].update( cls.fkControllerOptions )
            kwargs.update( sideAlteration(**fkControlSpec) )
            
            fkCtrl, fkConstraints = cls.fk( ballJoint, ballJoint, groupName=fkGroupName, **kwargs )
            
            # Ik is coming, disable fk so ik can lay cleanly on top.  Technically it shouldn't matter but sometimes it does.
            for const in fkConstraints:
                const.set(0)
        
        ikControlSpec = cls.controlOverrides(card, 'ik')
        
        kwargs = cls.readIkKwargs(card, isMirroredSide, sideAlteration)
        kwargs.update( cls.ikArgs )
        kwargs['controlSpec'].update( cls.ikControllerOptions )
        kwargs.update( sideAlteration(**ikControlSpec) )
        
        #fkCtrl, fkConstraints = rig.fkChain(ballJoint, ballJoint, translatable=True)
        ikCtrl, ikConstraints = cls.ik( ballJoint, toePos, heelPos, legControl, **kwargs )
        
        #switchPlug = controller.ikFkSwitch( ballJoint.name(), ikCtrl, ikConstraints, fkCtrl, fkConstraints )
        
        return OutputControls([], ikCtrl)



def availableControlTypeNames():
    global registeredControls
    return [name for name, cls in sorted(registeredControls.items()) if cls.displayInUI]
    
    
def updateIkChainCommands():
    '''
    ikChain uses a single `endOrientType` (string) enum instead of conflicting
    matchEndOrient and matchRotation.
    '''
    for card in core.findNode.allCards():
        if card.rigCommand in ('IkChain', 'Arm', 'Leg'):
            
            temp = ParamInfo.toDict( card.rigParams )
            
            # Convert old values to new value
            if 'endOrientType' not in temp:
                
                rotation = temp['matchRotation'] if 'matchRotation' in temp and temp['matchRotation'] else None
                trueWorld = temp['matchEndOrient'] if 'matchEndOrient' in temp and temp['matchEndOrient'] else None
                
                if trueWorld or (rotation is None and trueWorld is None):
                    temp['endOrientType'] = rig.EndOrient.TRUE_ZERO
                elif not trueWorld and rotation:
                    temp['endOrientType'] = rig.EndOrient.JOINT
                elif not trueWorld and not rotation:
                    temp['endOrientType'] = rig.EndOrient.WORLD
                else:
                    temp['endOrientType'] = rig.EndOrient.TRUE_ZERO
                
                print( 'card.rigParams', card.rigParams )
                print( 'UPDATING', card, 'to', temp['endOrientType'] )
            
            # Remove old values
            if 'matchRotation' in temp:
                del temp['matchRotation']
            
            if 'matchEndOrient' in temp:
                del temp['matchEndOrient']
                
            card.rigParams = ParamInfo.toStr(temp)


def buildRig(cards):
    '''
    Build the rig for the given cards, defaulting to all of them.
    '''
    global raiseErrors  # Testing hack.
    global availableControlTypes
    errors = []
    
    #if not cards:
    #    cards =
    
    print( 'Building Cards:\n    ', '    \n'.join( str(c) for c in cards ) )
    
    # Ensure that main and root motion exist
    main = lib.getNodes.mainGroup()
    lib.getNodes.rootMotion(main=main)
    
    # Build all the rig components
    for card in cards:
        if card.rigData.get('rigCmd'):
            try:
                availableControlTypes[ card.rigData.get('rigCmd') ].build(card)
            except Exception:
                print( traceback.format_exc() )
                errors.append( (card, traceback.format_exc()) )
                
    # Afterwards, create any required space switching that comes default with that card
    for card in cards:
        if card.rigData.get('rigCmd'):
            func = availableControlTypes[ card.rigData.get('rigCmd') ]
            if func:
                func.postCreate(card)
                
    if errors:
    
        for card, err in errors:
            print( lib.util.writeInBox( str(card) + '\n' + err ) )
    
        print( lib.util.writeInBox( "The following cards had errors:\n" +
                '\n'.join([str(card) for card, err in errors]) ) ) # noqa e127
                
        confirmDialog( m='Errors occured!  See script editor for details.' )
        
        if raiseErrors:
            raise Exception( 'Errors occured on {0}'.format( errors ) )