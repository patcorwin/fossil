from __future__ import print_function, absolute_import

from collections import OrderedDict
try: # python 3 compatibility
    from itertools import izip as zip
except ImportError:
    pass
import json
import os
import tempfile
import traceback

from maya.api.OpenMayaAnim import MFnSkinCluster

from pymel.core import cmds, dt, duplicate, mel, listConnections, listRelatives, skinCluster, select, selected, PyNode, warning, polyUnite, delete, objExists, skinPercent

from . import capi
from .. _add import shortName

__all__ = [
    'get',
    'substGen',
    'processWeightData',
    'apply',
    'save',
    'load',
    'mergePieces',
    'weightChildren',
    'findRelatedSkinCluster',
    'addMissingJoints',
    'removeUnwantedInfluence',
    'skeletonToJson',
    'copySkinning',
    'findBoundMeshes',
    'parallelTransfer',
]


'''
Timing tests on a 44k vert mesh, generally under 0.2s to save! under 2s load.

### get_slow() uses the regular commands to query weights.  Not bad, but not good.
import time
start = time.time()
w = weights.get_slow(o)
print( time.time() - start )

~ 4.2 seconds


### Investigating using mel to get weights directly instead of skinPercent.  While this isn't the full deal
#   it's much faster than skinPercent.
mga = cmds.getAttr
start = time.time()
temp = {}
for i in xrange( mesh.vtx.count() ):
    temp[i] = mga( 'skinCluster1.weightList[%i].weights' % i )
print( time.time() - start )

~ 0.6 seconds


### Test getting weight values from the api.  0.04 was common but sometimes as high as 0.15.
#   This is totally nuts how fast this is!
start = time.time()
t2 = []

skinClusterName = mel.findRelatedSkinCluster(mesh)

skinClusterMObj = capi.asMObject( skinClusterName )
skinFn = MFnSkinCluster( skinClusterMObj.object() )
weightListPlug = skinFn.findPlug( 'weightList', True )
weightListObj = weightListPlug.attribute()
weightsPlug = skinFn.findPlug( "weights", True )

for vertIdx in xrange( mesh.vtx.count() ):
    
    #we need to use the api to query the physical indices used
    weightsPlug.selectAncestorLogicalIndex( vertIdx, weightListObj )
    tmpIntArray = weightsPlug.getExistingArrayAttributeIndices()
    t2.append( list(tmpIntArray) )

print( time.time() - start )

~ 0.04 - 0.15

### Finally, the full test
start = time.time()
asdf = w.get(o)
print( time.time() - start )


SET
start = time.time()
weights.set(o, w)
print( time.time() - start )

1.6 - 1.7

'''

try:  # 3.x catch for xrange
    xrange
except Exception:
    xrange = range


def get_slow(mesh):
    '''
    Given a mesh, returns a list, one entry per vertex, with a list of (joint, value) pairs.
    ex:
        [0] = [ (ja, .5), (jb, .5) ]
        [1] = [ (ja, .5), (jb, .25), (jc, .25) ]
    '''

    skinClusterName = mel.findRelatedSkinCluster(mesh)
    
    joints = cmds.skinCluster(mesh.name(), q=True, inf=True)
    
    weights = []
    
    required = {}
    for j in joints:
        parent = cmds.listRelatives(j, p=True)
        required[j] = [parent[0] if parent else None] + cmds.xform(j, q=True, ws=True, t=True)
    
    info = {
        'joints': required,
        'weights': weights,
    }
    
    vtxStr = mesh.name() + '.vtx[%i]'
    for i in xrange(mesh.vtx.count()):
        weights.append( [(t, v) for t, v in zip(joints, cmds.skinPercent(skinClusterName, vtxStr % i, q=1, v=1)) if v > 0] )
    
    return info


