'''
The thinking was other languages/setups could use other short and long words so
you edit `sides`
'''

import pdil

#from ...vendor.enum import Enum # When maya get python 3, the stdlib can replace this.

# Joints are optionally prefixed with this string.  This can be helpful to avoid
# name collisions with other objects.
#prefix = '' &&& Test that this has been totally replaced by _settings['joint_prefix']


''' &&&
I *think* it should be:

side_suffix
side_name

And such conversions should match.

I should probably make the suffix include the underscore instead of making it automatic.


!!! mirrorCode should store a stable internal string, aka left/right!

I also think I want to prefix things that dig into json with meta_* so it's easier to
trace out the code.  I super dig this idea right now.


'''

# `left` and `right` are how everything is refered to internally, but if you
# want things build with other words/letters, do so here
"""sides = {
    'left': ('l', 'Left'),
    'right': ('r', 'Right')
}"""

FOSSIL_CTRL_TYPE = 'fossilCtrlType'

FOSSIL_MAIN_CONTROL = 'fossilMainControl'


_settings = pdil.ui.Settings( 'Skeleton Tool Settings',
    {
        'joint_left':  'L',
        'joint_right': 'R',
        
        'control_left':  'L',
        'control_right': 'R',
        
        'root_name': 'root',
        'joint_prefix': '',
    }
)


JOINT_SIDE_CODE_MAP = {
    'left': _settings['joint_left'],
    'right': _settings['joint_right'],
    '': '',
}

CONTROL_SIDE_CODE_MAP = {
    'left': _settings['control_left'],
    'right': _settings['control_right'],
    '': '',
    None: '',
}

#letterToWord = { letter: word for (letter, word) in sides.values() }

"""
def toWord(l):
    '''
    Given a letter, like 'R' returns 'Right'.
    '''
    global letterToWord
    return letterToWord[l]"""

"""# DEPRECATED ME
def otherLetter(l):
    '''
    Given a letter, like 'R', returns the other one, ex: 'L'.
    '''
    global letterToWord

    letters = letterToWord.keys()

    return letters[0] if l == letters[1] else letters[1]
"""

"""
# DEPRECATED ME
def otherWord(word):
    '''
    Given a word, like 'Right', returns the other one, ex: 'Left'.
    '''
    global letterToWord

    words = letterToWord.values()

    return words[0] if word == words[1] else words[1]
"""
    

def otherSideCode(name):
    return 'right' if name == 'left' else 'left'
    

def jointSideSuffix(code):
    ''' Accetps the strings 'left' and 'right'. '''

    return '_' + JOINT_SIDE_CODE_MAP[code]
    
    
def controlSideSuffix(code):
    ''' Accetps the strings 'left' and 'right'. '''

    return '_' + CONTROL_SIDE_CODE_MAP[code]