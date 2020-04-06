

import pdil.tool.fossil.main

a = pdil.tool.fossil.card.makeCard(jointCount=3, jointNames={'head': ['aa', 'bb', 'cc']})
x = pdil.tool.fossil.card.makeCard(jointCount=3, jointNames={'head': ['xx', 'yy', 'zz']})

assert not pdil.tool.fossil.main.RigTool.validateBoneNames([a, x])

data = a.rigData
data['nameInfo']['head'] = ['aa', 'bb', 'cc', 'xx']
a.rigData = data

assert not pdil.tool.fossil.main.RigTool.validateBoneNames([a, x]) # No issues because the xx is extra, therefore not build

data = a.rigData
data['nameInfo']['head'] = ['aa', 'bb', 'xx']
a.rigData = data

assert len(pdil.tool.fossil.main.RigTool.validateBoneNames([a, x])) == 1
assert  'overlap' in pdil.tool.fossil.main.RigTool.validateBoneNames([a, x])[0]

data = a.rigData
data['nameInfo']['head'] = ['aa', 'aa', 'xx']
a.rigData = data

assert len(pdil.tool.fossil.main.RigTool.validateBoneNames([a, x])) == 2
#assert  'overlap' in pdil.tool.fossil.main.RigTool.validateBoneNames([a, x])[0]

data = a.rigData
data['nameInfo']['head'] = ['aa', 'bb']
a.rigData = data

assert len(pdil.tool.fossil.main.RigTool.validateBoneNames([a, x])) == 1
assert  'enough' in pdil.tool.fossil.main.RigTool.validateBoneNames([a, x])[0]