def get(mesh):
    '''
    Creates as dictionary that looks like the following:
    
    {
        'weights': [   ], # index is vertex index, value is list of bone, weight pairs
        [0] = [ (<jn index>, .75), ('j2', .25) ]...
        'jointNames': ['joint1', joint2]
        'joints': {
            <index into jointNames> : [<parent index into jointNames>, global_x, global_y, global_z]
            ...
        'required': [<index into jointNames/joints>]
        }
    }
    '''
    
    ''' DEBUG
    from pdil.core import capi
    from maya.api.OpenMayaAnim import MFnSkinCluster
    '''
    
    skinClusterName = mel.findRelatedSkinCluster(mesh)
    
    skinClusterMObj = capi.asMObject( skinClusterName )
    skinFn = MFnSkinCluster( skinClusterMObj.object() )
    
    #construct a dict mapping joint names to joint indices
    jointApiIndices = {}

    jointNames = []
    #jointNameLookup = {}

    for i, jointDagMObj in enumerate(skinFn.influenceObjects()):
        #jointApiIndices[ skinFn.indexForInfluenceObject( jointDagMObj ) ] = jointDagMObj.partialPathName()
        jointApiIndices[ skinFn.indexForInfluenceObject( jointDagMObj ) ] = i

        jointNames.append(jointDagMObj.partialPathName())

    weightListPlug = skinFn.findPlug( 'weightList', True )
    weightListObj = weightListPlug.attribute()
    weightsPlug = skinFn.findPlug( 'weights', True )

    
    weights = [None] * mesh.vtx.count()  # Prebuilding the whole range is nearly instant, appending is probably slower
    # since it will trigger resizing.
    
    for vertIdx in xrange(mesh.vtx.count()):  # noqa
        # We need to use the api to query the physical indices used
        weightsPlug.selectAncestorLogicalIndex( vertIdx, weightListObj )
        activeJointIndices = weightsPlug.getExistingArrayAttributeIndices()
        
        # Values = cmds_getAttr( baseFmtStr % vertIdx + '.weights' )[0] # api 2.0 is 0.09 instead of  0.25
        values = [weightsPlug.elementByLogicalIndex(i).asDouble() for i in activeJointIndices]
        
        try:
            # If `i` isn't in jointApiIndices, that value is skipped.  Not sure why these garbage values are just left behind...
            weights[vertIdx] = [ [jointApiIndices[idx], v] for idx, v in zip( activeJointIndices, values ) if idx in jointApiIndices]
        except Exception:
            raise
            '''
            weights[vertIdx] = []
            # This gets hit when an influence object has been removed
            for i, v in zip(activeJointIndices, values):
                if v > 0.000001:
                    weights[vertIdx].append( (jointApiIndices[i], v) )
            '''
    
    # Prune out the unused joints (Maybe make an option?)
    joints = {}
    requiredJoints = set()
    for wgt in weights:
        for j, v in wgt:
            requiredJoints.add(j)
    
    def parentName(jnt):
        parent = cmds.listRelatives(j, p=True)
        if parent:
            try:
                return jointNames.index( parent[0] )
            except ValueError:
                return parent[0]

        return None

    # Save the joint's parent and worldspace position, for possible future use/issue detection.
    for i, j in enumerate(jointNames):
        joints[i] = [parentName(j)] + cmds.xform(j, q=True, ws=True, t=True)
    
    # required is built as a set, but then changed to a list for easy json serialization
    return {'weights': weights, 'joints': joints, 'jointNames': jointNames, 'required': list(requiredJoints)}


