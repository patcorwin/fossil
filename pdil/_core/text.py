import base64
import zlib

from ..vendor.Qt import QtGui

__all__ = ['writeInBox', 'asciiCompress', 'asciiDecompress', 'clipboard']

try:
    base64_decodebytes = base64.decodebytes
except AttributeError:
    base64_decodebytes = base64.decodestring # decodestring is a deprecated alias in 3.1


def writeInBox(msg):
    '''
    Given a message, returns a string with that message in an ascii box.
    '''
    largest = max( msg.splitlines(), key=len )

    largest = len(largest)

    newMsg = []
    for line in msg.splitlines():
        newMsg.append( '| {0:<{1}} |'.format(line, largest) )
        
    return ' ' + '_' * (largest + 2) + '\n/' + ' ' * (largest + 2) + '\\\n' + \
            '\n'.join(newMsg) + '\n' + '\\' + '_' * (largest + 2) + '/'


def asciiCompress(data, level=9):
    '''
    Compress data to printable ascii-code since Maya only stores ascii strings.
    From http://code.activestate.com/recipes/355486-compress-data-to-printable-ascii-data/
    '''
    try:
        code = zlib.compress(data, level)
    except TypeError: # python 3 compatibility, most sources will probably be strings
        code = zlib.compress(data.encode(), level)
    
    try:
        code = base64.encodestring(code)
    except:
        code = base64.encodebytes(code)
    return code


def asciiDecompress(code):
    '''
    Decompress result of asciiCompress
    From http://code.activestate.com/recipes/355486-compress-data-to-printable-ascii-data/
    '''
    try:
        code = base64_decodebytes(code)
    except TypeError: # python 3 compatibility, most sources will probably be strings
        code = base64_decodebytes(code.encode())
        
    data = zlib.decompress(code)
    return data


class clipboard(object):
    '''
    Originally only the windows clipboard was supported from help of
    From http://stackoverflow.com/questions/579687/how-do-i-copy-a-string-to-the-clipboard-on-windows-using-python
    but that stopped working in 2016 (maybe earlier) so just use Qt for compatibility, and since it works.
    '''
    
    @classmethod
    def get(cls):
        return QtGui.QClipboard().text()

    @classmethod
    def set(cls, data ):
        QtGui.QClipboard().setText(data)
