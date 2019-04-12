'''
The thinking was other languages/setups could use other short and long words so
you edit `sides`
'''

#from ...vendor.enum import Enum # When maya get python 3, the stdlib can replace this.

# Joints are optionally prefixed with this string.  This can be helpful to avoid
# name collisions with other objects.
prefix = ''


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


SIDE_CODE_MAP = {
    'left':  'l',
    'right': 'r',
    '': '',
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
    

def sideSuffix(code):
    ''' Accetps the strings 'left' and 'right'. '''

    return '_' + SIDE_CODE_MAP[code]