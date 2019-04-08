from __future__ import print_function, absolute_import

import os
import tempfile

try:
    from typing import List, Union # noqa
except ImportError:
    pass

try:
    # Only needed for `localizeFile` and `useSourceRoot`
    import pdilconfig
except ImportError:
    pass


SOURCE_ROOT = "RxSourceAssetRoot"


def normalize(p): # type: (str) -> str
    return os.path.normpath( os.path.abspath(os.path.expandvars(p) )).replace( '\\', '/' )

    
def compare(a, b): # type: (str, str) -> bool
    return normalize(a) == normalize(b)


def nicePath(path): # type: (str) -> str
    # Returns a cased and normalized path
    return os.path.normcase( os.path.normpath( path ) )


def cleanFilepath(filepath): # type: (str) -> str
    '''
    Removes whitespace and wrapping quotes from the given string.
    '''
    filepath = filepath.splitlines()[0].strip()

    # Strip quote wrapping
    if filepath[0] in ['"', "'"]:
        filepath = filepath[1:]
    if filepath[-1] in ['"', "'"]:
        filepath = filepath[:-1]
        
    return filepath


def localizeFile(filepath): # type: (str) -> str
    '''
    Given what might be depot path, or something from another user, convert it
    to what it would be on your machine.
    '''

    filepath = filepath.replace('\\', '/')

    key = '/sourceassets/'
    index = filepath.lower().find(key)
    if key != -1:
        return pdilconfig.sourceAssetDir() + '/' + filepath[index + len(key):]

    return filepath


def findRig(path): # type: (str) -> str
    '''
    Searches for a *_Rig.ma file adjacent, or in a parent directory.
    
    :returns: file path
    '''
            
    for f in os.listdir(path):
        if f.lower().endswith( '_rig.ma' ):
            return path + '/' + f
    else:
        if os.path.dirname(path) == path:
            return ''
        else:
            return findRig( os.path.dirname(path) )


def useSourceRoot(srcPath): # type: (str) -> str
    '''
    Given a path, return a version using the env var RxSourceAssetRoot if possible.
    
    ..todo: Probably rename to something like `formatFromSourceRoot`
    '''
    
    if nicePath(srcPath).startswith( nicePath(pdilconfig.sourceAssetDir()) ):
        path = '%{0}%'.format(SOURCE_ROOT) + os.path.normpath( srcPath )[len(nicePath(pdilconfig.sourceAssetDir())):]
    else:
        path = srcPath
        
    return path


def findLocalFile(path): # type: (str) -> Union[str, bool, None]
    '''
    Give a path, see if a local version exists.
    
    Returns False if no conversion was possible, None if it didn't think it
    needed to convert or a string of the new path that is source asset relative.
    '''
    
    if not path:
        return None
    
    if path.startswith('%'):
        return None
    
    if os.path.exists(path):
        return None
    
    norm = os.path.normpath(path)
    pos = norm.lower().find( '\\sourceassets\\' )
    if pos != -1:
        newPath = '%{0}%\\{1}'.format(SOURCE_ROOT, norm[pos + 14:])
        
        if os.path.exists( os.path.expandvars(newPath) ):
            return newPath
        else:
            print( 'Unable to convert', path, 'to', newPath, 'as the new path does not exist')
            
    else:
        print( 'This path does not appear to be in the SourceAssets', path)
        
    return False


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