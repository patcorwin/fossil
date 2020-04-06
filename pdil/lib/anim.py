import collections
from itertools import chain
import json
import os

from pymel.core import cmds, keyframe, selected, currentTime, PyNode, setAttr, hasAttr, setKeyframe, copyKey, pasteKey, warning, delete, exportSelected, playbackOptions, createNode, listAttr, select, objExists, cutKey, setDrivenKeyframe, keyTangent, dt, mel

from ..add import findFromIds, getIds
from .. import core


TAGGING_ATTR = 'fossilAnimSource'

if '_loadAlterPlug' not in globals():
    _loadAlterPlug = None



def findKeyTimes(obj, start=None, end=None, customAttrs=[], includeCaps=True):
    ''' Returns a list of all the frames the given obj has keyframes at.

    Args:
        start: Optionally specify a beginning
        end: Optionally specify an end
        attrs: Optional additional attributes to search beyond the basic transforms
        includeCaps: If keyed at all and a start or end where given, include those keys
    
    Returns:
        Ascending list of keyframes, or empty list.
    
    Examples - If an obj has keys at 0, 5, 10, 15:
        findKeyTimes(obj ) => [0, 5, 10, 15]
        findKeyTimes(obj, start=5 ) => [5, 10, 15]
        findKeyTimes(obj, start=6 ) => [6, 10, 15] # Notice start will be returned even when unkeyed due to `includeCaps`
    
    '''
    attrs = customAttrs[:] + [t + a for t in 'trs' for a in 'xyz']

    
    times = set(keyframe( obj, at=attrs, q=True, tc=True, t=(start, end)))
    
    if includeCaps:
        if start and start not in times and times:
            times.add(start)
        if end and end not in times and times:
            times.add(end)
        
    return sorted(times)


def _processAttr(plug, dups, forceKeys, staticValues, start, end):
    '''
    Used by `save`
    '''

    crvs = cmds.listConnections( plug, type='animCurve' )
    
    if not crvs:
        if forceKeys:
            setKeyframe( plug, t=start )
            setKeyframe( plug, t=end )
            crvs = cmds.listConnections( plug, type='animCurve' )
        else:
            if not cmds.getAttr(plug, lock=True) and not cmds.listConnections(plug, s=True, d=False):
                staticValues[plug] = cmds.getAttr(plug)
    
    if crvs:
        dup = cmds.duplicate(crvs)[0]
        if not objExists(dup + '.' + TAGGING_ATTR):
            cmds.addAttr( dup, ln=TAGGING_ATTR, dt='string' )
        cmds.setAttr( dup + '.' + TAGGING_ATTR, plug, type='string' )
        dups.append( dup )


SavedCurveInfo = collections.namedtuple( 'SavedCurveInfo', 'start end length' )


def save(filename, objs=None, forceOverwrite=False, forceKeys=False, start=None, end=None):
    '''
    Given a list of objects, save all the anim curves for t/r/s/v and user defined
    to the given filename.
    
    :param bool forceOverwrite: Allow prompting if the dest file already exists
    :param bool forceKeys: Put keys on the objects
    
    ..  todo::
        * Check if an attribute ISN'T keyed in the source and mark the static
            value somehow.  Specifically, if parent/world stuff isn't present,
            copying animations goes poorly.
        * At some point animation layers need to be addressed properly.
    
    '''
    global TAGGING_ATTR
    # USING CMDS VERSION FOR SPEED
    #listAttr = cmds.listAttr
    #listConnections = cmds.listConnections
    #addAttr = cmds.addAttr
    #setAttr = cmds.setAttr
    #duplicate = cmds.duplicate
    # ---
    sel = selected()
    objs = objs if objs else selected()
    
    info = createNode( 'network' )
    info.addAttr('start', at='long')
    info.addAttr('end', at='long')
    info.addAttr('staticValues', dt='string')

    if start is None:
        start = playbackOptions(q=True, min=True)
    if end is None:
        end = playbackOptions(q=True, max=True)

    if start >= end:
        end = start + 1

    info.start.set( start )
    info.end.set( end )
    
    defaultAttrs = [t + a for t in 'trs' for a in 'xyz' ] + ['visibility']
    
    dups = []
    staticValues = {}
    
    for obj in objs:
        zooHack = ['ikBlend'] if obj.hasAttr('ikBlend') else []  # Since use uses builtin ik trans, this doesn't get picked up.
        
        if obj.hasAttr('tx'):
            attrs = chain( listAttr( obj.name(), ud=True, k=True ), defaultAttrs, zooHack )
        else:
            attrs = chain( listAttr( obj.name(), ud=True, k=True ), zooHack )

        for attr in attrs:
            _processAttr(obj.name() + '.' + attr, dups, forceKeys, staticValues, start, end)

    if not dups:
        warning("Nothing was animated")
        return
    
    info.staticValues.set(core.text.asciiCompress( json.dumps(staticValues) ))

    select(dups, info)
    exportSelected(filename, force=forceOverwrite)
    select( sel )
    delete(dups)


