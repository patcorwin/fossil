
'''

Contains two systems for calling code that logs errors, `call` and `Callback`
if they occur.

Usage:
    # Decorate a function with alt.name (generally functions called via the shelf)
    @alt.name( 'Make Rocket' )
    def makeARocket():
        # A rocket is made
        pass

    # For Callbacks:
    window()
    columnLayout()
    button( l='Press me', c=alt.Callback( makeARocket ) )
    showWindow()

In either of the above cases, if an error occurs, it is automatically logged.
    
..  todo::
    Exclude specific users from logging errors via pdil.NO_ERROR_LIST
    
'''
from __future__ import print_function

import os

from pymel.core import menuItem

        
# This holds all the functions registered via `name`
if '_functions' not in globals():
    _functions = {}


# This holds the optional menu system
if '_menus' not in globals():
    _menus = {}


def buildMenus(topParent):
    global _functions
    global _menus
        
    menus = {}
    
    for niceName, menuPath in _menus.items():
        
        if menuPath not in menus:
            if not menuPath:
                menuPath = '(unlabeled)'
            parts = menuPath.split('|')
            paths = [ '|'.join(parts[:i + 1]) for i in range(len(parts)) ]
            
            parent = topParent
            
            for subPath, label in zip(paths, parts):
                if subPath not in menus:
                    newMenu = menuItem(l=label, p=parent, sm=True, to=True)
                    menus[subPath] = newMenu
                    parent = newMenu
        
        try:
            doc = _functions[niceName].__doc__
        except Exception:
            doc = ''
        
        menuItem(l=niceName, p=menus[menuPath], c=Callback(_functions[niceName]), ann=doc )
    


def name(niceName, menuPath=''):
    '''
    Decorate a function to give it a globally accessible name.  This allows
    shelves to refer to the global name while allowing the underlaying function
    to move around without having to change the shelf.
    '''
    def real_decorator(function):
        global _functions
        global _menus
        _functions[niceName] = function
        _menus[niceName] = menuPath
        return function

    return real_decorator


def call(niceName):
    '''
    Find a registered function.
    '''
    global _functions
    
    if niceName not in _functions:
        raise Exception( '{0} is not a registered function.'.format(niceName) )
        
    return _functions[niceName]


def nicePath(path):
    return os.path.normpath( os.path.normcase(path) )

    
class Callback(object):
    '''
    Wrapper for GUI callbacks to have nicer output when bugs happen
    '''

    def __init__(self, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def __call__(self, *args, **kwargs):
        res = self.func( *self.args, **self.kwargs )
        return res

    def __repr__(self):
        return "<Callback {0}>".format( self.func )
