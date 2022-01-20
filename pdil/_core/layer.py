from pymel.core import ls, createDisplayLayer


__all__ = ['putInLayer']


def putInLayer(objs, layerName):
    '''
    Puts the given objects in a layer of the given name.
    
    todo::
        There needs to be a fallback if the layer isn't found to verify another
        dag obj doesn't have the intended name.
    '''
    
    for layer in ls(type='displayLayer'):
        if layer.name() == layerName:
            break
    else:
        layer = createDisplayLayer(name=layerName, e=True)
        
    layer.addMembers(objs)