def load(filename, insertTime=None, alterPlug=None, bufferKeys=True, targetPool=None):
    '''
    Loads a file containing animCurves (made with `save`) and hooks them up.
    
    :param func alterPlug:  If the input needs some sort of transformation, provide
        a function that takes the plug string, ex "someSphere.tx" and returns
        a plug string of how it maps back, ex "zCube.tx" or "zCube.ty" and
        a function to alter the curve (or None)

        def alterPlug( 'inputNode.attr' ):
            return 'transformed'
        
    :param bool bufferKeys: If True (default), will add keys a frame before and
        after the range.
    '''
    global TAGGING_ATTR
    global _loadAlterPlug
    
    existingSelection = selected()
    
    # Hook for easily providing an alterPlug via the GUI
    if _loadAlterPlug and not alterPlug:
        alterPlug = _loadAlterPlug
        
    # Using cmds for speed
    getAttr = cmds.getAttr
    objExists = cmds.objExists
    ls = cmds.ls
    # ---
    
    if insertTime is None:
        insertTime = currentTime(q=True)
    
    missingObj = set()
    missingAttr = []
    pasteError = []
    
    newNodes = cmds.file( filename, i=True, rnn=True )
    
    curves = cmds.ls(newNodes, type='animCurve')
    info = ls(newNodes, type='network')[0]
    
    start = getAttr( info + '.start' )
    end = getAttr( info + '.end' )
    length = end - start
    
    attr = '.' + TAGGING_ATTR
    
    singleObj = ''
    
    if len(existingSelection) == 1:
        targetObj = getAttr( curves[0] + attr ).split('.')[0]
        for c in curves:
            loadedTarget = getAttr( c + attr ).split('.')[0]
            # FKIK_SWITCH is a hack to deal with the switching attr if a single
            # obj is selected
            if loadedTarget != targetObj and not loadedTarget.endswith('FKIK_SWITCH'):
                break
        else:
            singleObj = targetObj
            
    if singleObj:
        targetObj = existingSelection[0].longName()
        
        def alter(plug):
            return targetObj + '.' + plug.split('.')[-1], None
    else:
        # Determine if there is a namespace mismatch
        if alterPlug:
            targets = [ alterPlug(cmds.getAttr(crv + attr ))[0].split('.')[0] for crv in curves ]
        else:
            targets = [ cmds.getAttr(crv + attr ).split('.')[0] for crv in curves ]
            
        changeNamespace = None
        
        newTargets = core.names.findAlternates(targets, targetPool)
        
        global JUNK
        JUNK = targets
        
        if newTargets.alteration:
            print( 'NS change', '--' * 20, newTargets.alteration )
            if newTargets.alteration[0] == 'add':
                def changeNamespace(plug):
                    return newTargets.alteration[1] + plug
            elif newTargets.alteration[0] == 'sub':
                def changeNamespace(plug):
                    return plug.replace( newTargets.alteration[1], newTargets.alteration[2] )
            elif newTargets.alteration[0] == 'rem':
                def changeNamespace(plug):
                    return plug.replace( newTargets.alteration[1], '' )
                    
        # Build an alteration function if needed
        alter = None
        if alterPlug and changeNamespace:
            def alter(plug):
                newPlug, curveEditFunc = alterPlug(changeNamespace(plug))
                return newPlug, curveEditFunc
        elif alterPlug:
            alter = alterPlug
        elif changeNamespace:
            def alter(plug):
                return changeNamespace(plug), None
    
    if hasAttr(PyNode(info), 'staticValues'):
        keys = json.loads(core.text.asciiDecompress( getAttr(info + '.staticValues')))

        for plug, value in keys.items():
            try:
                if alter:
                    setAttr(alter(plug), value)
                else:
                    setAttr(plug, value)
            except Exception:
                pass

    # Finally, actually copy over the animation
    for node in curves:
        alterCurve = None
        if objExists( node + '.' + TAGGING_ATTR ):
            dest = getAttr( node + '.' + TAGGING_ATTR )
            if alter:
                dest, alterCurve = alter(dest)
            
            if alterCurve:
                alterCurve(node)
            
            if objExists( dest ):
                
                # If we aren't going to be able to paste, just punt.
                if not getAttr(dest, k=True):
                    pasteError.append(dest)
                    continue
                                    
                if bufferKeys or getAttr(node, s=1) <= 1:
                    setKeyframe( node, time=(insertTime - 1), insert=True )
                    setKeyframe( node, time=(insertTime + length + 1), insert=True )
                
                copyKey( node, time=(start, end), iub=True, option='curve' )
                
                try:
                    pasteKey( dest, time=(insertTime, insertTime + length), option='replace' )
                except Exception:
                    pasteError.append( dest )
            else:
                obj, attr = dest.split('.')
                if objExists(obj):
                    missingAttr.append( dest )
                else:
                    missingObj.add( obj )
                    
    if missingObj:
        print( core.text.writeInBox( "These objects don't exist:\n\n" + '\n'.join(missingObj) ) )
    if missingAttr:
        print( core.text.writeInBox( "These attribute couldn't be found:\n\n" + '\n'.join(missingAttr) ) )
    if pasteError:
        print( core.text.writeInBox( "Errors occurred when pasting animation onto:\n\n" + '\n'.join(pasteError) ) )
        
    if missingObj or missingAttr or pasteError:
        warning( 'Completed but with errors. See script editor for details.' )
        
    delete( newNodes )
    
    return SavedCurveInfo( insertTime, insertTime + length, length )


