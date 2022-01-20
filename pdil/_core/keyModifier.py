'''
Since Maya doesn't provide any way to detect modifier keys for most controls,
we can ask the OS directly.
'''

import ctypes


__all__ = ['shift', 'control']


VK_SHIFT    = 0x10 # http://msdn.microsoft.com/en-us/library/dd375731
VK_CONTROL  = 0x11


'''
ctypes.windll.user32.GetKeyState low bit is the toggle state, often useless and
the high bit is if it actually pressed so just check for val over 1 for actual
pressed state.
'''


def shift():
    '''
    Returns True if shift is pressed.
    '''
    return ctypes.windll.user32.GetKeyState( VK_SHIFT ) > 1

    
def control():
    '''
    Returns True if control is pressed.
    '''
    return ctypes.windll.user32.GetKeyState( VK_CONTROL ) > 1