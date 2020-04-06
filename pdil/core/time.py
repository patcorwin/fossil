from pymel.core import *


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
    

class PreserveCurrentTime(object):
    '''
    Context Manager to reset the current frame at the end
    '''
    
    def __enter__(self):
        self.current = currentTime(q=True)
        
    def __exit__(self, type, value, traceback):
        currentTime(self.current)