def findSetDrivenKeys(control):
    '''
    Return a list of strings specially formatted with setDrivenKey data.
    '''
    sdkCurves = control.listConnections(s=True, d=False, type=['animCurveUA', 'animCurveUT', 'animCurveUU', 'animCurveUL'])
    
    curveText = []

    for sdkCurve in sdkCurves:
        input = sdkCurve.input.listConnections(p=1, scn=True)[0]
        dest = sdkCurve.output.listConnections(p=1, scn=True)[0].attrName()
        
        curveText.append( (dest, getIds(input.node()), input.attrName(), curveToData(sdkCurve) ) )
    
    return curveText


def applySetDrivenKeys(ctrl, infos):
    '''
    Create the setDrivenKeys on the ctrl with the specially formatted string
    list from `findSetDrivenKeys`.
    '''
    
    for info in infos:
        drivenAttr, driveNode, driveAttr, data = info
        
        node = findFromIds(driveNode)
        cutKey(ctrl.attr(drivenAttr), cl=True)
        
        #keyData = [KeyData(*d) for d in data]
        
        if isinstance(data, list):
            setDrivenKeyframe( ctrl, at=[drivenAttr], v=-.14, cd=node.attr(driveAttr), dv=[data[0]['time']] )
        else:
            setDrivenKeyframe( ctrl, at=[drivenAttr], v=-.14, cd=node.attr(driveAttr), dv=[data['keys'][0]['time']] )
                
        dataToCurve(data, ctrl.attr(drivenAttr) )
        

class KeyData(object):
    def __init__(self, time, val, inAngle, outAngle, inWeight, outWeight, inType, outType):
        self.time = time
        self.val = val
        self.inAngle = inAngle
        self.outAngle = outAngle
        self.inWeight = inWeight
        self.outWeight = outWeight
        self.inType = inType
        self.outType = outType
    
    def toDict(self):
        d = {}
        d['time'] = self.time
        d['val'] = self.val
        d['inAngle'] = self.inAngle
        d['outAngle'] = self.outAngle
        d['inWeight'] = self.inWeight
        d['outWeight'] = self.outWeight
        d['inType'] = self.inType
        d['outType'] = self.outType
        return d


