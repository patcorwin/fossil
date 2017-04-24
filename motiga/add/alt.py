'''

Contains two systems for calling code that logs errors, `call` and `Callback`
if they occur.

Usage:
    # Decorate a function with alt.name (generally functions called via the shelf)
    @alt.name( 'Make Rocket' )
    def makeARocket():
        # A rocket is made
        pass

    # For Callbacks:
    window()
    columnLayout()
    button( l='Press me', c=alt.Callback( makeARocket ) )
    showWindow()

In either of the above cases, if an error occurs, it is automatically logged.
    
..  todo::
    Exclude patc from logging errors via motiga.NO_ERROR_LIST
    
'''
from __future__ import print_function

import inspect
import os
import numbers
import traceback

import traceback as TB

try:
    import motigaconfig
except ImportError:
    pass

try:
    import pymongo
except ImportError:
    pass


def connectToErrorDB():
    '''
    Connect the maya error database once for ease of use later on.
    
    ..  todo::
        * Handle database failed connections by
            * Change notify to journaled and send off message in separate thread
                On failure, save the errors locally somewhere for retrieval later
                or possibly email them.
    '''

    global _dbClient
    global _errorDB
    try:
        _dbClient = pymongo.MongoClient( motigaconfig.TECH_ART_DB, motigaconfig.DBPORT )
        _errorDB = _dbClient[motigaconfig.MAYA_DB_NAME][motigaconfig.MAYA_ERROR_COLLECTION_NAME]
    except Exception:
        print( traceback.format_exc() )


if '_dbClient' not in globals():
    _dbClient = None
    _errorDB = None
    #connectToErrorDB()
        
# This holds all the functions registered via `name`
if '_functions' not in globals():
    _functions = {}


def name(niceName):
    '''
    Decorate a function to give it a globally accessible name.  This allows
    shelves to refer to the global name while allowing the underlaying function
    to move around without having to change the shelf.
    '''
    def real_decorator(function):
    
        global _functions
    
        _functions[niceName] = function
    
        return function

    return real_decorator


def call(niceName):
    '''
    Find a registered function.
    '''
    global _functions
    
    if niceName not in _functions:
        raise Exception( '{0} is not a registered function.'.format(niceName) )
    
    def wrappedFunc(*args, **kwargs):
        with _ErrorDBLogger('alt', args, kwargs):
            res = _functions[niceName](*args, **kwargs)
            return res
        
    wrappedFunc.__doc__ = _functions[niceName].__doc__
    wrappedFunc.__name__ = _functions[niceName].__name__
        
    return wrappedFunc


def nicePath(path):
    return os.path.normpath( os.path.normcase(path) )


def displayVars(varDict):
    '''
    Give a dict of vars (globals(), <frame>.f_locals, etc), print out the non-
    modules ones.
    '''
    for name, val in varDict.items():
        if not inspect.ismodule( val ):
            print( '   ', name, '=', val )


def formatFunction(func, args, kwargs):
    '''
    Given a function name, args and kwargs, return a nicely formatted string of
    how it was called
    '''

    argStr = str(args)[1:-1]
    kwargStr = str(kwargs)[1:-1]
    
    params = []
    if argStr:
        params.append(argStr)
    if kwargStr:
        params.append(kwargStr)

    return "{0}({1})".format( str(func), ', '.join(params) )

    
class Callback(object):
    '''
    Wrapper for GUI callbacks to have nicer output when bugs happen
    '''
    def __init__(self, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def __call__(self, *args, **kwargs):
        with _ErrorDBLogger('cb', self.args, self.kwargs):
            res = self.func( *self.args, **self.kwargs )
        return res

    def __repr__(self):
        return "<Callback {0}>".format( self.func )


def cleanNamespace( varDict, output ):
    '''
    Given a namespace, like the locals() from a traceback, add the non-module
    ones to the output dict
    '''
    for name, val in varDict.items():
        if not inspect.ismodule( val ):
            if isinstance( val, numbers.Number ):
                output[name] = val
            else:
                output[name] = str(val)


class _ErrorDBLogger(object):
    '''
    Context Manager to wrap calls that could fail and log them to the maya error
    database.
    
    The intended use is to have a shared log between `call` and `Callback`.
    '''
    def __init__(self, funcType, args=(), kwargs={}):
        '''
        :param str funcType: Either 'alt' or 'cb' for alt.call or Callback
        :param () args: The arguments used when calling the function
        :param {} wkargs: The kwargs used when calling the function
        '''
        self.funcType = funcType
        self.args = args
        self.kwargs = kwargs
    
    def __enter__(self):
        pass
        
    def __exit__(self, type, value, traceback):
        if type is None:
            return
    
        global _errorDB
        toolRoot = nicePath(os.environ['RxArtToolRoot'])
        
        traces = []
        cur = traceback
        while cur:
            traces.append(cur)
            cur = cur.tb_next
                
        errorObj = {
            'user': os.environ['user'],
            'type': self.funcType,
            'inner_file': '',
            'inner_line': '',
            'inner_name': '',
            'inner_locals': {},
            
            'outer_file': '',
            'outer_line': '',
            'outer_name': '',
            'outer_locals': {},
        }
        
        def _log(location, filename, funcName, num, locals):
            # Location is either 'inner' or 'outer'
            errorObj[ location + '_file' ] = filename
            errorObj[ location + '_line' ] = num
            errorObj[ location + '_funcName' ] = str(funcName)
            cleanNamespace(locals, errorObj[ location + '_locals' ])
        
        # Search from the failure point up for local code that failed to avoid
        # useless things like pynode or divide by zero errors.
        for trace in reversed(traces):
            if nicePath( trace.tb_frame.f_code.co_filename ).startswith( toolRoot ):
                print( "Function", formatFunction( trace.tb_frame.f_code.co_name, self.args, self.kwargs ), 'at line', trace.tb_lineno, 'failed with locals:')
                displayVars( trace.tb_frame.f_locals )

                print( TB.format_exc() )

                _log( 'inner',
                    trace.tb_frame.f_code.co_filename,
                    trace.tb_frame.f_code.co_name,
                    trace.tb_lineno,
                    trace.tb_frame.f_locals )
                
                
                
                break
                        
        # Log the outer point where this context manager was called
        _log( 'outer',
            traceback.tb_frame.f_code.co_filename,
            traceback.tb_frame.f_code.co_name,
            traceback.tb_lineno,
            traceback.tb_frame.f_locals )
            
        if _errorDB:
            _errorDB.insert( errorObj )
            print( 'logged error' )