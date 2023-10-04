from __future__ import division

import pytest

from pymel.core import newFile, PyNode, select, setAttr, xform
from pdil.tool.fossil import space_experimental as space
from pdil.tool import fossil

import pdil

from .helpers import vectorAssert


def simpleCard(name, offset=0):
    card = fossil.card.makeCard(2, {'repeat': name } )
    card.tx.set( offset )
    card.ty.set( 40 )
    card.sy.set( 4 )

    data = card.rigData
    data['rigCmd'] = 'TranslateChain'
    card.rigData = data
    return card


@pytest.fixture
def lead():
    return simpleCard('lead')


@pytest.fixture
def follow():
    return simpleCard('follow', 20)


@pytest.fixture
def cleanFile():
    # Trick to clear the file but use fixtures
    newFile(f=True)


def test_single_parent(cleanFile, lead, follow):
    # given
    
    select(lead, follow)
    fossil.card.buildBones()
    fossil.card.buildRig()

    spec = {'type': 'SINGLE_PARENT', 'target': lead.outputCenter.fk}
    space.add(follow.outputCenter.fk, 'follow', spec)
    
    vectorAssert( pdil.dagObj.getPos(follow.outputCenter.fk), [20, 43, 0] )
    vectorAssert( pdil.dagObj.getRot(follow.outputCenter.fk), [0, 0, -90] )
    
    # when
    lead.outputCenter.fk.r.set( 10, 20, 30 )
    
    # then
    newPos = [17.6512823852, 51.8193922106, 3.26351822333]
    vectorAssert( pdil.dagObj.getPos(follow.outputCenter.fk), newPos )
    vectorAssert( pdil.dagObj.getRot(follow.outputCenter.fk), [10, 20, -60] )
    
    
class Test_multi_parent(object):
    
    def DISABLED_test_equal_weights(cls): # The final structure changed
        # given
        newFile(f=True)
        a = simpleCard('aaa')
        b = simpleCard('bbb')
        f = simpleCard('follow', 20)

        select(a, b, f)
        fossil.card.buildBones()
        fossil.card.buildRig()
        
        spec = {
            'type': 'MULTI_PARENT',
            'parentTargets': {a.outputCenter.fk: 1, b.outputCenter.fk: 1},
            'orientTargets': {a.outputCenter.fk: 1, b.outputCenter.fk: 1},
        }
        
        space.add(f.outputCenter.fk, 'follow', spec)
    
        vectorAssert( pdil.dagObj.getPos(f.outputCenter.fk), [20, 43, 0] )
        vectorAssert( pdil.dagObj.getRot(f.outputCenter.fk), [0, 0, -90] )
    
        # when 1
        a.outputCenter.fk.rz.set(90)
        
        # then 1
        vectorAssert( pdil.dagObj.getPos(f.outputCenter.fk), [10.0, 53.0, 0.0] )
        vectorAssert( pdil.dagObj.getRot(f.outputCenter.fk), [0.0, 0.0, -45.0] )
        
        # when 2
        b.outputCenter.fk.rz.set(-90)
        
        # then 2
        vectorAssert( pdil.dagObj.getPos(f.outputCenter.fk), [0.0, 43.0, 0.0] )
        vectorAssert( pdil.dagObj.getRot(f.outputCenter.fk), [0.0, 0.0, -90.0] )
    
        # when 3
        a.outputCenter.fk.tx.set(-20)
        vectorAssert( pdil.dagObj.getPos(f.outputCenter.fk), [0.0, 53.0, 0.0] )
    
        # when 4
        spaces = space.serializeSpaces(f.outputCenter.fk)
        assert spaces == [
            {
                'name': 'follow',
                'orientTargets': [({'cardPath': "card('aaa_card').outputCenter.fk",
                          'long': '|main|aaa01_fkChain|aaa01_ctrl_space|aaa01_ctrl_align|aaa01_ctrl',
                          'short': 'aaa01_ctrl'},
                         1.0),
                        ({'cardPath': "card('bbb_card').outputCenter.fk",
                          'long': '|main|bbb01_fkChain|bbb01_ctrl_space|bbb01_ctrl_align|bbb01_ctrl',
                          'short': 'bbb01_ctrl'},
                         1.0)],
                'parentTargets': [({'cardPath': "card('aaa_card').outputCenter.fk",
                          'long': '|main|aaa01_fkChain|aaa01_ctrl_space|aaa01_ctrl_align|aaa01_ctrl',
                          'short': 'aaa01_ctrl'},
                         1.0),
                        ({'cardPath': "card('bbb_card').outputCenter.fk",
                          'long': '|main|bbb01_fkChain|bbb01_ctrl_space|bbb01_ctrl_align|bbb01_ctrl',
                          'short': 'bbb01_ctrl'},
                         1.0)],
                'type': 'MULTI_PARENT'
            }
        ]
    
    
    def DISABLED_t_est_different_weights(cls):
        # given
        newFile(f=True)
        a = simpleCard('aaa')
        b = simpleCard('bbb')
        f = simpleCard('follow', 20)

        select(a, b, f)
        fossil.card.buildBones()
        fossil.card.buildRig()
        
        spec = {
            'type': 'MULTI_PARENT',
            'parentTargets': {a.outputCenter.fk: 1, b.outputCenter.fk: .5},
            'orientTargets': {a.outputCenter.fk: .9, b.outputCenter.fk: .1},
        }
        
        space.add(f.outputCenter.fk, 'follow', spec)
    
        vectorAssert( pdil.dagObj.getPos(f.outputCenter.fk), [20, 43, 0] )
        vectorAssert( pdil.dagObj.getRot(f.outputCenter.fk), [0, 0, -90] )
    
        # when 1
        b.outputCenter.fk.tz.set(30)
        
        # then 1
        vectorAssert( pdil.dagObj.getPos(f.outputCenter.fk), [20, 43, 10] )
        
        # when 2
        b.outputCenter.fk.tz.set(0)
        b.outputCenter.fk.rx.set(90)
        
        # then 2
        vectorAssert( pdil.dagObj.getPos(f.outputCenter.fk), [40/3, 43.0, 20/3] )
        vectorAssert( pdil.dagObj.getRot(f.outputCenter.fk), [8.33261700567, 0.0, -90.0] )
        
        # when 3
        b.outputCenter.fk.tx.set(10)
        b.outputCenter.fk.ry.set(20)
        
        vectorAssert( pdil.dagObj.getPos(f.outputCenter.fk), [40/3, 109/3, 20/3])
        vectorAssert( pdil.dagObj.getRot(f.outputCenter.fk), [8.68058093538, 18.4473180765, -88.5877429051])