def get_old(mesh):
    '''
    Creates as dictionary that looks like the following:
    
    {
        'weights': [   ], # index is vertex index, value is list of bone, weight pairs
        [0] = [ ('j1', .75), ('j2', .25) ]...
        
        'joints': {
            'j1': [parent, global_x, global_y, global_z]
            ...
        }
    }
    '''
    
    ''' DEBUG
    from pdil.core import capi
    from maya.api.OpenMayaAnim import MFnSkinCluster
    '''
    
    
    skinClusterName = mel.findRelatedSkinCluster(mesh)
    
    skinClusterMObj = capi.asMObject( skinClusterName )
    skinFn = MFnSkinCluster( skinClusterMObj.object() )
    
    #construct a dict mapping joint names to joint indices
    jointApiIndices = {}
    
    for jointDagMObj in skinFn.influenceObjects():
        jointApiIndices[ skinFn.indexForInfluenceObject( jointDagMObj ) ] = jointDagMObj.partialPathName()
        
    weightListPlug = skinFn.findPlug( 'weightList', True )
    weightListObj = weightListPlug.attribute()
    weightsPlug = skinFn.findPlug( 'weights', True )
    
    weights = [None] * mesh.vtx.count() # Prebuilding the whole range is nearly instant, appending is probably slower
    # since it will trigger resizing.
    
    for vertIdx in xrange(mesh.vtx.count()):  # noqa
        # We need to use the api to query the physical indices used
        weightsPlug.selectAncestorLogicalIndex( vertIdx, weightListObj )
        activeJointIndices = weightsPlug.getExistingArrayAttributeIndices()
        
        # Values = cmds_getAttr( baseFmtStr % vertIdx + '.weights' )[0] # api 2.0 is 0.09 instead of  0.25
        values = [weightsPlug.elementByLogicalIndex(i).asDouble() for i in activeJointIndices]
        
        try:
            # If `i` isn't in jointApiIndices, that value is skipped.  Not sure why these garbage values are just left behind...
            weights[vertIdx] = [ (jointApiIndices[idx], v) for idx, v in zip( activeJointIndices, values ) if idx in jointApiIndices]
        except Exception:
            raise
            '''
            weights[vertIdx] = []
            # This gets hit when an influence object has been removed
            for i, v in zip(activeJointIndices, values):
                if v > 0.000001:
                    weights[vertIdx].append( (jointApiIndices[i], v) )
            '''
    
    # Prune out the unused joints (Maybe make an option?)
    joints = {}
    requiredJoints = set()
    for wgt in weights:
        for j, v in wgt:
            requiredJoints.add(j)
    
    # Save the joint's parent and worldspace position, for possible future use/issue detection.
    for j in requiredJoints:
        parent = cmds.listRelatives(j, p=True)
        joints[j] = [parent[0] if parent else None] + cmds.xform(j, q=True, ws=True, t=True)
    
    
    return {'weights': weights, 'joints': joints}
    
    
    
def substGen(weightData, renames={}, explicitSubst={}):
    requiredJoints = weightData['joints'].keys()
    
    subst = explicitSubst.copy()
    
    for jnt in requiredJoints:
        # Skip over joints that exist or have already been substituted
        if objExists(jnt) or (jnt in subst and objExists(subst[jnt])):
            continue
        
        for oldStr, newStr in renames.items():
            if oldStr in jnt:
                newJoint = jnt.replace(oldStr, newStr)
                if objExists(newJoint):
                    subst[jnt] = newJoint
                    break
        else:
            print('No subst for', jnt)
    
    return subst


def processWeightData(weight_data, remove=[], replace=OrderedDict()):
    ''' Replace and rebalance joints, then remove.
    
    replace = {<joint to remove>: <joint to replace it>}
    '''
    requiredJoints = weight_data['joints'].keys()
    
    weights = weight_data['weights']
    
    jointNames = weight_data['jointNames']

    # Replace the old joint with the new joint
    for oldJoint, newJoint in replace.items():

        oldIndex = jointNames.index(oldJoint)
        newIndex = jointNames.index(newJoint) if newJoint in jointNames else None

        # If needed, add the new joint to the list of required joints
        if newIndex not in requiredJoints:
            newIndex = len(weight_data['jointNames'])
            if objExists(newJoint):
                parent = listRelatives(newJoint, p=True)
                if parent and shortName(parent) in jointNames:
                    weight_data['joints'][newIndex] = [jointNames.index(shortName(parent))] + cmds.xform(newJoint, q=True, ws=True, t=True)
            
            if newIndex not in weight_data['joints']:
                weight_data['joints'][newIndex] = [None, 0, 0, 0] # Dummy value so the parent info update sections runs

            weight_data['jointNames'].append(newJoint)

        for data in weights:
            for i, (jnt, val) in enumerate(data):
                if jnt == oldIndex:
                    data[i][0] = newIndex
    
    # Update all the weights to reflect new joints
    for data in weights:
        # If a subst removal resulted in multiple weights, combine them
        if len({jnt for jnt, val in data}) != len(data):
            
            cleaned = {}
            for jnt, val in data:
                cleaned.setdefault(jnt, 0)
                cleaned[jnt] += val
            data[:] = [ [jnt, val] for jnt, val in cleaned.items() ]
    
    # Compile {old joint index: joint index to fallback to}
    parentFallback = {}
    indicesToRemove = {jointNames.index(name) for name in remove} | {jointNames.index(name) for name in replace}

    for i in range(len(jointNames)):
        if i not in indicesToRemove:
            validFallbackIndex = i
            break

    for index in indicesToRemove:
        parentIndex = weight_data['joints'][index][0]
        while parentIndex in indicesToRemove and parentIndex is not None:
            parentIndex = weight_data['joints'][parentIndex][0]

        if parentIndex is not None:
            parentFallback[index] = parentIndex
        else:
            parentFallback[index] = validFallbackIndex

    # Finally the joints can be removed
    for name in remove:
        index = jointNames.index(name)
        for data in weights:
            newData = [[jnt, val] for jnt, val in data if jnt != index]

            # Removed entirely, fallback to a parent
            if len(newData) == 0:
                data[:] = [[ parentFallback[index], 1.0]]

            # Recalc since a joint was removed
            elif len(newData) < len(data):
                total = sum([val for jnt, val in newData])
                data[:] = [ [jnt, val / total] for jnt, val in newData ]

    