def curveToData(animCurve):
    keys = keyframe(animCurve, q=True, tc=True, fc=True, vc=True)  # fc and tc are mutually ex
    
    tangents = keyTangent(animCurve, q=True, ia=True, oa=True, iw=True, ow=True, itt=True, ott=True)
    chunk = 6 # keyTanget returns a giant flat list

    keyData = []
    for i, key in enumerate(keys):
        keyData.append( KeyData(key[0], key[1], *tangents[i * chunk:(i + 1) * chunk]).toDict() )
    
    return {'keys': keyData, 'preInfinity': animCurve.preInfinity.get(), 'postInfinity': animCurve.postInfinity.get()}


def dataToCurve(allData, plug):
    
    if isinstance(allData, dict):
        data = allData['keys']
    else:
        data = allData
        allData = None
    
    cutKey(plug, t=(data[0]['time'], data[-1]['time']), cl=True, iub=True)
    for key in data:
        setKeyframe(plug, f=key['time'], t=key['time'], v=key['val'])
    
    for key in data:
        keyTangent(plug, f=(key['time'],), t=key['time'], ia=key['inAngle'], oa=key['outAngle'], iw=key['inWeight'], ow=key['outWeight'], itt=key['inType'], ott=key['outType'])
    
    if allData:
        node = plug.listConnections(s=True)[0]
        node.preInfinity.set( allData['preInfinity'] )
        node.postInfinity.set( allData['postInfinity'] )
        
        
def orientJoint(jnt, target, upTarget=None, aim='x', up='y', upVector=None):
    '''
    Orient an object (doesn't have to be a joint) to the target.  Basically a
    code only aiming.
    
    :param PyNode jnt: The joint to orient
    :param PyNode target: The object to orient to.
    :param PyNode/upTarget pos: A PyNode or position [x,y,z] for the up vector
    :param upVector: If specified, upTarget is not needed
    :param chr aim:
    
    This works for aim=x, up=y and negative versions
    
    Things to investigate:
        * Sometimes the rotations are different but that turns out to be -0.0 in
        the matrix.  AFAIK, everything still ends up fine.
            # Adept ends up with the same JOs!
            # Minotaur is the same
        
        * It looks like rotate order doesn't matter
    
    It's (almost) an all code version of:

        if isinstance(pos, PyNode):
            upObj = pos
        else:
            upObj = spaceLocator()
            upObj.t.set( pos )
        
        aim = axisConvert(aim)
        up = axisConvert(up)
        
        # Temporarily unparent children and clear orientation.
        with lib.core.dagObj.Solo( jnt ):
            jnt.r.set(0, 0, 0)
            jnt.jo.set(0, 0, 0)
            
            const = aimConstraint( target, jnt, aim=aim, u=up, wut='object', wuo=upObj )
            jnt.jo.set( jnt.r.get() )
            delete( const )
            jnt.r.set(0, 0, 0)

        def axisConvert( axisChar ):
            """
            Turn a character representing an axis into 3 numbers, ex x = [1,0,0], -y = [0,-1,0]
            
            :param char axisChar: Either "x", "y" or "z", possibly negated, eg: "-x"
            """
            axis = [0, 0, 0]
            c = axisChar[-1]
            axis[ ord(c) - ord('x') ] = -1 if axisChar.startswith('-') else 1
            return axis
    '''

    #print jnt, target, pos, aim, up
    jPos = dt.Vector(cmds.xform(str(jnt), q=True, ws=True, t=True))
    
    if not isinstance(target, dt.Vector):
        tPos = dt.Vector(cmds.xform(str(target), q=True, ws=True, t=True))
    else:
        tPos = target
    
    if not upVector:
        if isinstance(upTarget, PyNode):
            uPos = dt.Vector(cmds.xform(str(upTarget), q=True, ws=True, t=True))
        else:
            uPos = dt.Vector(upTarget)
            
        upV = uPos - jPos
        if up[0] == '-':
            upV *= -1.0
        upV.normalize()
    else:
        upV = dt.Vector(upVector)
        upV.normalize()

    aimV = tPos - jPos
    if aim[0] == '-':
        aimV *= -1.0
    aimV.normalize()
    
    # The aim/up order determines if it's aim.cross(up) or up.cross(aim) for the final axis
    if aim[-1] == 'x' and up[-1] == 'y':
        mainCross = _forwardCross
        finalCross = _forwardCross
    elif aim[-1] == 'x' and up[-1] == 'z':
        mainCross = _reverseCross
        finalCross = _reverseCross

    elif aim[-1] == 'y' and up[-1] == 'z':
        mainCross = _forwardCross
        finalCross = _forwardCross
    elif aim[-1] == 'y' and up[-1] == 'x':
        mainCross = _reverseCross
        finalCross = _reverseCross

    elif aim[-1] == 'z' and up[-1] == 'x':
        mainCross = _forwardCross
        finalCross = _forwardCross
    elif aim[-1] == 'z' and up[-1] == 'y':
        mainCross = _reverseCross
        finalCross = _reverseCross

    finalAxis = mainCross(aimV, upV)
    finalAxis.normalize()
    
    # aimV and upV are probably not perpendicular, but finalAxis was built
    # perpendicular to both so rebuild upV from aimV and finalAxis
    #newUp = finalAxis.cross(aimV)
    newUp = finalCross(finalAxis, aimV)
    newUp.normalize()

    axes = [None, None, None]
    
    if aim[-1] == 'x':
        axes[0] = list(aimV) + [0.0]
    elif aim[-1] == 'y':
        axes[1] = list(aimV) + [0.0]
    else:
        axes[2] = list(aimV) + [0.0]
    
    if up[-1] == 'x':
        axes[0] = list(newUp) + [0.0]
    elif up[-1] == 'y':
        axes[1] = list(newUp) + [0.0]
    else:
        axes[2] = list(newUp) + [0.0]

    for i, v in enumerate(axes):
        if not v:
            axes[i] = list(finalAxis) + [0.0]
    
    axes.append( list(jnt.t.get()) + [1.0] )

    r = core.math.eulerFromMatrix(axes, degrees=True)

    # Temporarily unparent children and clear orientation.
    with core.dagObj.TempWorld(jnt):
        with core.dagObj.Solo( jnt ):
            if jnt.type() == 'joint':
                jnt.r.set(0, 0, 0)
                jnt.jo.set(r)
            else:
                jnt.r.set(r)
                

