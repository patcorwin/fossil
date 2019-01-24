'''
Provides an easy hook for appening menus to the dag right click menu.
'''
from __future__ import print_function, absolute_import

import os
import re

from pymel.core import mel, warning

from ..core import pubsub, version


def override_dagMenuProc():
    '''
    Builds `dagMenuProc.<maya version#>.mel` in this folder if it doesn't exist.
    
    '''
    overrideFilename = os.path.dirname(__file__).replace('\\', '/') + '/dagMenuProc.' + str(version()) + '.mel'
    
    if not os.path.exists(overrideFilename):

        filename = find_dagMenuProcMel()
        
        if not filename:
            warning( 'dagMenuProc.mel not found so unable to create custom override' )
            return
        else:
            print('Making dagMenuProc.mel override')

            with open(filename, 'r') as fid:
                lines = fid.readlines()
            
            newline = re.search('[\r\n]+$', lines[0]).group(0)
            
            for i, line in enumerate(lines):
                if '"m_dagMenuProc.kSelect"' in line:
                    lines[i:i] = ['''            python("try:pdil.melOverrides.dagMenuProc.customMenu('" + $object + "')\\nexcept:pass");''' + newline]
                    break
            
            with open(overrideFilename, 'w') as fid:
                fid.write( ''.join(lines) )
    
    print('Sourced override ' + overrideFilename)
    mel.source('dagMenuProc')
    mel.source(overrideFilename)
    

if '_menus' not in globals():
    _menus = {}


def registerMenu(menu):
    pubsub.subscribe('Custom_Dag_Menu', menu)


def customMenu(objectName):
    pubsub.publish('Custom_Dag_Menu', objectName)
        
    
def find_dagMenuProcMel():
    for path in os.environ['maya_script_path'].split(';'):
        for f in os.listdir(path):
            if f.lower() == 'dagmenuproc.mel':
                return path + '/' + f
    
    return ''


''' Excerpt from 2017 version, search for the >>>> uiRes call and insert a line above it
            // label the object
            string $shortName = `substitute ".*|" $object ""`;
            menuItem -label ($shortName + "...") -c ("showEditor "+$object);
            menuItem -divider true;
            menuItem -divider true;

            // Create the list of selection masks
            createSelectMenuItems($parent, $object);

            menuItem -d true;
        
>>>>        menuItem -label (uiRes("m_dagMenuProc.kSelect"))  -c ("select -r " + $object);
            menuItem -version "2014" -label (uiRes("m_dagMenuProc.kSelectAll"))  -c ("SelectAll");
            menuItem -version "2014" -label (uiRes("m_dagMenuProc.kDeselect"))  -c ("SelectNone;");
            menuItem -label (uiRes("m_dagMenuProc.kSelectHierarchy"))  -c ("select -hierarchy " + $object);
            menuItem -version "2014" -label (uiRes("m_dagMenuProc.kInverseSelection"))  -c ("InvertSelection");
            string $container = `container -q -fc $object`;
            if( $container != "" ){
'''