from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from pymel.core import window, button, columnLayout, textScrollList, scriptJob, selected, showWindow, select, text
from pymel.core import orientConstraint, pointConstraint, parentConstraint

from .. import _core as core


class ConstraintTracker(object):

    @staticmethod
    @core.alt.name('Constraint Tracker', 'Debug|Tools')
    def show(target=None):
        return ConstraintTracker(target)

    def __init__(self, target=None):
        self.obj = None
        self.win = window()
        with columnLayout():
            button(l='Tear Off', c=lambda *args: self.tearOff())
            text(l='Orient')
            self.orient = textScrollList()
            text(l='Point')
            self.point = textScrollList()
            text(l='Parent')
            self.parent = textScrollList()
        showWindow()
        
        self.orient.selectCommand( lambda *args: select(self.orient.getSelectItem()) )
        self.point.selectCommand( lambda *args: select(self.point.getSelectItem()) )
        self.parent.selectCommand( lambda *args: select(self.parent.getSelectItem()) )

        if target:
            self.viewObj(target)
        else:
            self.update()
            scriptJob( e=('SelectionChanged', core.alt.Callback(self.update)), p=self.win )
    
    def tearOff(self):
        self.show(self.obj)

    def update(self):
        sel = selected(type='transform')
        if sel:
            self.viewObj( sel[0] )
        else:
            return
    
    def viewObj(self, obj):
        self.win.setTitle(str(obj))
        self.obj = obj
        self.orient.removeAll()
        for obj in orientConstraint(obj, q=True, tl=True):
            self.orient.append(obj)

        self.point.removeAll()
        for obj in pointConstraint(obj, q=True, tl=True):
            self.point.append(obj)

        self.parent.removeAll()
        for obj in parentConstraint(obj, q=True, tl=True):
            self.parent.append(obj)
