# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'reposer_gui.ui'
##
## Created by: Qt User Interface Compiler version 5.15.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(409, 673)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout = QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(-1, 0, -1, -1)
        self.updateAll = QPushButton(self.centralwidget)
        self.updateAll.setObjectName(u"updateAll")

        self.horizontalLayout_2.addWidget(self.updateAll)

        self.updateSelected = QPushButton(self.centralwidget)
        self.updateSelected.setObjectName(u"updateSelected")

        self.horizontalLayout_2.addWidget(self.updateSelected)


        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setContentsMargins(-1, 0, -1, -1)
        self.runAll = QPushButton(self.centralwidget)
        self.runAll.setObjectName(u"runAll")

        self.horizontalLayout_3.addWidget(self.runAll)

        self.runSelected = QPushButton(self.centralwidget)
        self.runSelected.setObjectName(u"runSelected")

        self.horizontalLayout_3.addWidget(self.runSelected)


        self.verticalLayout.addLayout(self.horizontalLayout_3)

        self.line_2 = QFrame(self.centralwidget)
        self.line_2.setObjectName(u"line_2")
        self.line_2.setFrameShape(QFrame.HLine)
        self.line_2.setFrameShadow(QFrame.Sunken)

        self.verticalLayout.addWidget(self.line_2)

        self.goToBind = QPushButton(self.centralwidget)
        self.goToBind.setObjectName(u"goToBind")

        self.verticalLayout.addWidget(self.goToBind)

        self.aligns = QTableWidget(self.centralwidget)
        if (self.aligns.columnCount() < 4):
            self.aligns.setColumnCount(4)
        self.aligns.setObjectName(u"aligns")
        self.aligns.setColumnCount(4)
        self.aligns.horizontalHeader().setDefaultSectionSize(35)
        self.aligns.horizontalHeader().setStretchLastSection(True)

        self.verticalLayout.addWidget(self.aligns)

        self.widget = QWidget(self.centralwidget)
        self.widget.setObjectName(u"widget")
        self.horizontalLayout = QHBoxLayout(self.widget)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, -1, 0, -1)
        self.cardChooser = QComboBox(self.widget)
        self.cardChooser.setObjectName(u"cardChooser")

        self.horizontalLayout.addWidget(self.cardChooser)

        self.adjustmentChooser = QComboBox(self.widget)
        self.adjustmentChooser.setObjectName(u"adjustmentChooser")

        self.horizontalLayout.addWidget(self.adjustmentChooser)

        self.addAdjustment = QPushButton(self.widget)
        self.addAdjustment.setObjectName(u"addAdjustment")

        self.horizontalLayout.addWidget(self.addAdjustment)

        self.removeAdjustment = QPushButton(self.widget)
        self.removeAdjustment.setObjectName(u"removeAdjustment")

        self.horizontalLayout.addWidget(self.removeAdjustment)


        self.verticalLayout.addWidget(self.widget)

        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(-1, 10, -1, -1)
        self.label0 = QLabel(self.centralwidget)
        self.label0.setObjectName(u"label0")

        self.gridLayout.addWidget(self.label0, 0, 0, 1, 1)

        self.label1 = QLabel(self.centralwidget)
        self.label1.setObjectName(u"label1")

        self.gridLayout.addWidget(self.label1, 1, 0, 1, 1)

        self.input0 = QComboBox(self.centralwidget)
        self.input0.setObjectName(u"input0")

        self.gridLayout.addWidget(self.input0, 0, 2, 1, 1)

        self.input1 = QComboBox(self.centralwidget)
        self.input1.setObjectName(u"input1")

        self.gridLayout.addWidget(self.input1, 1, 2, 1, 1)

        self.label2 = QLabel(self.centralwidget)
        self.label2.setObjectName(u"label2")

        self.gridLayout.addWidget(self.label2, 2, 0, 1, 1)

        self.input2 = QComboBox(self.centralwidget)
        self.input2.setObjectName(u"input2")

        self.gridLayout.addWidget(self.input2, 2, 2, 1, 1)


        self.verticalLayout.addLayout(self.gridLayout)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 409, 21))
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.updateAll.setText(QCoreApplication.translate("MainWindow", u"Update All Reposers", None))
        self.updateSelected.setText(QCoreApplication.translate("MainWindow", u"Update Selected Reposers", None))
        self.runAll.setText(QCoreApplication.translate("MainWindow", u"Run All Adjusters", None))
        self.runSelected.setText(QCoreApplication.translate("MainWindow", u"Run Selected Adjusters", None))
        self.goToBind.setText(QCoreApplication.translate("MainWindow", u"Go To Bind Pose", None))
        self.addAdjustment.setText(QCoreApplication.translate("MainWindow", u"Add Adjustment", None))
        self.removeAdjustment.setText(QCoreApplication.translate("MainWindow", u"Remove", None))
        self.label0.setText(QCoreApplication.translate("MainWindow", u"TextLabel", None))
        self.label1.setText(QCoreApplication.translate("MainWindow", u"TextLabel", None))
        self.label2.setText(QCoreApplication.translate("MainWindow", u"TextLabel", None))
    # retranslateUi

