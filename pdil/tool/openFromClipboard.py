from ..vendor.Qt import QtGui


from pymel.core import mel, openFile, Path


def openFromClipboard():
    
    filepath = Path(QtGui.QClipboard().text().strip())
    
    if filepath.exists():
        if filepath.ext.lower() == '.mb':
            fileType = 'mayaBinary'
        if filepath.ext.lower() == '.ma':
            fileType = 'mayaAscii'
        
        mel.addRecentFile(filepath.cannonicalPath(), fileType)
    
        openFile( filename, f=True )