def _adjustForNamespace(jointNames):
    alts = cmds.ls( [name.rsplit(':', 1)[-1] for name in jointNames], r=True)
    if len(alts) == len(jointNames):
        return alts
    return []
    

def apply(mesh, weight_data, targetVerts=None):
    '''
    weights = [
        vertIndex: [ (jointA, val), (jointB, val) ]
    ]
    
    '''
    
    '''
    skinCluster.weightList[ vertexIndex ].weights[ jointIndex ] = weightValue
    '''

    jointNames = weight_data['jointNames']

    assert len(set(jointNames)) == len(jointNames), 'Duplicate joint names exist, which probably means a subsitution failed'

    requiredJoints = [jointNames[index] for index in weight_data['required']]
    
    weights = weight_data['weights']
    
    #joints = weight_data['joints']
    missing = [j for j in requiredJoints if not objExists(j)]

    if missing:
        alts = _adjustForNamespace(jointNames)
        if alts:
            jointNames = alts
            requiredJoints = [jointNames[index] for index in weight_data['required']]
        else:
            print('Unable to weight, missing the following joints:\n' + '\n'.join(missing))
            return
    
    skinClusterName = mel.findRelatedSkinCluster(mesh)
    
    
    # If no skin cluster exists, bind it
    if not skinClusterName:
        temp = skinCluster(mesh, requiredJoints, tsb=True, skinMethod=0, bindMethod=0, removeUnusedInfluence=False)
        skinClusterName = temp.name()
    # Otherwise make sure the joints given in `weights` are part of the skin cluster
    else:
        joints = cmds.skinCluster( skinClusterName, q=True, inf=True )
        missing = [j for j in requiredJoints if j not in joints]
        
        if missing:
            cmds.skinCluster(skinClusterName, e=True, addInfluence=missing, weight=0.0)
        
    
    skinClusterMObj = capi.asMObject( skinClusterName )
    skinFn = MFnSkinCluster( skinClusterMObj.object() )
    
    #construct a dict mapping joint names to joint indices
    jointApiIndices = {}

    for jointDagMObj in skinFn.influenceObjects():
        #jointApiIndices[ jointDagMObj.partialPathName() ] = skinFn.indexForInfluenceObject( jointDagMObj )
        # Might need to more rigorously verify, catching objs with the same
        jointApiIndices[ jointNames.index(jointDagMObj.partialPathName()) ] = skinFn.indexForInfluenceObject( jointDagMObj )
        
    weightListPlug = skinFn.findPlug( 'weightList', True )
    weightListObj = weightListPlug.attribute()
    weightsPlug = skinFn.findPlug( 'weights', True )
    
    # Prebuild the string for speed
    baseFmtStr = skinClusterName + '.weightList[%d]'
    # Set mel commands for direct local access, which could provide a slight speed benefit
    #cmds_setAttr = cmds.setAttr
    cmds_removeMultiInstance  = cmds.removeMultiInstance
    
    if not targetVerts:
        targetVerts = xrange(len(weights))
        
    for vertIdx in targetVerts:
        
        jointsAndWeights = weights[vertIdx]
        #cmds_removeMultiInstance( baseFmtStr % vertIdx )  # Removing parent element is not faster.
        
        #we need to use the api to query the physical indices used
        vertIdx = int(vertIdx)
        weightsPlug.selectAncestorLogicalIndex( vertIdx, weightListObj )
        activeJointIndices = weightsPlug.getExistingArrayAttributeIndices()
        
        weightFmtStr = baseFmtStr % vertIdx + '.weights[%d]'
        # Can't find a way to do this in the api, so call it as little as possible.  Down to .25 with identical weights (.2 bypassing the check).
        for jointIndex in set(activeJointIndices).difference( [jointApiIndices[ joint ] for joint, w in jointsAndWeights] ):
            cmds_removeMultiInstance( weightFmtStr % jointIndex )
            
        # Need to test if api 2.0 is faster than mel
        for joint, weight in jointsAndWeights:
            if weight:
                influenceIndex = jointApiIndices[ joint ]
                #cmds_setAttr( weightFmtStr % influenceIndex, weight )  # Using the api takes it from 1.6 to .9s!
                weightsPlug.elementByLogicalIndex(influenceIndex).setDouble(weight)
                try:
                    activeJointIndices.remove(influenceIndex)
                except Exception:
                    pass



