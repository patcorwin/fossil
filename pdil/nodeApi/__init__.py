import pymel.internal.factories


def registerNodeType(classApi):
    '''
    Use instead of pymel.internal.factories.registerVirtualClass so classes
    are made easily accessibly to other modules.
    '''
    
    pymel.internal.factories.registerVirtualClass( classApi )
    
    globals()[classApi.__name__] = classApi