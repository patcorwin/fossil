from __future__ import print_function, absolute_import

import os
import tempfile


def normalize(p): # type: (str) -> str
    ''' Returns absolute path with forward slash, and env vars resolved. '''
    return os.path.normpath( os.path.abspath(os.path.expandvars(p) )).replace( '\\', '/' )

    
def compare(a, b): # type: (str, str) -> bool
    return normalize(a) == normalize(b)


def nicePath(path): # type: (str) -> str
    # Returns a cased and normalized path
    return os.path.normcase( os.path.normpath( path ) )


def cleanFilepath(filepath): # type: (str) -> str
    '''
    Removes whitespace capping and wrapping quotes from the given string (win clipboard adds quotes)
    '''
    filepath = filepath.splitlines()[0].strip()

    # Strip quote wrapping
    if filepath[0] in ['"', "'"]:
        filepath = filepath[1:]
    if filepath[-1] in ['"', "'"]:
        filepath = filepath[:-1]
        
    return filepath


def getMayaFiles(folder): # type: (str) -> List[str]
    '''
    Gets all the maya files recursively from the directory, excluding backups
    '''
    
    allfiles = []
    
    for path, dirs, files in os.walk(folder):
        if 'incrementalSave' in dirs:
            dirs.remove('incrementalSave')
        if '.mayaScatches' in dirs:
            dirs.remove('.mayaScatches')
            
        for f in files:
            if f.lower().endswith( '.mb' ) or f.lower().endswith( '.ma' ):
                allfiles.append( path + '/' + f )
                
    return allfiles
    
    
def getTempPath(filename):
    '''
    Returns the full path for a temp file.  Doing this makes debugging easier,
    plus lets content transfer between maya sessions.
    '''
    
    tempdir = tempfile.gettempdir() + '/maya_pdil'
    
    if not os.path.exists(tempdir):
        os.makedirs(tempdir)
    
    return tempdir + '/' + filename