def apply_old(mesh, weight_data, targetVerts=None):
    '''
    weights = [
        vertIndex: [ (jointA, val), (jointB, val) ]
    ]
    
    '''
    
    '''
    skinCluster.weightList[ vertexIndex ].weights[ jointIndex ] = weightValue
    '''

    requiredJoints = weight_data['joints'].keys()
    
    weights = weight_data['weights']
    
    #joints = weight_data['joints']
    missing = [j for j in requiredJoints if not objExists(j)]

    if missing:
        print('Unable to weight, missing the following joints:\n' + '\n'.join(missing))
        return
    
    skinClusterName = mel.findRelatedSkinCluster(mesh)
    
    
    
    # If no skin cluster exists, bind it
    if not skinClusterName:
        temp = skinCluster(mesh, requiredJoints, tsb=True)
        skinClusterName = temp.name()
    # Otherwise make sure the joints given in `weights` are part of the skin cluster
    else:
        joints = cmds.skinCluster( skinClusterName, q=True, inf=True )
        missing = [j for j in requiredJoints if j not in joints]
        
        if missing:
            cmds.skinCluster(skinClusterName, e=True, addInfluence=missing, weight=0.0)
        
    
    skinClusterMObj = capi.asMObject( skinClusterName )
    skinFn = MFnSkinCluster( skinClusterMObj.object() )
    
    #construct a dict mapping joint names to joint indices
    jointApiIndices = {}
    
    for jointDagMObj in skinFn.influenceObjects():
        jointApiIndices[ jointDagMObj.partialPathName() ] = skinFn.indexForInfluenceObject( jointDagMObj )
        
    weightListPlug = skinFn.findPlug( 'weightList', True )
    weightListObj = weightListPlug.attribute()
    weightsPlug = skinFn.findPlug( 'weights', True )
    
    # Prebuild the string for speed
    baseFmtStr = skinClusterName + '.weightList[%d]'
    # Set mel commands for direct local access, which could provide a slight speed benefit
    #cmds_setAttr = cmds.setAttr
    cmds_removeMultiInstance  = cmds.removeMultiInstance
    
    if not targetVerts:
        targetVerts = xrange(len(weights))
        
    for vertIdx in targetVerts:
        
        jointsAndWeights = weights[vertIdx]
        #cmds_removeMultiInstance( baseFmtStr % vertIdx )  # Removing parent element is not faster.
        
        #we need to use the api to query the physical indices used
        vertIdx = int(vertIdx)
        weightsPlug.selectAncestorLogicalIndex( vertIdx, weightListObj )
        activeJointIndices = weightsPlug.getExistingArrayAttributeIndices()
        
        weightFmtStr = baseFmtStr % vertIdx + '.weights[%d]'
        
        # Can't find a way to do this in the api, so call it as little as possible.  Down to .25 with identical weights (.2 bypassing the check).
        for jointIndex in set(activeJointIndices).difference( [jointApiIndices[ joint ] for joint, w in jointsAndWeights] ):
            cmds_removeMultiInstance( weightFmtStr % jointIndex )
            
        # Need to test if api 2.0 is faster than mel
        for joint, weight in jointsAndWeights:
            if weight:
                influenceIndex = jointApiIndices[ joint ]
                #cmds_setAttr( weightFmtStr % influenceIndex, weight )  # Using the api takes it from 1.6 to .9s!
                weightsPlug.elementByLogicalIndex(influenceIndex).setDouble(weight)
                try:
                    activeJointIndices.remove(influenceIndex)
                except Exception:
                    pass
    

