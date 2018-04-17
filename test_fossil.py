'''
Not elaborate tests, but having some is better than nothing.
'''


from pymel.core import select, objExists, listRelatives, PyNode

from pdil import core

from pdil.tool.fossil import card
from pdil.tool.fossil import main



def test_basicBiped():
    
    #gui = main.RigTool()
    
    # Make the default biped
    card.bipedSetup(spineCount=5)
    
    # Make all the bones and test their existence
    select(core.findNode.allCards())
    main.RigTool.buildBones()
    
    for j in jointsToMake:
        assert objExists(j), 'Joint ' + j + ' was not made'
    
    root = core.findNode.getRoot()
    
    assert len(listRelatives(root, ad=True, type='joint')) == (len(jointsToMake) - 1), 'Too many bones were made'
    
    # Build the rig
    spine = PyNode('Spine_card')
    rigData = spine.rigData
    rigData['rigCmd'] = 'SplineChest'
    spine.rigData = rigData
    
    select(core.findNode.allCards())
    main.RigTool.buildRig()
    
    
jointsToMake = [
    '|b_root',
    '|b_root|b_Pelvis',
    '|b_root|b_Pelvis|b_Hips',
    '|b_root|b_Pelvis|b_Hips|b_Hip_L',
    '|b_root|b_Pelvis|b_Hips|b_Hip_L|b_Knee_L',
    '|b_root|b_Pelvis|b_Hips|b_Hip_L|b_Knee_L|b_Ankle_L',
    '|b_root|b_Pelvis|b_Hips|b_Hip_L|b_Knee_L|b_Ankle_L|b_Ball_L',
    '|b_root|b_Pelvis|b_Hips|b_Hip_L|b_Knee_L|b_Ankle_L|b_Ball_L|b_Toe_L',
    '|b_root|b_Pelvis|b_Hips|b_Hip_R',
    '|b_root|b_Pelvis|b_Hips|b_Hip_R|b_Knee_R',
    '|b_root|b_Pelvis|b_Hips|b_Hip_R|b_Knee_R|b_Ankle_R',
    '|b_root|b_Pelvis|b_Hips|b_Hip_R|b_Knee_R|b_Ankle_R|b_Ball_R',
    '|b_root|b_Pelvis|b_Hips|b_Hip_R|b_Knee_R|b_Ankle_R|b_Ball_R|b_Toe_R',
    '|b_root|b_Pelvis|b_Spine01',
    '|b_root|b_Pelvis|b_Spine01|b_Spine02',
    '|b_root|b_Pelvis|b_Spine01|b_Spine02|b_Spine03',
    '|b_root|b_Pelvis|b_Spine01|b_Spine02|b_Spine03|b_Spine04',
    '|b_root|b_Pelvis|b_Spine01|b_Spine02|b_Spine03|b_Spine04|b_Spine05',
    '|b_root|b_Pelvis|b_Spine01|b_Spine02|b_Spine03|b_Spine04|b_Spine05|b_Clavicle_L',
    '|b_root|b_Pelvis|b_Spine01|b_Spine02|b_Spine03|b_Spine04|b_Spine05|b_Clavicle_L|b_Shoulder_L',
    '|b_root|b_Pelvis|b_Spine01|b_Spine02|b_Spine03|b_Spine04|b_Spine05|b_Clavicle_L|b_Shoulder_L|b_Elbow_L',
    '|b_root|b_Pelvis|b_Spine01|b_Spine02|b_Spine03|b_Spine04|b_Spine05|b_Clavicle_L|b_Shoulder_L|b_Elbow_L|b_Wrist_L',
    '|b_root|b_Pelvis|b_Spine01|b_Spine02|b_Spine03|b_Spine04|b_Spine05|b_Clavicle_L|b_Shoulder_L|b_Elbow_L|b_Wrist_L|b_Index01_L',
    '|b_root|b_Pelvis|b_Spine01|b_Spine02|b_Spine03|b_Spine04|b_Spine05|b_Clavicle_L|b_Shoulder_L|b_Elbow_L|b_Wrist_L|b_Index01_L|b_Index02_L',
    '|b_root|b_Pelvis|b_Spine01|b_Spine02|b_Spine03|b_Spine04|b_Spine05|b_Clavicle_L|b_Shoulder_L|b_Elbow_L|b_Wrist_L|b_Index01_L|b_Index02_L|b_Index03_L',
    '|b_root|b_Pelvis|b_Spine01|b_Spine02|b_Spine03|b_Spine04|b_Spine05|b_Clavicle_L|b_Shoulder_L|b_Elbow_L|b_Wrist_L|b_Middle01_L',
    '|b_root|b_Pelvis|b_Spine01|b_Spine02|b_Spine03|b_Spine04|b_Spine05|b_Clavicle_L|b_Shoulder_L|b_Elbow_L|b_Wrist_L|b_Middle01_L|b_Middle02_L',
    '|b_root|b_Pelvis|b_Spine01|b_Spine02|b_Spine03|b_Spine04|b_Spine05|b_Clavicle_L|b_Shoulder_L|b_Elbow_L|b_Wrist_L|b_Middle01_L|b_Middle02_L|b_Middle03_L',
    '|b_root|b_Pelvis|b_Spine01|b_Spine02|b_Spine03|b_Spine04|b_Spine05|b_Clavicle_L|b_Shoulder_L|b_Elbow_L|b_Wrist_L|b_Ring01_L',
    '|b_root|b_Pelvis|b_Spine01|b_Spine02|b_Spine03|b_Spine04|b_Spine05|b_Clavicle_L|b_Shoulder_L|b_Elbow_L|b_Wrist_L|b_Ring01_L|b_Ring02_L',
    '|b_root|b_Pelvis|b_Spine01|b_Spine02|b_Spine03|b_Spine04|b_Spine05|b_Clavicle_L|b_Shoulder_L|b_Elbow_L|b_Wrist_L|b_Ring01_L|b_Ring02_L|b_Ring03_L',
    '|b_root|b_Pelvis|b_Spine01|b_Spine02|b_Spine03|b_Spine04|b_Spine05|b_Clavicle_L|b_Shoulder_L|b_Elbow_L|b_Wrist_L|b_Pinky01_L',
    '|b_root|b_Pelvis|b_Spine01|b_Spine02|b_Spine03|b_Spine04|b_Spine05|b_Clavicle_L|b_Shoulder_L|b_Elbow_L|b_Wrist_L|b_Pinky01_L|b_Pinky02_L',
    '|b_root|b_Pelvis|b_Spine01|b_Spine02|b_Spine03|b_Spine04|b_Spine05|b_Clavicle_L|b_Shoulder_L|b_Elbow_L|b_Wrist_L|b_Pinky01_L|b_Pinky02_L|b_Pinky03_L',
    '|b_root|b_Pelvis|b_Spine01|b_Spine02|b_Spine03|b_Spine04|b_Spine05|b_Clavicle_L|b_Shoulder_L|b_Elbow_L|b_Wrist_L|b_Thumb01_L',
    '|b_root|b_Pelvis|b_Spine01|b_Spine02|b_Spine03|b_Spine04|b_Spine05|b_Clavicle_L|b_Shoulder_L|b_Elbow_L|b_Wrist_L|b_Thumb01_L|b_Thumb02_L',
    '|b_root|b_Pelvis|b_Spine01|b_Spine02|b_Spine03|b_Spine04|b_Spine05|b_Clavicle_L|b_Shoulder_L|b_Elbow_L|b_Wrist_L|b_Thumb01_L|b_Thumb02_L|b_Thumb03_L',
    '|b_root|b_Pelvis|b_Spine01|b_Spine02|b_Spine03|b_Spine04|b_Spine05|b_Clavicle_R',
    '|b_root|b_Pelvis|b_Spine01|b_Spine02|b_Spine03|b_Spine04|b_Spine05|b_Clavicle_R|b_Shoulder_R',
    '|b_root|b_Pelvis|b_Spine01|b_Spine02|b_Spine03|b_Spine04|b_Spine05|b_Clavicle_R|b_Shoulder_R|b_Elbow_R',
    '|b_root|b_Pelvis|b_Spine01|b_Spine02|b_Spine03|b_Spine04|b_Spine05|b_Clavicle_R|b_Shoulder_R|b_Elbow_R|b_Wrist_R',
    '|b_root|b_Pelvis|b_Spine01|b_Spine02|b_Spine03|b_Spine04|b_Spine05|b_Clavicle_R|b_Shoulder_R|b_Elbow_R|b_Wrist_R|b_Index01_R',
    '|b_root|b_Pelvis|b_Spine01|b_Spine02|b_Spine03|b_Spine04|b_Spine05|b_Clavicle_R|b_Shoulder_R|b_Elbow_R|b_Wrist_R|b_Index01_R|b_Index02_R',
    '|b_root|b_Pelvis|b_Spine01|b_Spine02|b_Spine03|b_Spine04|b_Spine05|b_Clavicle_R|b_Shoulder_R|b_Elbow_R|b_Wrist_R|b_Index01_R|b_Index02_R|b_Index03_R',
    '|b_root|b_Pelvis|b_Spine01|b_Spine02|b_Spine03|b_Spine04|b_Spine05|b_Clavicle_R|b_Shoulder_R|b_Elbow_R|b_Wrist_R|b_Middle01_R',
    '|b_root|b_Pelvis|b_Spine01|b_Spine02|b_Spine03|b_Spine04|b_Spine05|b_Clavicle_R|b_Shoulder_R|b_Elbow_R|b_Wrist_R|b_Middle01_R|b_Middle02_R',
    '|b_root|b_Pelvis|b_Spine01|b_Spine02|b_Spine03|b_Spine04|b_Spine05|b_Clavicle_R|b_Shoulder_R|b_Elbow_R|b_Wrist_R|b_Middle01_R|b_Middle02_R|b_Middle03_R',
    '|b_root|b_Pelvis|b_Spine01|b_Spine02|b_Spine03|b_Spine04|b_Spine05|b_Clavicle_R|b_Shoulder_R|b_Elbow_R|b_Wrist_R|b_Ring01_R',
    '|b_root|b_Pelvis|b_Spine01|b_Spine02|b_Spine03|b_Spine04|b_Spine05|b_Clavicle_R|b_Shoulder_R|b_Elbow_R|b_Wrist_R|b_Ring01_R|b_Ring02_R',
    '|b_root|b_Pelvis|b_Spine01|b_Spine02|b_Spine03|b_Spine04|b_Spine05|b_Clavicle_R|b_Shoulder_R|b_Elbow_R|b_Wrist_R|b_Ring01_R|b_Ring02_R|b_Ring03_R',
    '|b_root|b_Pelvis|b_Spine01|b_Spine02|b_Spine03|b_Spine04|b_Spine05|b_Clavicle_R|b_Shoulder_R|b_Elbow_R|b_Wrist_R|b_Pinky01_R',
    '|b_root|b_Pelvis|b_Spine01|b_Spine02|b_Spine03|b_Spine04|b_Spine05|b_Clavicle_R|b_Shoulder_R|b_Elbow_R|b_Wrist_R|b_Pinky01_R|b_Pinky02_R',
    '|b_root|b_Pelvis|b_Spine01|b_Spine02|b_Spine03|b_Spine04|b_Spine05|b_Clavicle_R|b_Shoulder_R|b_Elbow_R|b_Wrist_R|b_Pinky01_R|b_Pinky02_R|b_Pinky03_R',
    '|b_root|b_Pelvis|b_Spine01|b_Spine02|b_Spine03|b_Spine04|b_Spine05|b_Clavicle_R|b_Shoulder_R|b_Elbow_R|b_Wrist_R|b_Thumb01_R',
    '|b_root|b_Pelvis|b_Spine01|b_Spine02|b_Spine03|b_Spine04|b_Spine05|b_Clavicle_R|b_Shoulder_R|b_Elbow_R|b_Wrist_R|b_Thumb01_R|b_Thumb02_R',
    '|b_root|b_Pelvis|b_Spine01|b_Spine02|b_Spine03|b_Spine04|b_Spine05|b_Clavicle_R|b_Shoulder_R|b_Elbow_R|b_Wrist_R|b_Thumb01_R|b_Thumb02_R|b_Thumb03_R',
    '|b_root|b_Pelvis|b_Spine01|b_Spine02|b_Spine03|b_Spine04|b_Spine05|b_Neck01',
    '|b_root|b_Pelvis|b_Spine01|b_Spine02|b_Spine03|b_Spine04|b_Spine05|b_Neck01|b_Head',
]