def _forwardCross(a, b):
    return a.cross(b)


def _reverseCross(a, b):
    return b.cross(a)
    

if 'FBX_ANIM_PRESETS_FILE' not in globals():
    FBX_ANIM_PRESETS_FILE = ''
    # Path to an fbx presents file used by `fbxExport`, protected against development reset.


def preFbxExport(*args):
    # Replace this with a function taking the same args as fbxExport to do anything
    # special, like check out the file.
    pass


def postFbxExport(*args):
    # Replace this with a function taking the same args as fbxExport to do anything
    # special, like check in the file.
    pass


def fbxExport(objs, start, end, filepath):
    '''
    Convenience function to export fbx animations.
    
    :param node/list objs: An object, or list, to export.  Most likely Rig:b_root.
    :param int start: The beginning of the range to export.
    :param int end: The end of the range to export.
    :param string filepath: The full name to export.
    '''
    assert os.path.exists(FBX_ANIM_PRESETS_FILE), 'FBX presets file "%s" does not exist' % FBX_ANIM_PRESETS_FILE
    
    # Ensure directories exist
    filepath = filepath.replace('\\', '/')
    if not os.path.exists( os.path.dirname(filepath) ):
        os.makedirs( os.path.dirname(filepath) )
    
    select(objs)
    
    mel.FBXPushSettings()
    mel.FBXResetExport()
    
    # Preset path MUST use forward slashes.
    mel.eval('FBXLoadExportPresetFile -f "{0}"'.format(FBX_ANIM_PRESETS_FILE.replace('\\', '/')) )
    mel.eval('FBXExportBakeComplexStart -v {0}'.format(start) )
    mel.eval('FBXExportBakeComplexEnd -v {0}'.format(end) )

    try:
        preFbxExport(objs, start, end, filepath)
        mel.eval('FBXExport -f "%s" -s' % filepath)
        postFbxExport(objs, start, end, filepath)
    finally:
        mel.FBXPopSettings()