def save(objs=None, outfile=''):
    
    if not outfile:
        tempdir = tempfile.gettempdir() + '/pdil'
        if not os.path.exists(tempdir):
            os.makedirs(tempdir)
        
        outfile = tempdir + '/temp_weights.json'

    if not objs:
        objs = selected()
    
    allWeights = {}
    
    for s in objs:
        allWeights[s.fullPath()] = get(s)
    
    with open(outfile, 'w') as fid:
        json.dump(allWeights, fid, indent=4)
        
        
def _loadTempWeight():
    directions = tempfile.gettempdir() + '/pdil/temp_weights.json'
    
    if not os.path.exists(directions):
        warning('Temp file of weights not found, ' + directions)
        return None
        
    with open(directions, 'r') as fid:
        data = json.load(fid)
    
    return data
        
        
def load(jsonfile='', subst={}, remove=[], replace=OrderedDict()):
    if not jsonfile:
        data = _loadTempWeight()
    else:
        with open(jsonfile, 'r') as fid:
            data = json.load(fid)
    
    for mesh, weightData in data.items():
        
        if subst or remove or replace:
            processWeightData(weightData, subst, remove, replace)
        
        apply( PyNode(mesh), weightData)
    
        
def __load(targetMesh, targetSkeletonRoot):
    data = _loadTempWeight()
    
    if not data:
        return
    
    skiningData = data.values()[0]
    
    # Map all the joints in the file to the joints in the targetSkeletonRoot
    
    targetJoints = {j: [] for j in listRelatives(targetSkeletonRoot, ad=True, type='joint')}
    targetJoints[PyNode(targetSkeletonRoot)] = []
    
    #print(skiningData['joints'].values()[0])
    sourceTrans = {j: dt.Vector( info[1:4] ) for j, info in skiningData['joints'].items()}
    targetTrans = {target: target.getTranslation(space='world') for target in targetJoints}
    
    #for target in targetJoints:
    #    trans = target.getTranslation(space='world')
    for srcJ, srcPos in sourceTrans.items():
        dists = [((srcPos - tgtPos).length(), tgtJ) for tgtJ, tgtPos in targetTrans.items()]
        dists.sort()
        print(srcJ, list((dists))[-3:])
            

def mergePieces(objs=None, keepSource=False):
    '''
    Combine the skinned objects into one nicely skinned object with clean history.
    '''
    dups = []
    merged = None
    try:
        if not objs:
            objs = selected()
        
        weight_data = { 'weights': [], 'joints': {}, 'jointNames': [] }
        for obj in objs:
            if not findRelatedSkinCluster(obj):
                warning("{0} wasn't bound, all objects must be bound to merge".format(obj))
                return
            dups.append( duplicate(obj)[0].name(long=True) )
            temp = get(obj)
            
            # Possibly add new jointNames, and then update the index references in the weighting
            newJointIndex = {}
            for i, jName in enumerate(temp['jointNames']):
                try:
                    newIndex = weight_data['jointNames'].index(jName)
                except ValueError:
                    newIndex = len(weight_data['jointNames'])
                    weight_data['jointNames'].append(jName)
                
                newJointIndex[i] = newIndex
            
            altered = [[(newJointIndex[oldIndex], val) for oldIndex, val in w] for w in temp['weights']]
            
            
            weight_data['weights'] += altered
            
            #weight_data['joints'].update( temp['joints'] )
        
        # Cheesily assume all joints are required
        weight_data['required'] = list(range(len(weight_data['jointNames'])))

        
        merged = polyUnite( dups )[0]
        
        delete( merged, ch=True )
        
        for dup in dups:
            if objExists(dup):
                delete(dup)
        
        apply( merged, weight_data )
        
        if not keepSource:
            delete(objs)
            
        return merged
        
    except Exception:
        print( traceback.format_exc() )
        warning('An error occurred trying to merge the skinned objects')
        if merged:
            delete(merged)
        if dups:
            delete(dups)
        raise


