from __future__ import absolute_import, division, print_function

from pymel.core import shelfButton, shelfLayout, tabLayout


def toolShelf():

    tab = tabLayout()
    shelfLayout('Tools')
    
    shelfButton(image1='zeropose.png',
                annotation='Zero Controllers',
                command="import pdil.tool.fossil.userTools;core.alt.call('Zero Controllers')()")
    
    shelfButton(image1='skeletonTool.png',
                annotation='Open Fossil',
                command="import pdil.tool.fossil.main;pdil.core.alt.call('Rig Tool')()")
    
    shelfButton(image1='selectAllControls.png',
                annotation='Select All Controllers',
                command="import pdil.tool.fossil.userTools;pdil.core.alt.call('Select All Controllers')()")
    
    shelfButton(image1='switch.png',
                annotation='Ik/Fk Switch GUI',
                command="import pdil.tool.animSwitcherGui;pdil.core.alt.call('Anim Switch GUI')()")
    
    return tab