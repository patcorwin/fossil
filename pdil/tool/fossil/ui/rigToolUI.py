# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'rigToolUI.ui'
##
## Created by: Qt User Interface Compiler version 5.15.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *

from pdil.tool.fossil.jointlister import JointLister
from pdil.tool.fossil.cardlister import CardLister
from pdil.tool.fossil.cardparams import CardParams


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1201, 1050)
        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(MainWindow.sizePolicy().hasHeightForWidth())
        MainWindow.setSizePolicy(sizePolicy)
        self.actionCard_Orients = QAction(MainWindow)
        self.actionCard_Orients.setObjectName(u"actionCard_Orients")
        self.actionCard_Orients.setCheckable(True)
        self.actionReconnect_Real_Joints = QAction(MainWindow)
        self.actionReconnect_Real_Joints.setObjectName(u"actionReconnect_Real_Joints")
        self.actionCard_Orients_2 = QAction(MainWindow)
        self.actionCard_Orients_2.setObjectName(u"actionCard_Orients_2")
        self.actionCard_Orients_2.setCheckable(True)
        self.actionConnectors = QAction(MainWindow)
        self.actionConnectors.setObjectName(u"actionConnectors")
        self.actionConnectors.setCheckable(True)
        self.actionHandles = QAction(MainWindow)
        self.actionHandles.setObjectName(u"actionHandles")
        self.actionHandles.setCheckable(True)
        self.actionMatch_Selected_Orients = QAction(MainWindow)
        self.actionMatch_Selected_Orients.setObjectName(u"actionMatch_Selected_Orients")
        self.actionNaming_Rules = QAction(MainWindow)
        self.actionNaming_Rules.setObjectName(u"actionNaming_Rules")
        self.actionShow_Individual_Restores = QAction(MainWindow)
        self.actionShow_Individual_Restores.setObjectName(u"actionShow_Individual_Restores")
        self.actionShow_Individual_Restores.setCheckable(True)
        self.actionShow_Card_Rig_State = QAction(MainWindow)
        self.actionShow_Card_Rig_State.setObjectName(u"actionShow_Card_Rig_State")
        self.actionShow_Card_Rig_State.setCheckable(True)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.horizontalLayout = QHBoxLayout(self.centralwidget)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.tabWidget = QTabWidget(self.centralwidget)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tab = QWidget()
        self.tab.setObjectName(u"tab")
        self.tabWidget.addTab(self.tab, "")
        self.tab_3 = QWidget()
        self.tab_3.setObjectName(u"tab_3")
        self.horizontalLayout_2 = QHBoxLayout(self.tab_3)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.splitter_2 = QSplitter(self.tab_3)
        self.splitter_2.setObjectName(u"splitter_2")
        self.splitter_2.setOrientation(Qt.Horizontal)
        self.widget = QWidget(self.splitter_2)
        self.widget.setObjectName(u"widget")
        self.verticalLayout_3 = QVBoxLayout(self.widget)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(-1, 0, -1, 0)
        self.splitter = QSplitter(self.widget)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Vertical)
        self.widget_4 = QWidget(self.splitter)
        self.widget_4.setObjectName(u"widget_4")
        self.verticalLayout = QVBoxLayout(self.widget_4)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(-1, 0, -1, 0)
        self.horizontalLayout_6 = QHBoxLayout()
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.horizontalLayout_6.setContentsMargins(-1, 0, -1, -1)
        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(-1, -1, -1, 3)
        self.jointCount = QSpinBox(self.widget_4)
        self.jointCount.setObjectName(u"jointCount")
        self.jointCount.setMinimum(1)

        self.gridLayout.addWidget(self.jointCount, 0, 0, 1, 1)

        self.buildBonesBtn = QPushButton(self.widget_4)
        self.buildBonesBtn.setObjectName(u"buildBonesBtn")

        self.gridLayout.addWidget(self.buildBonesBtn, 1, 1, 1, 1)

        self.buildRigBtn = QPushButton(self.widget_4)
        self.buildRigBtn.setObjectName(u"buildRigBtn")

        self.gridLayout.addWidget(self.buildRigBtn, 1, 2, 1, 1)

        self.cardJointNames = QLineEdit(self.widget_4)
        self.cardJointNames.setObjectName(u"cardJointNames")

        self.gridLayout.addWidget(self.cardJointNames, 0, 1, 1, 2)

        self.selectAllBtn = QPushButton(self.widget_4)
        self.selectAllBtn.setObjectName(u"selectAllBtn")

        self.gridLayout.addWidget(self.selectAllBtn, 1, 0, 1, 1)

        self.deleteRigBtn = QPushButton(self.widget_4)
        self.deleteRigBtn.setObjectName(u"deleteRigBtn")

        self.gridLayout.addWidget(self.deleteRigBtn, 2, 2, 1, 1)

        self.deleteBonesBtn = QPushButton(self.widget_4)
        self.deleteBonesBtn.setObjectName(u"deleteBonesBtn")

        self.gridLayout.addWidget(self.deleteBonesBtn, 2, 1, 1, 1)

        self.saveModsBtn = QPushButton(self.widget_4)
        self.saveModsBtn.setObjectName(u"saveModsBtn")

        self.gridLayout.addWidget(self.saveModsBtn, 1, 3, 1, 1)

        self.restoreModsBtn = QPushButton(self.widget_4)
        self.restoreModsBtn.setObjectName(u"restoreModsBtn")

        self.gridLayout.addWidget(self.restoreModsBtn, 2, 3, 1, 1)

        self.label_15 = QLabel(self.widget_4)
        self.label_15.setObjectName(u"label_15")

        self.gridLayout.addWidget(self.label_15, 1, 4, 1, 1)

        self.makeCardBtn = QPushButton(self.widget_4)
        self.makeCardBtn.setObjectName(u"makeCardBtn")

        self.gridLayout.addWidget(self.makeCardBtn, 0, 5, 1, 1)

        self.rebuildProxyBtn = QPushButton(self.widget_4)
        self.rebuildProxyBtn.setObjectName(u"rebuildProxyBtn")

        self.gridLayout.addWidget(self.rebuildProxyBtn, 0, 6, 1, 1)


        self.horizontalLayout_6.addLayout(self.gridLayout)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horizontalLayout_6.addItem(self.horizontalSpacer)

        self.restoreContainer = QWidget(self.widget_4)
        self.restoreContainer.setObjectName(u"restoreContainer")
        sizePolicy.setHeightForWidth(self.restoreContainer.sizePolicy().hasHeightForWidth())
        self.restoreContainer.setSizePolicy(sizePolicy)
        self.restoreContainer.setMinimumSize(QSize(30, 0))
        self.horizontalLayout_13 = QHBoxLayout(self.restoreContainer)
        self.horizontalLayout_13.setSpacing(0)
        self.horizontalLayout_13.setObjectName(u"horizontalLayout_13")
        self.horizontalLayout_13.setContentsMargins(0, 0, 0, 0)
        self.layout = QGridLayout()
        self.layout.setObjectName(u"layout")
        self.layout.setContentsMargins(-1, -1, -1, 3)
        self.constraintsRestore = QPushButton(self.restoreContainer)
        self.constraintsRestore.setObjectName(u"constraintsRestore")

        self.layout.addWidget(self.constraintsRestore, 0, 2, 1, 1)

        self.lockedAttrsRestore = QPushButton(self.restoreContainer)
        self.lockedAttrsRestore.setObjectName(u"lockedAttrsRestore")

        self.layout.addWidget(self.lockedAttrsRestore, 1, 2, 1, 1)

        self.spacesRestore = QPushButton(self.restoreContainer)
        self.spacesRestore.setObjectName(u"spacesRestore")

        self.layout.addWidget(self.spacesRestore, 0, 0, 1, 1)

        self.pushButton_3 = QPushButton(self.restoreContainer)
        self.pushButton_3.setObjectName(u"pushButton_3")

        self.layout.addWidget(self.pushButton_3, 3, 0, 1, 1)

        self.visGroupRestore = QPushButton(self.restoreContainer)
        self.visGroupRestore.setObjectName(u"visGroupRestore")

        self.layout.addWidget(self.visGroupRestore, 1, 0, 1, 1)

        self.connectionsRestore = QPushButton(self.restoreContainer)
        self.connectionsRestore.setObjectName(u"connectionsRestore")

        self.layout.addWidget(self.connectionsRestore, 0, 1, 1, 1)

        self.setDrivenRestore = QPushButton(self.restoreContainer)
        self.setDrivenRestore.setObjectName(u"setDrivenRestore")

        self.layout.addWidget(self.setDrivenRestore, 1, 1, 1, 1)

        self.customAttrsRestore = QPushButton(self.restoreContainer)
        self.customAttrsRestore.setObjectName(u"customAttrsRestore")

        self.layout.addWidget(self.customAttrsRestore, 3, 1, 1, 1)

        self.attrStateRestore = QPushButton(self.restoreContainer)
        self.attrStateRestore.setObjectName(u"attrStateRestore")

        self.layout.addWidget(self.attrStateRestore, 3, 2, 1, 1)


        self.horizontalLayout_13.addLayout(self.layout)


        self.horizontalLayout_6.addWidget(self.restoreContainer)


        self.verticalLayout.addLayout(self.horizontalLayout_6)

        self.cardLister = CardLister(self.widget_4)
        self.cardLister.setObjectName(u"cardLister")
        self.cardLister.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.cardLister.header().setStretchLastSection(False)

        self.verticalLayout.addWidget(self.cardLister)

        self.splitter.addWidget(self.widget_4)
        self.widget_5 = QWidget(self.splitter)
        self.widget_5.setObjectName(u"widget_5")
        self.verticalLayout_2 = QVBoxLayout(self.widget_5)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(-1, 0, -1, 0)
        self.horizontalLayout_7 = QHBoxLayout()
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.horizontalLayout_7.setContentsMargins(-1, 0, -1, -1)
        self.gridLayout_2 = QGridLayout()
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setContentsMargins(-1, 0, -1, -1)
        self.mergeCardBtn = QPushButton(self.widget_5)
        self.mergeCardBtn.setObjectName(u"mergeCardBtn")

        self.gridLayout_2.addWidget(self.mergeCardBtn, 0, 2, 1, 1)

        self.label = QLabel(self.widget_5)
        self.label.setObjectName(u"label")

        self.gridLayout_2.addWidget(self.label, 0, 0, 1, 1)

        self.label_16 = QLabel(self.widget_5)
        self.label_16.setObjectName(u"label_16")

        self.gridLayout_2.addWidget(self.label_16, 0, 4, 1, 1)

        self.splitCardBtn = QPushButton(self.widget_5)
        self.splitCardBtn.setObjectName(u"splitCardBtn")

        self.gridLayout_2.addWidget(self.splitCardBtn, 0, 3, 1, 1)

        self.addCardIkButton = QPushButton(self.widget_5)
        self.addCardIkButton.setObjectName(u"addCardIkButton")

        self.gridLayout_2.addWidget(self.addCardIkButton, 0, 5, 1, 1)

        self.label_2 = QLabel(self.widget_5)
        self.label_2.setObjectName(u"label_2")

        self.gridLayout_2.addWidget(self.label_2, 1, 0, 1, 1)

        self.duplicateCardBtn = QPushButton(self.widget_5)
        self.duplicateCardBtn.setObjectName(u"duplicateCardBtn")

        self.gridLayout_2.addWidget(self.duplicateCardBtn, 0, 1, 1, 1)

        self.remCardIkButton = QPushButton(self.widget_5)
        self.remCardIkButton.setObjectName(u"remCardIkButton")

        self.gridLayout_2.addWidget(self.remCardIkButton, 0, 6, 1, 1)

        self.insertJointBtn = QPushButton(self.widget_5)
        self.insertJointBtn.setObjectName(u"insertJointBtn")

        self.gridLayout_2.addWidget(self.insertJointBtn, 1, 1, 1, 1)

        self.addTipBtn = QPushButton(self.widget_5)
        self.addTipBtn.setObjectName(u"addTipBtn")

        self.gridLayout_2.addWidget(self.addTipBtn, 1, 2, 1, 1)

        self.deleteJointBtn = QPushButton(self.widget_5)
        self.deleteJointBtn.setObjectName(u"deleteJointBtn")

        self.gridLayout_2.addWidget(self.deleteJointBtn, 1, 3, 1, 1)

        self.customUpBtn = QPushButton(self.widget_5)
        self.customUpBtn.setObjectName(u"customUpBtn")

        self.gridLayout_2.addWidget(self.customUpBtn, 1, 5, 1, 1)


        self.horizontalLayout_7.addLayout(self.gridLayout_2)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horizontalLayout_7.addItem(self.horizontalSpacer_2)


        self.verticalLayout_2.addLayout(self.horizontalLayout_7)

        self.jointLister = JointLister(self.widget_5)
        if (self.jointLister.columnCount() < 6):
            self.jointLister.setColumnCount(6)
        __qtablewidgetitem = QTableWidgetItem()
        self.jointLister.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.jointLister.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        __qtablewidgetitem2 = QTableWidgetItem()
        self.jointLister.setHorizontalHeaderItem(2, __qtablewidgetitem2)
        __qtablewidgetitem3 = QTableWidgetItem()
        self.jointLister.setHorizontalHeaderItem(3, __qtablewidgetitem3)
        __qtablewidgetitem4 = QTableWidgetItem()
        self.jointLister.setHorizontalHeaderItem(4, __qtablewidgetitem4)
        __qtablewidgetitem5 = QTableWidgetItem()
        self.jointLister.setHorizontalHeaderItem(5, __qtablewidgetitem5)
        self.jointLister.setObjectName(u"jointLister")
        self.jointLister.setColumnCount(6)

        self.verticalLayout_2.addWidget(self.jointLister)

        self.splitter.addWidget(self.widget_5)

        self.verticalLayout_3.addWidget(self.splitter)

        self.splitter_2.addWidget(self.widget)
        self.propertyLayout = QWidget(self.splitter_2)
        self.propertyLayout.setObjectName(u"propertyLayout")
        self.propertyLayout.setMaximumSize(QSize(403, 16777215))
        self.verticalLayout_5 = QVBoxLayout(self.propertyLayout)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.verticalLayout_5.setContentsMargins(-1, 0, -1, -1)
        self.widget_7 = QWidget(self.propertyLayout)
        self.widget_7.setObjectName(u"widget_7")
        self.verticalLayout_4 = QVBoxLayout(self.widget_7)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalLayout_4.setContentsMargins(-1, 0, -1, -1)
        self.widget_8 = QWidget(self.widget_7)
        self.widget_8.setObjectName(u"widget_8")
        sizePolicy1 = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.widget_8.sizePolicy().hasHeightForWidth())
        self.widget_8.setSizePolicy(sizePolicy1)
        self.widget_8.setMinimumSize(QSize(0, 95))
        self.widget_8.setMaximumSize(QSize(16777215, 95))
        self.cardName = QLabel(self.widget_8)
        self.cardName.setObjectName(u"cardName")
        self.cardName.setGeometry(QRect(10, 0, 151, 20))
        self.cardType = QLabel(self.widget_8)
        self.cardType.setObjectName(u"cardType")
        self.cardType.setGeometry(QRect(180, 0, 81, 20))
        self.cardDescription = QLabel(self.widget_8)
        self.cardDescription.setObjectName(u"cardDescription")
        self.cardDescription.setGeometry(QRect(10, 20, 261, 71))
        self.cardDescription.setWordWrap(True)

        self.verticalLayout_4.addWidget(self.widget_8)

        self.cardParams = CardParams(self.widget_7)
        if (self.cardParams.columnCount() < 2):
            self.cardParams.setColumnCount(2)
        __qtablewidgetitem6 = QTableWidgetItem()
        self.cardParams.setHorizontalHeaderItem(0, __qtablewidgetitem6)
        __qtablewidgetitem7 = QTableWidgetItem()
        self.cardParams.setHorizontalHeaderItem(1, __qtablewidgetitem7)
        self.cardParams.setObjectName(u"cardParams")
        sizePolicy2 = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.cardParams.sizePolicy().hasHeightForWidth())
        self.cardParams.setSizePolicy(sizePolicy2)
        self.cardParams.setMinimumSize(QSize(0, 250))
        self.cardParams.horizontalHeader().setVisible(False)
        self.cardParams.horizontalHeader().setStretchLastSection(True)
        self.cardParams.verticalHeader().setVisible(False)

        self.verticalLayout_4.addWidget(self.cardParams)


        self.verticalLayout_5.addWidget(self.widget_7)

        self.propertySpacer = QSpacerItem(20, 1, QSizePolicy.Minimum, QSizePolicy.Expanding)

        self.verticalLayout_5.addItem(self.propertySpacer)

        self.rigStateContainer = QWidget(self.propertyLayout)
        self.rigStateContainer.setObjectName(u"rigStateContainer")
        self.verticalLayout_6 = QVBoxLayout(self.rigStateContainer)
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.updateRigState = QPushButton(self.rigStateContainer)
        self.updateRigState.setObjectName(u"updateRigState")

        self.verticalLayout_6.addWidget(self.updateRigState)

        self.rigStateTab = QTabWidget(self.rigStateContainer)
        self.rigStateTab.setObjectName(u"rigStateTab")
        self.rigStateTab.setTabPosition(QTabWidget.West)
        self.rigStateTab.setDocumentMode(False)
        self.tab_2 = QWidget()
        self.tab_2.setObjectName(u"tab_2")
        self.verticalLayout_11 = QVBoxLayout(self.tab_2)
        self.verticalLayout_11.setObjectName(u"verticalLayout_11")
        self.verticalLayout_11.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_14 = QHBoxLayout()
        self.horizontalLayout_14.setObjectName(u"horizontalLayout_14")
        self.space_save = QPushButton(self.tab_2)
        self.space_save.setObjectName(u"space_save")

        self.horizontalLayout_14.addWidget(self.space_save)

        self.space_load = QPushButton(self.tab_2)
        self.space_load.setObjectName(u"space_load")

        self.horizontalLayout_14.addWidget(self.space_load)


        self.verticalLayout_11.addLayout(self.horizontalLayout_14)

        self.spacesField = QTextEdit(self.tab_2)
        self.spacesField.setObjectName(u"spacesField")
        self.spacesField.setLineWrapMode(QTextEdit.NoWrap)

        self.verticalLayout_11.addWidget(self.spacesField)

        self.rigStateTab.addTab(self.tab_2, "")
        self.tab_8 = QWidget()
        self.tab_8.setObjectName(u"tab_8")
        self.verticalLayout_19 = QVBoxLayout(self.tab_8)
        self.verticalLayout_19.setObjectName(u"verticalLayout_19")
        self.verticalLayout_19.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_15 = QHBoxLayout()
        self.horizontalLayout_15.setObjectName(u"horizontalLayout_15")
        self.vis_save = QPushButton(self.tab_8)
        self.vis_save.setObjectName(u"vis_save")

        self.horizontalLayout_15.addWidget(self.vis_save)

        self.vis_load = QPushButton(self.tab_8)
        self.vis_load.setObjectName(u"vis_load")

        self.horizontalLayout_15.addWidget(self.vis_load)


        self.verticalLayout_19.addLayout(self.horizontalLayout_15)

        self.visGroupField = QTextEdit(self.tab_8)
        self.visGroupField.setObjectName(u"visGroupField")

        self.verticalLayout_19.addWidget(self.visGroupField)

        self.rigStateTab.addTab(self.tab_8, "")
        self.tab_6 = QWidget()
        self.tab_6.setObjectName(u"tab_6")
        self.verticalLayout_20 = QVBoxLayout(self.tab_6)
        self.verticalLayout_20.setObjectName(u"verticalLayout_20")
        self.verticalLayout_20.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_16 = QHBoxLayout()
        self.horizontalLayout_16.setObjectName(u"horizontalLayout_16")
        self.shape_save = QPushButton(self.tab_6)
        self.shape_save.setObjectName(u"shape_save")

        self.horizontalLayout_16.addWidget(self.shape_save)


        self.verticalLayout_20.addLayout(self.horizontalLayout_16)

        self.horizontalLayout_17 = QHBoxLayout()
        self.horizontalLayout_17.setObjectName(u"horizontalLayout_17")
        self.shape_local_load = QPushButton(self.tab_6)
        self.shape_local_load.setObjectName(u"shape_local_load")

        self.horizontalLayout_17.addWidget(self.shape_local_load)

        self.shape_world_load = QPushButton(self.tab_6)
        self.shape_world_load.setObjectName(u"shape_world_load")

        self.horizontalLayout_17.addWidget(self.shape_world_load)


        self.verticalLayout_20.addLayout(self.horizontalLayout_17)

        self.shapesField = QTextEdit(self.tab_6)
        self.shapesField.setObjectName(u"shapesField")

        self.verticalLayout_20.addWidget(self.shapesField)

        self.rigStateTab.addTab(self.tab_6, "")
        self.tab_7 = QWidget()
        self.tab_7.setObjectName(u"tab_7")
        self.verticalLayout_21 = QVBoxLayout(self.tab_7)
        self.verticalLayout_21.setObjectName(u"verticalLayout_21")
        self.verticalLayout_21.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_18 = QHBoxLayout()
        self.horizontalLayout_18.setObjectName(u"horizontalLayout_18")
        self.constraints_save = QPushButton(self.tab_7)
        self.constraints_save.setObjectName(u"constraints_save")

        self.horizontalLayout_18.addWidget(self.constraints_save)

        self.constraints_load = QPushButton(self.tab_7)
        self.constraints_load.setObjectName(u"constraints_load")

        self.horizontalLayout_18.addWidget(self.constraints_load)


        self.verticalLayout_21.addLayout(self.horizontalLayout_18)

        self.constraintsField = QTextEdit(self.tab_7)
        self.constraintsField.setObjectName(u"constraintsField")

        self.verticalLayout_21.addWidget(self.constraintsField)

        self.rigStateTab.addTab(self.tab_7, "")
        self.tab_5 = QWidget()
        self.tab_5.setObjectName(u"tab_5")
        self.verticalLayout_22 = QVBoxLayout(self.tab_5)
        self.verticalLayout_22.setObjectName(u"verticalLayout_22")
        self.verticalLayout_22.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_19 = QHBoxLayout()
        self.horizontalLayout_19.setObjectName(u"horizontalLayout_19")
        self.connections_save = QPushButton(self.tab_5)
        self.connections_save.setObjectName(u"connections_save")

        self.horizontalLayout_19.addWidget(self.connections_save)

        self.connections_load = QPushButton(self.tab_5)
        self.connections_load.setObjectName(u"connections_load")

        self.horizontalLayout_19.addWidget(self.connections_load)


        self.verticalLayout_22.addLayout(self.horizontalLayout_19)

        self.connectionsField = QTextEdit(self.tab_5)
        self.connectionsField.setObjectName(u"connectionsField")

        self.verticalLayout_22.addWidget(self.connectionsField)

        self.rigStateTab.addTab(self.tab_5, "")
        self.tab_9 = QWidget()
        self.tab_9.setObjectName(u"tab_9")
        self.verticalLayout_23 = QVBoxLayout(self.tab_9)
        self.verticalLayout_23.setObjectName(u"verticalLayout_23")
        self.verticalLayout_23.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_20 = QHBoxLayout()
        self.horizontalLayout_20.setObjectName(u"horizontalLayout_20")
        self.driven_save = QPushButton(self.tab_9)
        self.driven_save.setObjectName(u"driven_save")

        self.horizontalLayout_20.addWidget(self.driven_save)

        self.driven_load = QPushButton(self.tab_9)
        self.driven_load.setObjectName(u"driven_load")

        self.horizontalLayout_20.addWidget(self.driven_load)


        self.verticalLayout_23.addLayout(self.horizontalLayout_20)

        self.setDrivenField = QTextEdit(self.tab_9)
        self.setDrivenField.setObjectName(u"setDrivenField")

        self.verticalLayout_23.addWidget(self.setDrivenField)

        self.rigStateTab.addTab(self.tab_9, "")
        self.tab_10 = QWidget()
        self.tab_10.setObjectName(u"tab_10")
        self.verticalLayout_24 = QVBoxLayout(self.tab_10)
        self.verticalLayout_24.setObjectName(u"verticalLayout_24")
        self.verticalLayout_24.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_21 = QHBoxLayout()
        self.horizontalLayout_21.setObjectName(u"horizontalLayout_21")
        self.custom_save = QPushButton(self.tab_10)
        self.custom_save.setObjectName(u"custom_save")

        self.horizontalLayout_21.addWidget(self.custom_save)

        self.custom_load = QPushButton(self.tab_10)
        self.custom_load.setObjectName(u"custom_load")

        self.horizontalLayout_21.addWidget(self.custom_load)


        self.verticalLayout_24.addLayout(self.horizontalLayout_21)

        self.customAttrsField = QTextEdit(self.tab_10)
        self.customAttrsField.setObjectName(u"customAttrsField")

        self.verticalLayout_24.addWidget(self.customAttrsField)

        self.rigStateTab.addTab(self.tab_10, "")
        self.tab_12 = QWidget()
        self.tab_12.setObjectName(u"tab_12")
        self.verticalLayout_26 = QVBoxLayout(self.tab_12)
        self.verticalLayout_26.setObjectName(u"verticalLayout_26")
        self.horizontalLayout_23 = QHBoxLayout()
        self.horizontalLayout_23.setObjectName(u"horizontalLayout_23")
        self.attr_load = QPushButton(self.tab_12)
        self.attr_load.setObjectName(u"attr_load")

        self.horizontalLayout_23.addWidget(self.attr_load)

        self.attr_save = QPushButton(self.tab_12)
        self.attr_save.setObjectName(u"attr_save")

        self.horizontalLayout_23.addWidget(self.attr_save)


        self.verticalLayout_26.addLayout(self.horizontalLayout_23)

        self.attrStateField = QTextEdit(self.tab_12)
        self.attrStateField.setObjectName(u"attrStateField")

        self.verticalLayout_26.addWidget(self.attrStateField)

        self.rigStateTab.addTab(self.tab_12, "")
        self.tab_11 = QWidget()
        self.tab_11.setObjectName(u"tab_11")
        self.verticalLayout_25 = QVBoxLayout(self.tab_11)
        self.verticalLayout_25.setObjectName(u"verticalLayout_25")
        self.verticalLayout_25.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_22 = QHBoxLayout()
        self.horizontalLayout_22.setObjectName(u"horizontalLayout_22")
        self.locked_save = QPushButton(self.tab_11)
        self.locked_save.setObjectName(u"locked_save")

        self.horizontalLayout_22.addWidget(self.locked_save)

        self.locked_load = QPushButton(self.tab_11)
        self.locked_load.setObjectName(u"locked_load")

        self.horizontalLayout_22.addWidget(self.locked_load)


        self.verticalLayout_25.addLayout(self.horizontalLayout_22)

        self.lockedAttrsField = QTextEdit(self.tab_11)
        self.lockedAttrsField.setObjectName(u"lockedAttrsField")

        self.verticalLayout_25.addWidget(self.lockedAttrsField)

        self.rigStateTab.addTab(self.tab_11, "")

        self.verticalLayout_6.addWidget(self.rigStateTab)


        self.verticalLayout_5.addWidget(self.rigStateContainer)

        self.verticalLayout_5.setStretch(2, 1)
        self.splitter_2.addWidget(self.propertyLayout)

        self.horizontalLayout_2.addWidget(self.splitter_2)

        self.tabWidget.addTab(self.tab_3, "")
        self.controller_edit = QWidget()
        self.controller_edit.setObjectName(u"controller_edit")
        self.verticalLayout_7 = QVBoxLayout(self.controller_edit)
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.verticalLayout_13 = QVBoxLayout()
        self.verticalLayout_13.setObjectName(u"verticalLayout_13")
        self.verticalLayout_13.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_9 = QHBoxLayout()
        self.horizontalLayout_9.setObjectName(u"horizontalLayout_9")
        self.horizontalLayout_9.setContentsMargins(25, 25, 25, 25)
        self.verticalLayout_16 = QVBoxLayout()
        self.verticalLayout_16.setObjectName(u"verticalLayout_16")
        self.verticalLayout_16.setContentsMargins(25, -1, -1, -1)
        self.horizontalLayout_10 = QHBoxLayout()
        self.horizontalLayout_10.setObjectName(u"horizontalLayout_10")
        self.horizontalLayout_10.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_14 = QVBoxLayout()
        self.verticalLayout_14.setObjectName(u"verticalLayout_14")
        self.verticalLayout_14.setContentsMargins(0, -1, -1, -1)
        self.label_5 = QLabel(self.controller_edit)
        self.label_5.setObjectName(u"label_5")

        self.verticalLayout_14.addWidget(self.label_5)

        self.scrollArea = QScrollArea(self.controller_edit)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents_2 = QWidget()
        self.scrollAreaWidgetContents_2.setObjectName(u"scrollAreaWidgetContents_2")
        self.scrollAreaWidgetContents_2.setGeometry(QRect(0, 0, 353, 104))
        self.gridLayout_4 = QGridLayout(self.scrollAreaWidgetContents_2)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.shape_chooser = QGridLayout()
        self.shape_chooser.setObjectName(u"shape_chooser")

        self.gridLayout_4.addLayout(self.shape_chooser, 0, 0, 1, 1)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents_2)

        self.verticalLayout_14.addWidget(self.scrollArea)


        self.horizontalLayout_10.addLayout(self.verticalLayout_14)

        self.verticalLayout_15 = QVBoxLayout()
        self.verticalLayout_15.setObjectName(u"verticalLayout_15")
        self.verticalLayout_15.setContentsMargins(0, -1, -1, -1)
        self.label_11 = QLabel(self.controller_edit)
        self.label_11.setObjectName(u"label_11")

        self.verticalLayout_15.addWidget(self.label_11)

        self.surfaceColorGrid = QGridLayout()
        self.surfaceColorGrid.setObjectName(u"surfaceColorGrid")

        self.verticalLayout_15.addLayout(self.surfaceColorGrid)

        self.surfaceColorLayout = QGridLayout()
        self.surfaceColorLayout.setObjectName(u"surfaceColorLayout")
        self.surfaceColorLayout.setContentsMargins(-1, -1, -1, 55)

        self.verticalLayout_15.addLayout(self.surfaceColorLayout)

        self.label_12 = QLabel(self.controller_edit)
        self.label_12.setObjectName(u"label_12")

        self.verticalLayout_15.addWidget(self.label_12)

        self.curveColorGrid = QGridLayout()
        self.curveColorGrid.setObjectName(u"curveColorGrid")

        self.verticalLayout_15.addLayout(self.curveColorGrid)

        self.curveColorLayout = QGridLayout()
        self.curveColorLayout.setObjectName(u"curveColorLayout")

        self.verticalLayout_15.addLayout(self.curveColorLayout)


        self.horizontalLayout_10.addLayout(self.verticalLayout_15)


        self.verticalLayout_16.addLayout(self.horizontalLayout_10)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setContentsMargins(-1, 0, -1, -1)
        self.verticalLayout_8 = QVBoxLayout()
        self.verticalLayout_8.setObjectName(u"verticalLayout_8")
        self.verticalLayout_8.setContentsMargins(-1, 0, -1, 0)
        self.gridLayout_3 = QGridLayout()
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.gridLayout_3.setContentsMargins(-1, 0, -1, -1)
        self.label_13 = QLabel(self.controller_edit)
        self.label_13.setObjectName(u"label_13")
        self.label_13.setAlignment(Qt.AlignCenter)

        self.gridLayout_3.addWidget(self.label_13, 0, 0, 1, 1)

        self.label_14 = QLabel(self.controller_edit)
        self.label_14.setObjectName(u"label_14")
        self.label_14.setAlignment(Qt.AlignCenter)

        self.gridLayout_3.addWidget(self.label_14, 0, 1, 1, 1)

        self.copyShapes = QPushButton(self.controller_edit)
        self.copyShapes.setObjectName(u"copyShapes")

        self.gridLayout_3.addWidget(self.copyShapes, 1, 0, 1, 1)

        self.label_7 = QLabel(self.controller_edit)
        self.label_7.setObjectName(u"label_7")
        self.label_7.setAlignment(Qt.AlignCenter)

        self.gridLayout_3.addWidget(self.label_7, 0, 2, 1, 1)

        self.select_cvs = QPushButton(self.controller_edit)
        self.select_cvs.setObjectName(u"select_cvs")

        self.gridLayout_3.addWidget(self.select_cvs, 1, 2, 1, 1)

        self.copyToCBBtn = QPushButton(self.controller_edit)
        self.copyToCBBtn.setObjectName(u"copyToCBBtn")

        self.gridLayout_3.addWidget(self.copyToCBBtn, 1, 1, 1, 1)

        self.pasteLocalBtn = QPushButton(self.controller_edit)
        self.pasteLocalBtn.setObjectName(u"pasteLocalBtn")

        self.gridLayout_3.addWidget(self.pasteLocalBtn, 2, 1, 1, 1)

        self.pasteWorldBtn = QPushButton(self.controller_edit)
        self.pasteWorldBtn.setObjectName(u"pasteWorldBtn")

        self.gridLayout_3.addWidget(self.pasteWorldBtn, 3, 1, 1, 1)

        self.select_band_edge_1 = QPushButton(self.controller_edit)
        self.select_band_edge_1.setObjectName(u"select_band_edge_1")

        self.gridLayout_3.addWidget(self.select_band_edge_1, 3, 2, 1, 1)

        self.mirrorShapes = QPushButton(self.controller_edit)
        self.mirrorShapes.setObjectName(u"mirrorShapes")

        self.gridLayout_3.addWidget(self.mirrorShapes, 2, 0, 1, 1)

        self.mirrorSide = QPushButton(self.controller_edit)
        self.mirrorSide.setObjectName(u"mirrorSide")

        self.gridLayout_3.addWidget(self.mirrorSide, 3, 0, 1, 1)

        self.select_pin_head = QPushButton(self.controller_edit)
        self.select_pin_head.setObjectName(u"select_pin_head")

        self.gridLayout_3.addWidget(self.select_pin_head, 2, 2, 1, 1)

        self.select_band_edge_2 = QPushButton(self.controller_edit)
        self.select_band_edge_2.setObjectName(u"select_band_edge_2")

        self.gridLayout_3.addWidget(self.select_band_edge_2, 4, 2, 1, 1)

        self.copyColor = QPushButton(self.controller_edit)
        self.copyColor.setObjectName(u"copyColor")

        self.gridLayout_3.addWidget(self.copyColor, 4, 0, 1, 1)


        self.verticalLayout_8.addLayout(self.gridLayout_3)

        self.label_9 = QLabel(self.controller_edit)
        self.label_9.setObjectName(u"label_9")
        sizePolicy1.setHeightForWidth(self.label_9.sizePolicy().hasHeightForWidth())
        self.label_9.setSizePolicy(sizePolicy1)
        self.label_9.setAlignment(Qt.AlignCenter)

        self.verticalLayout_8.addWidget(self.label_9)

        self.horizontalLayout_11 = QHBoxLayout()
        self.horizontalLayout_11.setObjectName(u"horizontalLayout_11")
        self.horizontalLayout_11.setContentsMargins(-1, 0, -1, -1)
        self.minus_ten = QPushButton(self.controller_edit)
        self.minus_ten.setObjectName(u"minus_ten")

        self.horizontalLayout_11.addWidget(self.minus_ten)

        self.minus_one = QPushButton(self.controller_edit)
        self.minus_one.setObjectName(u"minus_one")

        self.horizontalLayout_11.addWidget(self.minus_one)

        self.plus_one = QPushButton(self.controller_edit)
        self.plus_one.setObjectName(u"plus_one")

        self.horizontalLayout_11.addWidget(self.plus_one)

        self.plus_ten = QPushButton(self.controller_edit)
        self.plus_ten.setObjectName(u"plus_ten")

        self.horizontalLayout_11.addWidget(self.plus_ten)


        self.verticalLayout_8.addLayout(self.horizontalLayout_11)

        self.label_10 = QLabel(self.controller_edit)
        self.label_10.setObjectName(u"label_10")
        sizePolicy1.setHeightForWidth(self.label_10.sizePolicy().hasHeightForWidth())
        self.label_10.setSizePolicy(sizePolicy1)
        self.label_10.setAlignment(Qt.AlignBottom|Qt.AlignHCenter)

        self.verticalLayout_8.addWidget(self.label_10)

        self.gridLayout_5 = QGridLayout()
        self.gridLayout_5.setObjectName(u"gridLayout_5")
        self.gridLayout_5.setContentsMargins(-1, 0, -1, -1)
        self.rot_local_y = QPushButton(self.controller_edit)
        self.rot_local_y.setObjectName(u"rot_local_y")

        self.gridLayout_5.addWidget(self.rot_local_y, 2, 0, 1, 1)

        self.label_6 = QLabel(self.controller_edit)
        self.label_6.setObjectName(u"label_6")
        sizePolicy1.setHeightForWidth(self.label_6.sizePolicy().hasHeightForWidth())
        self.label_6.setSizePolicy(sizePolicy1)
        self.label_6.setAlignment(Qt.AlignCenter)

        self.gridLayout_5.addWidget(self.label_6, 0, 0, 1, 1)

        self.label_8 = QLabel(self.controller_edit)
        self.label_8.setObjectName(u"label_8")
        sizePolicy1.setHeightForWidth(self.label_8.sizePolicy().hasHeightForWidth())
        self.label_8.setSizePolicy(sizePolicy1)
        self.label_8.setAlignment(Qt.AlignCenter)

        self.gridLayout_5.addWidget(self.label_8, 0, 1, 1, 1)

        self.rot_world_x = QPushButton(self.controller_edit)
        self.rot_world_x.setObjectName(u"rot_world_x")

        self.gridLayout_5.addWidget(self.rot_world_x, 1, 1, 1, 1)

        self.rot_local_x = QPushButton(self.controller_edit)
        self.rot_local_x.setObjectName(u"rot_local_x")

        self.gridLayout_5.addWidget(self.rot_local_x, 1, 0, 1, 1)

        self.rot_world_y = QPushButton(self.controller_edit)
        self.rot_world_y.setObjectName(u"rot_world_y")

        self.gridLayout_5.addWidget(self.rot_world_y, 2, 1, 1, 1)

        self.rot_local_z = QPushButton(self.controller_edit)
        self.rot_local_z.setObjectName(u"rot_local_z")

        self.gridLayout_5.addWidget(self.rot_local_z, 3, 0, 1, 1)

        self.rot_world_z = QPushButton(self.controller_edit)
        self.rot_world_z.setObjectName(u"rot_world_z")

        self.gridLayout_5.addWidget(self.rot_world_z, 3, 1, 1, 1)


        self.verticalLayout_8.addLayout(self.gridLayout_5)


        self.horizontalLayout_3.addLayout(self.verticalLayout_8)

        self.horizontalSpacer_3 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horizontalLayout_3.addItem(self.horizontalSpacer_3)


        self.verticalLayout_16.addLayout(self.horizontalLayout_3)


        self.horizontalLayout_9.addLayout(self.verticalLayout_16)

        self.controlCardList = QTreeWidget(self.controller_edit)
        __qtreewidgetitem = QTreeWidgetItem()
        __qtreewidgetitem.setText(0, u"1");
        self.controlCardList.setHeaderItem(__qtreewidgetitem)
        self.controlCardList.setObjectName(u"controlCardList")
        self.controlCardList.header().setVisible(False)

        self.horizontalLayout_9.addWidget(self.controlCardList)


        self.verticalLayout_13.addLayout(self.horizontalLayout_9)

        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)

        self.verticalLayout_13.addItem(self.verticalSpacer_2)

        self.shapeDebug = QTextEdit(self.controller_edit)
        self.shapeDebug.setObjectName(u"shapeDebug")
        self.shapeDebug.setEnabled(True)
        self.shapeDebug.setLineWrapMode(QTextEdit.NoWrap)

        self.verticalLayout_13.addWidget(self.shapeDebug)


        self.verticalLayout_7.addLayout(self.verticalLayout_13)

        self.tabWidget.addTab(self.controller_edit, "")
        self.tab_4 = QWidget()
        self.tab_4.setObjectName(u"tab_4")
        self.visGroups = QListWidget(self.tab_4)
        self.visGroups.setObjectName(u"visGroups")
        self.visGroups.setGeometry(QRect(10, 10, 256, 381))
        self.verticalLayoutWidget_6 = QWidget(self.tab_4)
        self.verticalLayoutWidget_6.setObjectName(u"verticalLayoutWidget_6")
        self.verticalLayoutWidget_6.setGeometry(QRect(280, 10, 341, 381))
        self.verticalLayout_9 = QVBoxLayout(self.verticalLayoutWidget_6)
        self.verticalLayout_9.setObjectName(u"verticalLayout_9")
        self.verticalLayout_9.setContentsMargins(0, 0, 0, 0)
        self.unequipVisControl = QPushButton(self.verticalLayoutWidget_6)
        self.unequipVisControl.setObjectName(u"unequipVisControl")

        self.verticalLayout_9.addWidget(self.unequipVisControl)

        self.equipVisControl = QPushButton(self.verticalLayoutWidget_6)
        self.equipVisControl.setObjectName(u"equipVisControl")

        self.verticalLayout_9.addWidget(self.equipVisControl)

        self.pruneVisGroups = QPushButton(self.verticalLayoutWidget_6)
        self.pruneVisGroups.setObjectName(u"pruneVisGroups")

        self.verticalLayout_9.addWidget(self.pruneVisGroups)

        self.widget_3 = QWidget(self.verticalLayoutWidget_6)
        self.widget_3.setObjectName(u"widget_3")
        sizePolicy1.setHeightForWidth(self.widget_3.sizePolicy().hasHeightForWidth())
        self.widget_3.setSizePolicy(sizePolicy1)
        self.widget_3.setMinimumSize(QSize(0, 100))
        self.widget_3.setMaximumSize(QSize(16777215, 100))

        self.verticalLayout_9.addWidget(self.widget_3)

        self.tagAsMain = QPushButton(self.verticalLayoutWidget_6)
        self.tagAsMain.setObjectName(u"tagAsMain")

        self.verticalLayout_9.addWidget(self.tagAsMain)

        self.verticalSpacer_3 = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)

        self.verticalLayout_9.addItem(self.verticalSpacer_3)

        self.verticalLayoutWidget_7 = QWidget(self.tab_4)
        self.verticalLayoutWidget_7.setObjectName(u"verticalLayoutWidget_7")
        self.verticalLayoutWidget_7.setGeometry(QRect(10, 400, 611, 151))
        self.verticalLayout_10 = QVBoxLayout(self.verticalLayoutWidget_7)
        self.verticalLayout_10.setObjectName(u"verticalLayout_10")
        self.verticalLayout_10.setContentsMargins(0, 0, 0, 0)
        self.label_3 = QLabel(self.verticalLayoutWidget_7)
        self.label_3.setObjectName(u"label_3")

        self.verticalLayout_10.addWidget(self.label_3)

        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.horizontalLayout_4.setContentsMargins(-1, -1, 0, 0)
        self.visGroupNameEntry = QLineEdit(self.verticalLayoutWidget_7)
        self.visGroupNameEntry.setObjectName(u"visGroupNameEntry")

        self.horizontalLayout_4.addWidget(self.visGroupNameEntry)

        self.label_4 = QLabel(self.verticalLayoutWidget_7)
        self.label_4.setObjectName(u"label_4")

        self.horizontalLayout_4.addWidget(self.label_4)

        self.groupLevel = QSpinBox(self.verticalLayoutWidget_7)
        self.groupLevel.setObjectName(u"groupLevel")
        self.groupLevel.setMinimum(1)

        self.horizontalLayout_4.addWidget(self.groupLevel)

        self.assignVisGroup = QPushButton(self.verticalLayoutWidget_7)
        self.assignVisGroup.setObjectName(u"assignVisGroup")

        self.horizontalLayout_4.addWidget(self.assignVisGroup)


        self.verticalLayout_10.addLayout(self.horizontalLayout_4)

        self.verticalSpacer_4 = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)

        self.verticalLayout_10.addItem(self.verticalSpacer_4)

        self.tabWidget.addTab(self.tab_4, "")
        self.space_tab = QWidget()
        self.space_tab.setObjectName(u"space_tab")
        self.verticalLayout_17 = QVBoxLayout(self.space_tab)
        self.verticalLayout_17.setObjectName(u"verticalLayout_17")
        self.horizontalLayout_12 = QHBoxLayout()
        self.horizontalLayout_12.setObjectName(u"horizontalLayout_12")
        self.verticalLayout_18 = QVBoxLayout()
        self.verticalLayout_18.setObjectName(u"verticalLayout_18")
        self.verticalLayout_18.setContentsMargins(-1, -1, -1, 0)
        self.horizontalLayout_5 = QHBoxLayout()
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.verticalLayout_12 = QVBoxLayout()
        self.verticalLayout_12.setObjectName(u"verticalLayout_12")
        self.spaceList = QListWidget(self.space_tab)
        self.spaceList.setObjectName(u"spaceList")

        self.verticalLayout_12.addWidget(self.spaceList)

        self.horizontalLayout_8 = QHBoxLayout()
        self.horizontalLayout_8.setObjectName(u"horizontalLayout_8")
        self.spaceUp = QPushButton(self.space_tab)
        self.spaceUp.setObjectName(u"spaceUp")

        self.horizontalLayout_8.addWidget(self.spaceUp)

        self.spaceDown = QPushButton(self.space_tab)
        self.spaceDown.setObjectName(u"spaceDown")

        self.horizontalLayout_8.addWidget(self.spaceDown)


        self.verticalLayout_12.addLayout(self.horizontalLayout_8)


        self.horizontalLayout_5.addLayout(self.verticalLayout_12)


        self.verticalLayout_18.addLayout(self.horizontalLayout_5)

        self.spaceQuickButtons = QGridLayout()
        self.spaceQuickButtons.setObjectName(u"spaceQuickButtons")

        self.verticalLayout_18.addLayout(self.spaceQuickButtons)

        self.label_17 = QLabel(self.space_tab)
        self.label_17.setObjectName(u"label_17")

        self.verticalLayout_18.addWidget(self.label_17)

        self.multiWeights = QTableWidget(self.space_tab)
        if (self.multiWeights.columnCount() < 2):
            self.multiWeights.setColumnCount(2)
        self.multiWeights.setObjectName(u"multiWeights")
        self.multiWeights.setEnabled(False)
        self.multiWeights.setColumnCount(2)
        self.multiWeights.horizontalHeader().setVisible(False)

        self.verticalLayout_18.addWidget(self.multiWeights)


        self.horizontalLayout_12.addLayout(self.verticalLayout_18)

        self.horizontalSpacer_4 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horizontalLayout_12.addItem(self.horizontalSpacer_4)


        self.verticalLayout_17.addLayout(self.horizontalLayout_12)

        self.tabWidget.addTab(self.space_tab, "")

        self.horizontalLayout.addWidget(self.tabWidget)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 1201, 26))
        self.menuTools = QMenu(self.menubar)
        self.menuTools.setObjectName(u"menuTools")
        self.menuVisibility = QMenu(self.menuTools)
        self.menuVisibility.setObjectName(u"menuVisibility")
        self.menuSettings = QMenu(self.menubar)
        self.menuSettings.setObjectName(u"menuSettings")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.menubar.addAction(self.menuTools.menuAction())
        self.menubar.addAction(self.menuSettings.menuAction())
        self.menuTools.addAction(self.actionReconnect_Real_Joints)
        self.menuTools.addAction(self.menuVisibility.menuAction())
        self.menuTools.addAction(self.actionMatch_Selected_Orients)
        self.menuVisibility.addAction(self.actionCard_Orients_2)
        self.menuVisibility.addAction(self.actionConnectors)
        self.menuVisibility.addAction(self.actionHandles)
        self.menuSettings.addAction(self.actionNaming_Rules)
        self.menuSettings.addAction(self.actionShow_Individual_Restores)
        self.menuSettings.addAction(self.actionShow_Card_Rig_State)

        self.retranslateUi(MainWindow)

        self.tabWidget.setCurrentIndex(1)
        self.rigStateTab.setCurrentIndex(7)


        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.actionCard_Orients.setText(QCoreApplication.translate("MainWindow", u"Card Orients", None))
        self.actionReconnect_Real_Joints.setText(QCoreApplication.translate("MainWindow", u"Reconnect Real Joints", None))
        self.actionCard_Orients_2.setText(QCoreApplication.translate("MainWindow", u"Card Orients", None))
        self.actionConnectors.setText(QCoreApplication.translate("MainWindow", u"Connectors", None))
        self.actionHandles.setText(QCoreApplication.translate("MainWindow", u"Joint Handles", None))
        self.actionMatch_Selected_Orients.setText(QCoreApplication.translate("MainWindow", u"Match Selected Orients", None))
        self.actionNaming_Rules.setText(QCoreApplication.translate("MainWindow", u"Naming Rules", None))
        self.actionShow_Individual_Restores.setText(QCoreApplication.translate("MainWindow", u"Show Individual Restores", None))
        self.actionShow_Card_Rig_State.setText(QCoreApplication.translate("MainWindow", u"Show Card Rig State", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab), QCoreApplication.translate("MainWindow", u"Start", None))
        self.buildBonesBtn.setText(QCoreApplication.translate("MainWindow", u"Build Bones", None))
        self.buildRigBtn.setText(QCoreApplication.translate("MainWindow", u"Build Rig", None))
        self.selectAllBtn.setText(QCoreApplication.translate("MainWindow", u"Select All", None))
        self.deleteRigBtn.setText(QCoreApplication.translate("MainWindow", u"Delete Rig", None))
        self.deleteBonesBtn.setText(QCoreApplication.translate("MainWindow", u"Delete Bones", None))
        self.saveModsBtn.setText(QCoreApplication.translate("MainWindow", u"Save Mods", None))
        self.restoreModsBtn.setText(QCoreApplication.translate("MainWindow", u"Restore Mods", None))
        self.label_15.setText("")
        self.makeCardBtn.setText(QCoreApplication.translate("MainWindow", u"Make Card", None))
        self.rebuildProxyBtn.setText(QCoreApplication.translate("MainWindow", u"Rebuild Proxy", None))
        self.constraintsRestore.setText(QCoreApplication.translate("MainWindow", u"Const", None))
        self.lockedAttrsRestore.setText(QCoreApplication.translate("MainWindow", u"Locked", None))
        self.spacesRestore.setText(QCoreApplication.translate("MainWindow", u"Space", None))
        self.pushButton_3.setText(QCoreApplication.translate("MainWindow", u"Shape", None))
        self.visGroupRestore.setText(QCoreApplication.translate("MainWindow", u"Vis", None))
        self.connectionsRestore.setText(QCoreApplication.translate("MainWindow", u"Conn", None))
        self.setDrivenRestore.setText(QCoreApplication.translate("MainWindow", u"Driven", None))
        self.customAttrsRestore.setText(QCoreApplication.translate("MainWindow", u"Cust Attr", None))
        self.attrStateRestore.setText(QCoreApplication.translate("MainWindow", u"Attr St", None))
        ___qtreewidgetitem = self.cardLister.headerItem()
        ___qtreewidgetitem.setText(7, QCoreApplication.translate("MainWindow", u"Side", None));
        ___qtreewidgetitem.setText(6, QCoreApplication.translate("MainWindow", u"Mirror", None));
        ___qtreewidgetitem.setText(5, QCoreApplication.translate("MainWindow", u"End", None));
        ___qtreewidgetitem.setText(4, QCoreApplication.translate("MainWindow", u"Repeat", None));
        ___qtreewidgetitem.setText(3, QCoreApplication.translate("MainWindow", u"Start", None));
        ___qtreewidgetitem.setText(2, QCoreApplication.translate("MainWindow", u"Type", None));
        ___qtreewidgetitem.setText(1, QCoreApplication.translate("MainWindow", u"Vis", None));
        ___qtreewidgetitem.setText(0, QCoreApplication.translate("MainWindow", u"Name", None));
        self.mergeCardBtn.setText(QCoreApplication.translate("MainWindow", u"Merge", None))
        self.label.setText(QCoreApplication.translate("MainWindow", u"Cards", None))
        self.label_16.setText("")
        self.splitCardBtn.setText(QCoreApplication.translate("MainWindow", u"Split", None))
        self.addCardIkButton.setText(QCoreApplication.translate("MainWindow", u"Add Card Ik", None))
        self.label_2.setText(QCoreApplication.translate("MainWindow", u"Joints", None))
        self.duplicateCardBtn.setText(QCoreApplication.translate("MainWindow", u"Duplicate", None))
        self.remCardIkButton.setText(QCoreApplication.translate("MainWindow", u"Rem Card Ik", None))
        self.insertJointBtn.setText(QCoreApplication.translate("MainWindow", u"Insert Child", None))
        self.addTipBtn.setText(QCoreApplication.translate("MainWindow", u"Add Tip", None))
        self.deleteJointBtn.setText(QCoreApplication.translate("MainWindow", u"Delete", None))
        self.customUpBtn.setText(QCoreApplication.translate("MainWindow", u"Custom Up", None))
        ___qtablewidgetitem = self.jointLister.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("MainWindow", u"Name", None));
        ___qtablewidgetitem1 = self.jointLister.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("MainWindow", u"Helper", None));
        ___qtablewidgetitem2 = self.jointLister.horizontalHeaderItem(2)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("MainWindow", u"Output", None));
        ___qtablewidgetitem3 = self.jointLister.horizontalHeaderItem(3)
        ___qtablewidgetitem3.setText(QCoreApplication.translate("MainWindow", u"Handles", None));
        ___qtablewidgetitem4 = self.jointLister.horizontalHeaderItem(4)
        ___qtablewidgetitem4.setText(QCoreApplication.translate("MainWindow", u"Orient To", None));
        ___qtablewidgetitem5 = self.jointLister.horizontalHeaderItem(5)
        ___qtablewidgetitem5.setText(QCoreApplication.translate("MainWindow", u"Child Of", None));
        self.cardName.setText("")
        self.cardType.setText("")
        self.cardDescription.setText("")
        ___qtablewidgetitem6 = self.cardParams.horizontalHeaderItem(0)
        ___qtablewidgetitem6.setText(QCoreApplication.translate("MainWindow", u"1", None));
        ___qtablewidgetitem7 = self.cardParams.horizontalHeaderItem(1)
        ___qtablewidgetitem7.setText(QCoreApplication.translate("MainWindow", u"2", None));
        self.updateRigState.setText(QCoreApplication.translate("MainWindow", u"Update", None))
        self.space_save.setText(QCoreApplication.translate("MainWindow", u"Save", None))
        self.space_load.setText(QCoreApplication.translate("MainWindow", u"Load", None))
        self.rigStateTab.setTabText(self.rigStateTab.indexOf(self.tab_2), QCoreApplication.translate("MainWindow", u"Space", None))
        self.vis_save.setText(QCoreApplication.translate("MainWindow", u"Save", None))
        self.vis_load.setText(QCoreApplication.translate("MainWindow", u"Load", None))
        self.rigStateTab.setTabText(self.rigStateTab.indexOf(self.tab_8), QCoreApplication.translate("MainWindow", u"Vis", None))
        self.shape_save.setText(QCoreApplication.translate("MainWindow", u"Save", None))
        self.shape_local_load.setText(QCoreApplication.translate("MainWindow", u"Load Local", None))
        self.shape_world_load.setText(QCoreApplication.translate("MainWindow", u"Load World", None))
        self.rigStateTab.setTabText(self.rigStateTab.indexOf(self.tab_6), QCoreApplication.translate("MainWindow", u"Shape", None))
        self.constraints_save.setText(QCoreApplication.translate("MainWindow", u"Save", None))
        self.constraints_load.setText(QCoreApplication.translate("MainWindow", u"Load", None))
        self.rigStateTab.setTabText(self.rigStateTab.indexOf(self.tab_7), QCoreApplication.translate("MainWindow", u"Const", None))
        self.connections_save.setText(QCoreApplication.translate("MainWindow", u"Save", None))
        self.connections_load.setText(QCoreApplication.translate("MainWindow", u"Load", None))
        self.rigStateTab.setTabText(self.rigStateTab.indexOf(self.tab_5), QCoreApplication.translate("MainWindow", u"Conn", None))
        self.driven_save.setText(QCoreApplication.translate("MainWindow", u"Save", None))
        self.driven_load.setText(QCoreApplication.translate("MainWindow", u"Load", None))
        self.rigStateTab.setTabText(self.rigStateTab.indexOf(self.tab_9), QCoreApplication.translate("MainWindow", u"Driven", None))
        self.custom_save.setText(QCoreApplication.translate("MainWindow", u"Save", None))
        self.custom_load.setText(QCoreApplication.translate("MainWindow", u"Load", None))
        self.rigStateTab.setTabText(self.rigStateTab.indexOf(self.tab_10), QCoreApplication.translate("MainWindow", u"Custom", None))
        self.attr_load.setText(QCoreApplication.translate("MainWindow", u"PushButton", None))
        self.attr_save.setText(QCoreApplication.translate("MainWindow", u"PushButton", None))
        self.rigStateTab.setTabText(self.rigStateTab.indexOf(self.tab_12), QCoreApplication.translate("MainWindow", u"Page", None))
        self.locked_save.setText(QCoreApplication.translate("MainWindow", u"Save", None))
        self.locked_load.setText(QCoreApplication.translate("MainWindow", u"Load", None))
        self.rigStateTab.setTabText(self.rigStateTab.indexOf(self.tab_11), QCoreApplication.translate("MainWindow", u"Locked", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_3), QCoreApplication.translate("MainWindow", u"Cards", None))
        self.label_5.setText(QCoreApplication.translate("MainWindow", u"Shapes", None))
        self.label_11.setText(QCoreApplication.translate("MainWindow", u"Surface Color", None))
        self.label_12.setText(QCoreApplication.translate("MainWindow", u"Curve Color", None))
        self.label_13.setText(QCoreApplication.translate("MainWindow", u"Shapes", None))
        self.label_14.setText(QCoreApplication.translate("MainWindow", u"Shape Clipboard", None))
        self.copyShapes.setText(QCoreApplication.translate("MainWindow", u"Copy to Second Selection", None))
        self.label_7.setText(QCoreApplication.translate("MainWindow", u"Select CVs", None))
        self.select_cvs.setText(QCoreApplication.translate("MainWindow", u"All", None))
        self.copyToCBBtn.setText(QCoreApplication.translate("MainWindow", u"Copy", None))
        self.pasteLocalBtn.setText(QCoreApplication.translate("MainWindow", u"Paste Local", None))
        self.pasteWorldBtn.setText(QCoreApplication.translate("MainWindow", u"Paste World", None))
        self.select_band_edge_1.setText(QCoreApplication.translate("MainWindow", u"Band Edge 1", None))
        self.mirrorShapes.setText(QCoreApplication.translate("MainWindow", u"Mirror to Selected", None))
        self.mirrorSide.setText(QCoreApplication.translate("MainWindow", u"Mirror All to Other Side", None))
        self.select_pin_head.setText(QCoreApplication.translate("MainWindow", u"Pin Head", None))
        self.select_band_edge_2.setText(QCoreApplication.translate("MainWindow", u"Band Edge 2", None))
        self.copyColor.setText(QCoreApplication.translate("MainWindow", u"Copy Color", None))
        self.label_9.setText(QCoreApplication.translate("MainWindow", u"Scale", None))
        self.minus_ten.setText(QCoreApplication.translate("MainWindow", u"-10%", None))
        self.minus_one.setText(QCoreApplication.translate("MainWindow", u"-1%", None))
        self.plus_one.setText(QCoreApplication.translate("MainWindow", u"+1%", None))
        self.plus_ten.setText(QCoreApplication.translate("MainWindow", u"+10%", None))
        self.label_10.setText(QCoreApplication.translate("MainWindow", u"Rotate", None))
        self.rot_local_y.setText(QCoreApplication.translate("MainWindow", u"Rotate Y 45", None))
        self.label_6.setText(QCoreApplication.translate("MainWindow", u"Local", None))
        self.label_8.setText(QCoreApplication.translate("MainWindow", u"World", None))
        self.rot_world_x.setText(QCoreApplication.translate("MainWindow", u"Rotate X 45", None))
        self.rot_local_x.setText(QCoreApplication.translate("MainWindow", u"Rotate X 45", None))
        self.rot_world_y.setText(QCoreApplication.translate("MainWindow", u"Rotate Y 45", None))
        self.rot_local_z.setText(QCoreApplication.translate("MainWindow", u"Rotate Z 45", None))
        self.rot_world_z.setText(QCoreApplication.translate("MainWindow", u"Rotate Z 45", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.controller_edit), QCoreApplication.translate("MainWindow", u"Controller Edit", None))
        self.unequipVisControl.setText(QCoreApplication.translate("MainWindow", u"Unequip Vis Control", None))
        self.equipVisControl.setText(QCoreApplication.translate("MainWindow", u"Equip Vis Control", None))
        self.pruneVisGroups.setText(QCoreApplication.translate("MainWindow", u"Prune Unused Vis Groups", None))
        self.tagAsMain.setText(QCoreApplication.translate("MainWindow", u"Tag as Main Control", None))
        self.label_3.setText(QCoreApplication.translate("MainWindow", u"Assign to Group", None))
        self.label_4.setText(QCoreApplication.translate("MainWindow", u"Level", None))
        self.assignVisGroup.setText(QCoreApplication.translate("MainWindow", u"Assign", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_4), QCoreApplication.translate("MainWindow", u"Vis Groups", None))
        self.spaceUp.setText(QCoreApplication.translate("MainWindow", u" ^ ", None))
        self.spaceDown.setText(QCoreApplication.translate("MainWindow", u" v ", None))
        self.label_17.setText(QCoreApplication.translate("MainWindow", u"Multi Weights editor (doesn't work just yet)", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.space_tab), QCoreApplication.translate("MainWindow", u"Space", None))
        self.menuTools.setTitle(QCoreApplication.translate("MainWindow", u"Tools", None))
        self.menuVisibility.setTitle(QCoreApplication.translate("MainWindow", u"Visibility", None))
        self.menuSettings.setTitle(QCoreApplication.translate("MainWindow", u"Settings", None))
    # retranslateUi

