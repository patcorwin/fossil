from collections import OrderedDict
from pymel.core import mel, surface, xform


_form = {
    0: 'open',
    1: 'closed',
    2: 'periodic',
}


def getNurbsShapeCache(shape):
    ''' Returns a dict to reconstruct a nurbs shape, via the 'cache' attr described by the docs (2022):
    
    From docs:
        Cached surface Defines geometry of the surface. The properties are defined in this order:
        First line: degree in U, degree in V, form in U, form in V, rational (yes/no)
        Second line: number of knots in U, list of knot values in U
        Third line: number of knots in V, list of knot values in V
        Fourth line: number of CVs
        Fifth and later lines: CV positions in x,y,z (and w if rational)
    
    The additional attrs are saved but appear to be the default so igore for now.
    setAttr -k off ".v";        Not sure why shape note vis is specifically set unkeyable
    setAttr ".vir" yes;         visible in reflection (probably just set false)
    setAttr ".vif" yes;         visible in reflection (probably just set false)
    setAttr ".covm[0]"  0 1 1;  collision, just set
    setAttr ".cdvm[0]"  0 1 1;  collision, just set
    setAttr ".dvu" 0;           Division, appears to be fine at default
    setAttr ".dvv" 0;           Division, appears to be fine at default
    setAttr ".cpr" 4;           curve percision appears to be fine at default
    setAttr ".cps" 4;           curve percision appears to be fine at default
    '''
    
    data = {
        'degU': shape.du.get(),
        'degV': shape.dv.get(),
        'formU': shape.fu.get(),
        'formV': shape.fv.get(),

        'knotsU': shape.getKnotsInU(),
        'knotsV': shape.getKnotsInV(),
        'cvU': shape.numCVsInU(False),
        'cvV': shape.numCVsInV(False),
        'rational': 'no'
    }

    data['cvs'] = [shape.getCV(u, v, space='world') for u in range(data['cvU']) for v in range(data['cvV'])]
    
    return data


def setNurbsShapeCache(shape, data):
    ''' Applies the data from `getNurbsShapeCache` to the given shape node.
    '''
    text = ['{0[degU]} {0[degV]} {0[formU]} {0[formV]} {0[rational]}'.format(data)]
    text.append( str(len(data['knotsU'])) + ' ' + ' '.join( str(k) for k in data['knotsU']) )
    text.append( str(len(data['knotsV'])) + ' ' + ' '.join( str(k) for k in data['knotsV']) )
    text.append( str(data['cvU'] * data['cvV']) )
    text += [ '{0.x} {0.y} {0.z}'.format(cv) for cv in data['cvs'] ]
    
    mel.eval('setAttr {}.cc -type "nurbsSurface" \n{}'.format(shape, '\n'.join(text)))


def generateShapeCode(objs):
    surfaces = []
    curves = []

    data = []

    for obj in objs:
        if obj.getShape().type() == 'nurbsSurface':
            surfaces.append(obj)
        if obj.getShape().type() == 'curve':
            curves.append(obj)

    for surf in surfaces:
        data.append(getNurbsShapeCache(surf))

    # Get the bounding box
    # scale all the values to a unit

    # Screenshot

    return data


def serializeNurbs(obj):
    info = OrderedDict()
    info['version'] = '1.0.0'

    shape = obj.getShape()

    if shape.type() == 'nurbsSurface':
        info['type'] = 'surface'
        info['spansUV'] = shape.spansUV.get()
        info['degreeUV'] = shape.degreeUV.get()
        info['formU'] = shape.formU.get()
        info['formV'] = shape.formV.get()
        info['minMaxRangeU'] = shape.minMaxRangeU.get()
        info['minMaxRangeV'] = shape.minMaxRangeV.get()
        info['knotsU'] = shape.getKnotsInU()
        info['knotsV'] = shape.getKnotsInV()
        info['points'] = [xform(cv, q=True, ws=True, t=True) for cv in shape.cv]

    return info



def deserializeNurbs(info):
    if info['type'] == 'surface':
        return surface(
            ku=info['knotsU'],
            kv=info['knotsV'],
            du=info['degreeUV'][0],
            dv=info['degreeUV'][1],
            fu=_form[info['formU']],
            fv=_form[info['formV']],
            p=info['points']
        ).getParent()
