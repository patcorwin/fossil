
from pymel.core import newFile

from pdil.tool.fossil import card, main


def test_validateBoneNames():

    newFile(f=True)

    a = card.makeCard(jointCount=3, jointNames={'head': ['aa', 'bb', 'cc']})
    x = card.makeCard(jointCount=3, jointNames={'head': ['xx', 'yy', 'zz']})

    assert not main.RigTool.validateBoneNames([a, x])

    data = a.rigData
    data['nameInfo']['head'] = ['aa', 'bb', 'cc', 'xx']
    a.rigData = data

    assert not main.RigTool.validateBoneNames([a, x]) # No issues because the xx is extra, therefore not build

    data = a.rigData
    data['nameInfo']['head'] = ['aa', 'bb', 'xx']
    a.rigData = data

    assert len(main.RigTool.validateBoneNames([a, x])) == 1
    assert 'overlap' in main.RigTool.validateBoneNames([a, x])[0]

    data = a.rigData
    data['nameInfo']['head'] = ['aa', 'aa', 'xx']
    a.rigData = data

    assert len(main.RigTool.validateBoneNames([a, x])) == 2
    #assert  'overlap' in main.RigTool.validateBoneNames([a, x])[0]

    data = a.rigData
    data['nameInfo']['head'] = ['aa', 'bb']
    a.rigData = data

    assert len(main.RigTool.validateBoneNames([a, x])) == 1
    assert 'enough' in main.RigTool.validateBoneNames([a, x])[0]
