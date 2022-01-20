from contextlib import contextmanager

from pymel.core import currentTime, playbackOptions, timeControl, melGlobals

__all__ = [
    'selectedTime',
    'rangeIsSelected',
    'playbackRange',
    'getTimeInput',
    'preserveCurrentTime',
]


def selectedTime(dataType=float):
    '''
    Helper for getting a time range selection.
    '''
    return timeControl(melGlobals['gPlayBackSlider'], q=True, ra=True)


def rangeIsSelected():
    return timeControl(melGlobals['gPlayBackSlider'], q=True, rv=True)


def playbackRange():
    return playbackOptions(q=True, min=True), playbackOptions(q=True, max=True)


def getTimeInput(start, end):
    '''
    Unless given explicit input, tries to use a time selection, falling back to
    playback range.
    '''
    if start is not None and end is not None:
        return int(start), int(end)
    
    start, end = selectedTime()
    if rangeIsSelected():
        return int(start), int(end) - 1
    else:
        return playbackRange()
    

@contextmanager
def preserveCurrentTime():
    ''' Context Manager to reset the current frame at the end
    '''
    current = currentTime(q=True)
    try:
        yield
    except Exception:
        currentTime(current)
