''' Fossil-aware skinning tools.
'''

from pymel.core import listConnections

import pdil


def getSkinClusters(cards):
    ''' Returns a list of skinClusters used by the given cards.
    '''
    skinClusters = set()
    for card in cards:
        for j in card.joints:
            if not j.isHelper:
                if j.real:
                    skinClusters.update( listConnections(j.real, type='skinCluster') )
                if j.realMirror:
                    skinClusters.update( listConnections(j.realMirror, type='skinCluster') )
                    
    return skinClusters

    
def cacheWeights(cards, weightCache):
    ''' Does a pdil.weights.get() on the meshes skinned to the given cards.  Stores results in weightCache.
    Reapply weights with `loadCachedWeights`.
    
    Args:
        cards: Iterable of blueprint cards
        weightCache: Empty dict
    '''
    
    skinClusters = getSkinClusters(cards)
    
    geometry = set()
    for skin in skinClusters:
        geometry.update( skin.getGeometry() )
        
    for geo in geometry:
        weightCache[geo] = pdil.weights.get(geo)
        
        
def loadCachedWeights(weightCache):
    ''' Applies the weights from weightCache (a dictionary) modified by `cacheWeights`.
    '''
    
    for g, skinData in weightCache.items():
        pdil.weights.apply(g, skinData)
    
    weightCache = {}