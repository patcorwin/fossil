''' The idea is fossil-aware skinning tools.

&&& I think this should replace the code in main.py
    storeMeshes()
    restoreMeshes()


'''

from pymel.core import listConnections

import pdil


def getSkinClusters(cards):
    skinClusters = set()
    for card in cards:
        for j in card.joints:
            if not j.isHelper:
                if j.real:
                    skinClusters.update( listConnections(j.real, type='skinCluster') )
                if j.realMirror:
                    skinClusters.update( listConnections(j.realMirror, type='skinCluster') )
                    
    return skinClusters


if 'WEIGHTS' not in globals():
    WEIGHTS = {}
    
    
def cacheWeights(cards):
    global WEIGHTS
    WEIGHTS = {}
    
    skinClusters = getSkinClusters(cards)
    
    geo = set()
    for skin in skinClusters:
        geo.update( skin.getGeometry() )
        
    for g in geo:
        WEIGHTS[g] = pdil.weights.get(g)
        
        
def loadCachedWeights():
    global WEIGHTS
    
    for g, skinData in WEIGHTS.items():
        pdil.weights.apply(g, skinData)