'''
The thinking was other languages/setups could use other short and long words so
you edit `sides`
'''

# `left` and `right` are how everything is refered to internally, but if you
# want things build with other words/letters, do so here
sides = {
    'left': ('L', 'Left'),
    'right': ('R', 'Right')
}


letterToWord = { letter: word for (letter, word) in sides.values() }


def toWord(l):
    '''
    Given a letter, like 'R' returns 'Right'.
    '''
    global letterToWord
    return letterToWord[l]


def otherLetter(l):
    '''
    Given a letter, like 'R', returns the other one, ex: 'L'.
    '''
    global letterToWord

    letters = letterToWord.keys()

    return letters[0] if l == letters[1] else letters[1]


def otherWord(word):
    '''
    Given a word, like 'Right', returns the other one, ex: 'Left'.
    '''
    global letterToWord

    words = letterToWord.values()

    return words[0] if word == words[1] else words[1]