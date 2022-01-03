# Python 3 only

from pathlib import Path

from pymel.core import confirmDialog, newFile, select

import pdil
from pdil.core.image import grab, grabTree, grabTable

from . import card, main


def trim(img, pct):
    return img.copy(0, 0, img.rect().width(), int(img.rect().height() * pct))


def saveImages(images):
    for dest, img in images:
        print('saving', dest)
        img.save(dest)


def setup():

    if confirmDialog(m='New scene?', b=['Yes', 'No']) != 'Yes':
        return

    newFile(f=True)

    #from pdil.tool.fossil import main
    spine = card.makeCard(jointCount=5, jointNames={'repeat': 'Spine', 'head': ['Pelvis'], 'tail': ['Head']} )
    spine.joints[0].orientTarget = '-world-'
    leg = card.makeCard(jointCount=3, jointNames={'head': ['Hip', 'Knee', 'Ankle']} )
    leg.mirror = ''
    with leg.rigData as rigData:
        rigData['mirrorCode'] = 'left'
    leg.joints[0].setBPParent( spine.joints[0] )

    foot = card.makeCard(jointCount=2, jointNames={'head': ['Ball', 'Toe']} )
    foot.joints[0].setBPParent( leg.joints[-1] )
    footAim = card.makeCard(jointCount=1, jointNames={'head': ['target']})
    footAim.joints[0].helper = True
    leg.joints[2].orientTarget = footAim.joints[0]

    with leg.rigData as rigData:
        rigData['rigCmd'] = 'IkChain'

    with spine.rigData as rigData:
        rigData['rigCmd'] = 'TranslateChain'

    select(None)
    return leg


def generateScreenshots():
    leg = setup()
    win = main.RigTool()
    win.setGeometry(10, 40, 1300, 880) # Need to have a consistent size for consistent screenshots
    
    for i in range(5):
        win.ui.tabWidget.setCurrentIndex(i)

    root = Path(__file__).parent.parent.parent.parent.joinpath('docs')

    images = [
        [f'{root}/start_tab.png', trim( grab(win.ui.tab), .4 )],
        [f'{root}/add_chain.png', grab(win.ui.gridLayout, highlight=[win.ui.cardJointNames, win.ui.jointCount, win.ui.makeCardBtn])],
        [f'{root}/cardLister_joint_naming.png', trim(grabTree(win.ui.cardLister, [3, 5]), .4)],
        [f'{root}/cardLister_side.png', trim( grabTree(win.ui.cardLister, [6, 7]), .4 )],
    ]


    select(leg)
    win.ui.jointLister.jointListerRefresh(leg)
    win.forceCardParams()
    images += [
        [f'{root}/jointLister_parent.png', trim( grabTable(win.ui.jointLister, [5]), .5)],
        [f'{root}/jointLister_orient.png', trim( grabTable(win.ui.jointLister, [4]), .5)],
    ]

    # Rigging
    # Leg still selected
    images += [
        [f'{root}/set_rig_type.png', trim(grabTree(win.ui.cardLister, [2]), .5)],
        [f'{root}/rig_options.png', grab(win.ui.widget_7)],
        [f'{root}/space_core.png', grab(win.ui.spaceQuickButtons, [win.spaceTab.buttons[1], win.spaceTab.buttons[7]] )],
        [f'{root}/space_convenience.png', grab(win.ui.spaceQuickButtons, [win.spaceTab.buttons[9], win.spaceTab.buttons[12]])],
        [f'{root}/build_rig_button.png', grab(win.ui.gridLayout, [win.ui.buildRigBtn])],
        [f'{root}/controller_shapes', grab(win.ui.shape_chooser)],
        [f'{root}/shape_clipboard.png', grab(win.ui.gridLayout_3, [win.ui.label_14, win.ui.pasteWorldBtn])],
        [f'{root}/controller_colors.png', grab(win.ui.verticalLayout_15)],
        [f'{root}/save_mods.png', grab(win.ui.gridLayout, [win.ui.saveModsBtn])],
    ]

    saveImages(images)
    return win # Just to make it easier to iterate