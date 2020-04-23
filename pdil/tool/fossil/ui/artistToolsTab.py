from __future__ import absolute_import, division, print_function

from pymel.core import shelfButton, shelfLayout, tabLayout


def toolShelf():

    tab = tabLayout()
    shelfLayout('Tools - Copy these freely into your shelf, they will get remade when fossil is opened')
    
    shelfButton(image1='zeropose.png',
                annotation='Zero Controllers',
                command="import pdil.tool.fossil.userTools;pdil.core.alt.call('Zero Controllers')()")
    
    shelfButton(image1='skeletonTool.png',
                annotation='Open Fossil',
                command="import pdil.tool.fossil.main;pdil.core.alt.call('Rig Tool')()")
    
    shelfButton(image1='selectAllControls.png',
                annotation='Select All Controllers',
                command="import pdil.tool.fossil.userTools;pdil.core.alt.call('Select All Controllers')()")
    
    shelfButton(image1='quickHideControls.png',
                annotation='Similar to "Isolated Selected" but just for rig controls',
                command="import pdil.tool.rigControls;pdil.core.alt.call('Quick Hide Controls')()")
    
    return tab