def weightChildren(leader=None):
    '''
    Take all the joints with poly children and weight them to their parent
    mimicing hard weighting.
    '''
    if not leader:
        leader = selected()[0]
    
    allMeshes = []
    
    for jnt in listRelatives(leader, ad=True, type='joint') + [leader]:
        polys = []
    
        children = jnt.listRelatives(type='transform')
        for child in children:
            if child.listRelatives(type='mesh'):
                polys.append( child )
        
        for poly in polys:
            weights = [ [[jnt.name(), 1.0]] ] * poly.vtx.count()
            set( poly, weights )
    
        allMeshes += polys
        
    mergePieces(allMeshes)
    
    
def findRelatedSkinCluster(skin):
    '''
    Mel's findRelatedSkinCluster that returns a PyNode.
    '''
    try:
        skin = mel.findRelatedSkinCluster( str(skin) )
        if skin:
            return PyNode(skin)
        else:
            return None
    except Exception:
        return None
        

def addMissingJoints(obj, joints):
    '''
    Adds the given joints to the mesh if they aren't already influencing without affecting the current skinning.
    '''
    boundJoints = skinCluster(obj, q=True, inf=True)

    missing = [PyNode(j) for j in joints if j not in boundJoints]

    skinCluster(obj, e=True, addInfluence=missing, weight=0)
    

def removeUnwantedInfluence(toRemove):
    
    skcluster = mel.findRelatedSkinCluster( selected()[0].node() )
    
    skinPercent( skcluster, tv=[(jnt, 0) for jnt in toRemove ] )


'''
def removeUnwantedInfluence(toRemove):
    # &&& Optionally provide a fallback list in case a vert is 100% bound to a bad joint.
    
    numRE = re.compile('(\d+)\]')

    # Pymel can be slow on lots of non-continugously selected verts, this will process 10k in 0.05s.
    indices = [int(numRE.search(vtx).group(1)) for vtx in cmds.ls(sl=True, fl=True)]
    
    mesh = selected()[0].node()
    data = get( mesh )
    altered = False
    for vtx in indices:
        valid = [ (jnt, val) for jnt, val in data['weights'][vtx] if jnt not in toRemove]
        if len(valid) != len(data['weights'][vtx]):
            
            if len(valid):
                total = sum( [val for jnt, val in valid] )
                part = total / len(valid)
                
                data['weights'][vtx] = [ (jnt, val + part) for jnt, val in valid ]
                altered = True
            else:
                print(vtx, ' had no other influences, not changing')
                
    if altered:
        apply(mesh, data, indices)
    else:
        print('Nothing was bound to those joints')
'''

def skeletonToJson(root):
    
    skel = {}
    
    for j in [root] + root.listRelatives(ad=True, type='joint'):
        parentName = j.getParent().shortName()
        
        skel[ j.shortName() ] = {
            'parent': parentName,
            'pos': cmds.xform(j.name(), q=True, ws=True, t=True),
            'jo': list(j.jointOrient.get())
        }
        
    return skel


def copySkinning():
    '''
    Wrapper for maya's copy that binds to the same joints if needed.
    Why this isn't the default behavior, I have no idea.
    '''
    src = selected()[0]
    targets = selected()[1:]

    joints = skinCluster(src, q=True, inf=True)

    skin = findRelatedSkinCluster(src)

    for dest in targets:
        if not findRelatedSkinCluster(dest):
            skinCluster(dest, joints, tsb=True, mi=skin.maxInfluences.get())

        select(src, dest)
        mel.eval('CopySkinWeights()')
        
        
def findBoundMeshes(joints):
    ''' Given a list of joints, returns a set of meshes that are bound to them.
    '''
    sk = listConnections(joints, type='skinCluster')
    
    return set(listConnections(sk, type='mesh'))
    
    
def parallelTransfer(sourceVerts, destVerts):
    ''' Copy the weights from the sourceVerts list directly to the destVerts.
    '''
    
    assert len(sourceVerts) == len(destVerts), 'List sizes do not match'
    
    src = get(sourceVerts[0].node())
    destMesh = destVerts[0].node()
    dest = get(destMesh)
    
    newJointIndex = { i: dest['jointNames'].index(name) for i, name in enumerate(src['jointNames']) if name in dest['jointNames'] }
    
    destIndices = [v.index() for v in destVerts]
    
    for srcVert, destIndex in zip(sourceVerts, destIndices):
        data = src['weights'][ srcVert.index() ]
        alteredData = [ (newJointIndex[i], w) for i, w in data]
        dest['weights'][ destIndex ] = alteredData
        
        
    apply( destMesh, dest, targetVerts=destIndices)