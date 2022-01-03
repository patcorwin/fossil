import json

from pymel.core import confirmDialog, menu, menuBarLayout, objExists, PyNode, selected

from .. import _core as core
from .._add import alt

_WEIGHTS = {}


@alt.name('Save Weights Locally', 'Weights')
def saveWeightsLocally():
    ''' Save the weights on the selected objects in a global var for use in this maya session.
    '''
    global _WEIGHTS
    _WEIGHTS.clear()
    
    for obj in selected():
        _WEIGHTS[obj.name()] = core.weights.get(obj)
        

@alt.name('Load Weights Locally', 'Weights')
def loadWeightsLocally():
    ''' Loads the weights in this session, applying to the same objects or the selection.
    
    Useful in case the namespaces changed.
    '''
    global _WEIGHTS
    multiLoadWeights( _WEIGHTS )


@alt.name('Save Weights To Clipboard', 'Weights')
def saveWeightsToClipboard():
    ''' Save weights as json to text clipboard
    '''
    core.text.clipboard.set(
        json.dumps(
            {obj.name(): core.weights.get(obj) for obj in selected() }
        )
    )


@alt.name('Load Weights From Clipboard', 'Weights')
def loadWeightsFromClipboard():
    ''' Loads the weights from json in the clipboard on the same objects or the selection.
    
    Useful in case the namespaces changed.
    '''
    multiLoadWeights( json.loads( core.text.clipboard.get() ) )


def multiLoadWeights(data):
    ''' Takes dict of {obj:weight_info}, applies by name, or to selection.
    '''
    allObjsExist = True
    for name in data:
        if not objExists(name):
            allObjsExist = False
            break
    
    if allObjsExist:
        for obj, vals in data.items():
            core.weights.apply(PyNode(obj), vals)
            
    elif len(data) == len(selected()):
        msg = 'Target objects do not exist, apply in this order?\n'
        
        for selObj, name in zip(selected(), data):
            msg += name + ' -> ' + selObj.name()
        
        res = confirmDialog(m=msg, b=['Yes', 'No'])
        
        if res == 'Yes':
            for selObj, (obj, data) in zip(selected(), data.items()):
                core.weights.apply(selObj, data)
        
        
def toolsWindow():
    
    with core.ui.singleWindow('Various Tools'):
        menuBarLayout()
        a = menu()
        alt.buildMenus(a)