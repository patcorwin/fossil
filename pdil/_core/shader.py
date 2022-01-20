from collections import OrderedDict

import re

from pymel.core import cmds, delete, ls, nt, sets, shadingNode

from .._add import path

try:
    basestring
except NameError:
    basestring = str


__all__ = [
    'namedColors',
    'parseStr',
    'rgbToHsv',
    'hsvToRgb',
    'createShader',
    'listControlShaders',
    'similar',
    'findShaders',
    'assign',
    'getShaders',
    'compare',
    'consolidate',
]


namedColors = OrderedDict([
    ("pink",         (1,     0.5,  1)),     # noqa
    ("peach",        (1,     0.5,  0.5)),   # noqa
    ("red",          (1,     0,    0)),     # noqa
    ("darkred",      (0.6,   0,    0)),     # noqa
    
    ("black",        (0,     0,    0)),     # noqa
    ("lightorange",  (1,     0.7,  0.1)),   # noqa
    ("orange",       (1,     0.5,  0)),     # noqa
    ("darkorange",   (0.7,   0.25, 0)),     # noqa
    
    ("darkgrey",     (0.25,  0.25, 0.25)),  # noqa
    ("lightyellow",  (1,     1,    0.5)),   # noqa
    ("yellow",       (1,     1,    0)),     # noqa
    ("darkyellow",   (0.8,   0.8,  0)),     # noqa
    
    ("lightgrey",    (0.7,   0.7,  0.7)),   # noqa
    ("lightgreen",   (0.4,   1,    0.2)),   # noqa
    ("green",        (0,     1,    0)),     # noqa
    ("darkgreen",    (0,     0.5,  0)),     # noqa
    
    ("grey",         (0.5,   0.5,  0.5)),   # noqa
    ("lightblue",    (0.4,   0.55, 1)),     # noqa
    ("blue",         (0,     0,    1)),     # noqa
    ("darkblue",     (0,     0,    0.4)),   # noqa
    
    ("white",        (1,     1,    1)),     # noqa
    ("lightpurple",  (0.8,   0.5,  1)),     # noqa
    ("purple",       (0.7,   0,    1)),     # noqa
    ("darkpurple",   (0.375, 0,    0.5)),   # noqa
    
    ("lightbrown",   (0.76,  0.64, 0.5)),   # noqa
    ("brown",        (0.57,  0.49, 0.39)),  # noqa
    ("darkbrown",    (0.37,  0.28, 0.17)),  # noqa
])

digit = re.compile( r'\d*\.\d*' )


def parseStr(s):
    '''
    Given a string, possibly a named color, convert it to an rgb+opacity list.
    
    Can take RGB "0.2 0.5 0.7"
    Or a named color like "red .70" or "lightblue"
    '''
    
    color = s.lower().split()
    opacity = 1
    try:
        newColor = [ float(v) for v in color ]
    except Exception:
        newColor = list(namedColors[color[0]])
        if len(color) == 2:
            opacity = float(color[1])

    if len(newColor) == 3:
        newColor.append(opacity)
           
    return newColor


def rgbToHsv(r, g, b):
    '''
    Convert rgb (0-1) into hsv (0-360, 0-1, 0-1).
    src: http://www.cs.rit.edu/~ncs/color/t_convert.html
    '''
    minC = float(min( r, g, b ))
    maxC = float(max( r, g, b ))
    v = maxC
    delta = maxC - minC
    if delta:
        s = delta / float(maxC)
    else:
        # This is a greyscale color
        s = 0.0
        h = 0.0
        return h, s, v

    if r == maxC:
        h = ( g - b ) / delta # between yellow & magenta
    elif g == maxC:
        h = 2 + ( b - r ) / delta # between cyan & yellow
    else:
        h = 4 + ( r - g ) / delta # between magenta & cyan
        
    # Convert hue into positive degrees
    h *= 60
    while h < 0:
        h += 360
        
    return h, s, v


def hsvToRgb(h, s, v):
    '''
    Convert hsv (0-360, 0-1, 0-1) into rgb (0-1).
    src: http://www.cs.rit.edu/~ncs/color/t_convert.html
    '''

    if s == 0:
        # This is a greyscale color
        r = g = b = v
        return r, g, b

    h /= 60.0 # sector 0 to 5
    i = int( h )
    f = h - i # factorial part of h

    p = v * ( 1 - s )
    q = v * ( 1 - s * f )
    t = v * ( 1 - s * ( 1 - f ) )
    
    if i == 0:
        r = v
        g = t
        b = p
    elif i == 1:
        r = q
        g = v
        b = p
    elif i == 2:
        r = p
        g = v
        b = t
    elif i == 3:
        r = p
        g = q
        b = v
    elif i == 4:
        r = t
        g = p
        b = v
    else:
        r = v
        g = p
        b = q

    return r, g, b


