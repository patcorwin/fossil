from __future__ import print_function, absolute_import


from ..add import simpleName

# &&& Probably move this to dagObj, or delete altogether (verify no other project is using it first!)
def childByName(parent, childName):
    for child in parent.listRelatives():
        if simpleName(child) == childName:
            return child
    
    return None
    
