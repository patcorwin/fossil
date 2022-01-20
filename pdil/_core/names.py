'''
Utilities to deal with names changing, generally due to namespaces, and
namespaces in general.
'''

from __future__ import print_function, absolute_import

import collections
import re

import pymel.core
from pymel.core import objExists, listReferences, ls, cmds

from ..import _add

__all__ = ['findAlternates', 'findUniqueReferenceNamespace']


def _formatResults(newJoints):
    newJointExists = [ int(objExists(j)) for j in newJoints ]
    
    failed = len(newJointExists) - sum( newJointExists )

    if all( newJointExists ):
        return newJoints, failed
    return [], failed


def _changeNS(joints, oldNamespace, newNamespace):
    
    newNamespace = newNamespace if newNamespace.endswith(':') else newNamespace + ':'
    oldNamespace = oldNamespace if oldNamespace.endswith(':') else oldNamespace + ':'
    
    newJoints = [ j.replace( oldNamespace, newNamespace ) for j in joints ]
    return _formatResults(newJoints)


def _addNS(joints, newNamespace):

    newNamespace = newNamespace if newNamespace.endswith(':') else newNamespace + ':'
    newJoints = [ newNamespace + j for j in joints ]
    return _formatResults(newJoints)


def _remNS(joints, oldNamespace):

    oldNamespace = oldNamespace if oldNamespace.endswith(':') else oldNamespace + ':'
    
    newJoints = [ j.replace(oldNamespace, '') for j in joints ]
    return _formatResults(newJoints)


NSChange = collections.namedtuple( 'NSChance', 'alteration joints' )


def findAlternates(joints, available=None):
    '''
    Given a list of objects, see if they all exist in the scene and try to
    figure out if they have lost or gained namespaces.
    
    :param list joints: A list of string names, not PyNodes.
    :param list available: If specified, only these objects will be considered
        valid targets, otherwise the whole scene will be considered.
    :return: None if unable to find matches for everything or a NSChange with
        the alterations made and list of new joints.
        NSCHange.alteration is a list with will be:
            * ['rem', <ns>] # The namespace was removed
            * ['add', <ns>] # The namespace was add
            * ['sub', <old>, <new>] # <old> was replaced with <new>
        
    '''
    
    if available is not None:
        def objExists(obj):
            #print 'searching for', obj, type(obj)
            return obj in available
    else:
        objExists = pymel.core.objExists
    
    missing = [ j for j in joints if not objExists(j) ]
            
    fixed = not bool(missing)
    alteration = []
    
    lowestFail = len(missing)
    bestChoice = None

    if missing:
        print( '# missing %i / %i' % (len(missing), len(joints)) )

    if not missing:
        return NSChange([], joints)
    else:
        for missingObj in missing:
            if missingObj.count(':'):
                
                # Try stripping off any namespace (accounting for long names) and proceed if all bones exist.
                namespace, simpleName = missingObj.split('|')[-1].rsplit( ':', 1 )
                
                if objExists(simpleName):
                    newJoints, failedCount = _remNS(joints, namespace)
                    if newJoints:
                        #weights = substitute( weights, [(namespace, '')] )
                        alteration = ['rem', namespace + ':']
                        fixed = True
                    else:
                        if failedCount < lowestFail:
                            lowestFail = failedCount
                            bestChoice = ['rem', namespace + ':']
                
                if not fixed:
                    #print 'Testing to see if joints exist with a different namespace l.m.fa'
                    # See if only one obj exists in the scene with the
                    # simple name and try adding that namespace
                    if available:
                        others = [obj for obj in available if _add.simpleName(obj) == simpleName]
                    else:
                        others = ls(simpleName, r=1)
                    
                    for other in others:
                        newNamespace = _add.shortName(other).rsplit( ':', 1 )[0]
                        
                        newJoints, failedCount = _changeNS(joints, namespace, newNamespace)
                        
                        if newJoints:
                            #weights = substitute( weights, [(namespace, newNamespace)] )
                            alteration = ['sub', namespace + ':', newNamespace + ':']
                            fixed = True
                            break
                        else:
                            if failedCount < lowestFail:
                                lowestFail = failedCount
                                bestChoice = ['sub', namespace + ':', newNamespace + ':']
                    
            else:
                # See if the first bone has a namespace and try adding it
                # to all the others.
                others = cmds.ls( missingObj, r=1 )

                for other in others:
                    
                    if available is not None and other not in available:
                        continue
                    
                    namespace = other[ :-len(missingObj) ]
                    newJoints, failedCount = _addNS(joints, namespace)
                    if newJoints:
                        #weights = prepend( weights, namespace )
                        alteration = ['add', namespace]
                        fixed = True
                        break
                    else:
                        if failedCount < lowestFail:
                            lowestFail = failedCount
                            bestChoice = ['add', namespace]
                    
            if fixed:
                return NSChange(alteration, newJoints)

    if bestChoice:
        return NSChange( bestChoice, [] )
    else:
        return NSChange([], [])
        
        
def findUniqueReferenceNamespace(name):
    for ref in listReferences():
        if ref.namespace == name:
            if re.search( '__[A-Z]$', name ):
                return findUniqueReferenceNamespace( name[: - 1] + '__' + chr( ord(name[ - 1]) + 1 ) )
            else:
                return findUniqueReferenceNamespace( name + '__A' )
    
    return name