def createShader(color, name=''):
    '''
    Creates a shader with the given color and opacity.
    :param rgb color:
    :param float opacity: 0.0 - 1.0, 1 is opaque
    '''

    opacity = 1.0
    if len(color) == 4:
        opacity = color[3]
    
    shader = shadingNode( 'surfaceShader', asShader=True )
    sg = sets(renderable=True, noSurfaceShader=True, empty=True)
    
    shader.outColor.set( color )
    shader.outTransparency.set( [1 - opacity] * 3 )

    shader.outColor >> sg.surfaceShader
    
    shader.addAttr( 'FossilControlShader', at='bool' )
    
    if not name:
        name = 'zz_ctrlShader'
        
        if opacity < 1:
            name += '_%i' % int(opacity * 100)
    
    shader.rename( name )
    
    return shader


def listControlShaders():
    '''
    Return all the special control shaders in the scene.
    '''
    return ls( '*.FossilControlShader', o=True )


def similar(aSrc, bSrc):
    '''
    Return True if two colors are similar.  Colors are rgb-opacity.  If opacity
    is not present, it's assumed to be 1.
    '''
    
    a = list(aSrc)
    b = list(bSrc)
    
    if len(a) == 3:
        a.append(1)
        
    if len(b) == 3:
        b.append(1)
    
    tolerance = 0.05
    if abs(a[0] - b[0] ) < tolerance \
        and abs(a[1] - b[1] ) < tolerance \
        and abs(a[2] - b[2] ) < tolerance \
        and abs(a[3] - b[3] ) < tolerance:  # noqa e125
        return True
    return False


def findShaders(color):
    '''
    Finds, if any, a shader with the given color and alpha
    
    :param rgb-o color: RGB tuple with optional opacity
    '''
    shaders = []
    for shader in listControlShaders():
        opacity = 1 - shader.outTransparency.get()[0]
        if similar(color, list(shader.outColor.get()) + [opacity]):
            shaders.append(shader)
    return shaders


def assign(obj, color):
    '''
    Assign a shader of the given color and opacity, reusing shaders when possible.
    '''
    global namedColors
    if isinstance( color, basestring ):
        color = parseStr(color)
    
    if len(color) == 3:
        color = list(color) + [1.0]
    
    shaders = findShaders(color)
    if not shaders:
        # No existing shader was found, so make it.
        shader = createShader(color)
        sg = shader.outColor.listConnections(type='shadingEngine')[0]
    else:
        # Matching shaders were found, find one that is valid.
        for shader in shaders:
            if shader.outColor.listConnections(type='shadingEngine'):
                sg = shader.outColor.listConnections(type='shadingEngine')[0]
                break
        # Or end up making one anyway.
        else:
            shader = createShader(color)
            sg = shader.outColor.listConnections(type='shadingEngine')[0]
    
    # cmds is much faster, but `sets` vs `pymel.core.sets` has different args (pymel made it saner but I need speed)
    cmds.sets( cmds.listRelatives(obj.name(), type='nurbsSurface', f=True), e=True, fe=sg.name() )
    
    
def getShaders(obj):
    '''
    Return all the shaders the given object uses.
    '''
    shaders = []
    for shadingEngine in set(obj.getShape().listConnections( type='shadingEngine')):
        con = shadingEngine.surfaceShader.listConnections()
        if con:
            shaders.append( con[0] )
    
    return shaders


def compare(a, b):
    '''
    Return True if the two shaders are of the same type and have the same color
    or texture.
    '''
    if type(a) != type(b):
        return False
    
    try:
        aColor = a.color.listConnections()
        bColor = b.color.listConnections()
    except Exception:
        aColor = a.outColor.listConnections()
        bColor = b.outColor.listConnections()
    
    if not aColor and not bColor:
        if a.color.get() == b.color.get():
            return True
        
    if aColor and bColor:
        if isinstance(aColor[0], nt.File) and isinstance(bColor[0], nt.File):
            if path.compare( aColor[0].fileTextureName.get(), bColor[0].fileTextureName.get() ):
                return True
    
    return False


def consolidate(reassign=True):
    '''
    If materials have the same color or use the same texture, merge them together.
    
    :param bool reassign:  If True (default), materials are actually merged and
        excess deleted.
    
    :return: List of names of the duplicate materials.
    
    '''
    
    shaders = [shadingEngine.surfaceShader.listConnections()[0] for shadingEngine in ls(type='shadingEngine') if shadingEngine.surfaceShader.listConnections()]
    shaders.sort()
    
    dups = []
    
    for outerIndex, a in enumerate(shaders[:-1]):

        for b in shaders[outerIndex + 1: len(shaders)]:
            if a == b or b in dups:
                continue
            
            if compare(a, b):
                if reassign:
                    aSE = a.listConnections(type='shadingEngine')
                    bSE = b.listConnections(type='shadingEngine')
                    if aSE and bSE:
                        for member in bSE[0].members():
                            sets(aSE[0], edit=True, fe=member)
                
                dups.append(b)

    dupNames = [dup.name() for dup in dups]

    if reassign:
        for dup in dups:
            delete(dup)
            
    return dupNames