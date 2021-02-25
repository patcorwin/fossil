from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from pymel.core import window, columnLayout, textScrollList, scriptJob, selected, showWindow, select
from pymel.core import orientConstraint, pointConstraint, parentConstraint

from .. import core


class ConstraintTracker(object):

    @staticmethod
    @core.alt.name('Constraint Tracker', 'Debug|Tools')
    def show():
        return ConstraintTracker()

    def __init__(self):
        w = window()
        with columnLayout():
            self.orient = textScrollList()
            self.point = textScrollList()
            self.parent = textScrollList()
        showWindow()

        self.orient.selectCommand( lambda *args: select(self.orient.getSelectItem()) )
        self.point.selectCommand( lambda *args: select(self.point.getSelectItem()) )
        self.parent.selectCommand( lambda *args: select(self.parent.getSelectItem()) )

        self.update()

        scriptJob( e=('SelectionChanged', core.alt.Callback(self.update)), p=w )

    def update(self):
        sel = selected(type='transform')
        if sel:
            obj = sel[0]
        else:
            return

        self.orient.removeAll()
        for obj in orientConstraint(obj, q=True, tl=True):
            self.orient.append(obj)

        self.point.removeAll()
        for obj in pointConstraint(obj, q=True, tl=True):
            self.point.append(obj)

        self.parent.removeAll()
        for obj in parentConstraint(obj, q=True, tl=True):
            self.parent.append(obj)
