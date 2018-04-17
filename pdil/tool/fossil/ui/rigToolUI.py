# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\MAYA_APP_DIR\fossil\motiga\tool\fossil/ui/rigToolUI.ui'
#
# Created: Mon Jul 03 22:32:56 2017
#      by: pyside2-uic  running on PySide2 2.0.0~alpha0
#
# WARNING! All changes made in this file will be lost!

from PySide2 import QtCore, QtGui, QtWidgets

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1234, 947)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.centralwidget)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.tabWidget = QtWidgets.QTabWidget(self.centralwidget)
        self.tabWidget.setObjectName("tabWidget")
        self.tab = QtWidgets.QWidget()
        self.tab.setObjectName("tab")
        self.tabWidget.addTab(self.tab, "")
        self.tab_2 = QtWidgets.QWidget()
        self.tab_2.setObjectName("tab_2")
        self.tabWidget.addTab(self.tab_2, "")
        self.tab_3 = QtWidgets.QWidget()
        self.tab_3.setObjectName("tab_3")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.tab_3)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.splitter_2 = QtWidgets.QSplitter(self.tab_3)
        self.splitter_2.setOrientation(QtCore.Qt.Horizontal)
        self.splitter_2.setObjectName("splitter_2")
        self.widget = QtWidgets.QWidget(self.splitter_2)
        self.widget.setObjectName("widget")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.widget)
        self.verticalLayout_3.setContentsMargins(-1, 0, -1, 0)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.splitter = QtWidgets.QSplitter(self.widget)
        self.splitter.setOrientation(QtCore.Qt.Vertical)
        self.splitter.setObjectName("splitter")
        self.widget_4 = QtWidgets.QWidget(self.splitter)
        self.widget_4.setObjectName("widget_4")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.widget_4)
        self.verticalLayout.setContentsMargins(-1, 0, -1, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.widget_3 = QtWidgets.QWidget(self.widget_4)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.widget_3.sizePolicy().hasHeightForWidth())
        self.widget_3.setSizePolicy(sizePolicy)
        self.widget_3.setMinimumSize(QtCore.QSize(0, 90))
        self.widget_3.setMaximumSize(QtCore.QSize(16777215, 121))
        self.widget_3.setObjectName("widget_3")
        self.jointCount = QtWidgets.QSpinBox(self.widget_3)
        self.jointCount.setGeometry(QtCore.QRect(10, 3, 42, 22))
        self.jointCount.setMinimum(1)
        self.jointCount.setObjectName("jointCount")
        self.cardJointNames = QtWidgets.QLineEdit(self.widget_3)
        self.cardJointNames.setGeometry(QtCore.QRect(60, 3, 113, 20))
        self.cardJointNames.setObjectName("cardJointNames")
        self.makeCardBtn = QtWidgets.QPushButton(self.widget_3)
        self.makeCardBtn.setGeometry(QtCore.QRect(190, 3, 75, 23))
        self.makeCardBtn.setObjectName("makeCardBtn")
        self.selectAllBtn = QtWidgets.QPushButton(self.widget_3)
        self.selectAllBtn.setGeometry(QtCore.QRect(10, 31, 75, 23))
        self.selectAllBtn.setObjectName("selectAllBtn")
        self.deleteBonesBtn = QtWidgets.QPushButton(self.widget_3)
        self.deleteBonesBtn.setGeometry(QtCore.QRect(90, 61, 75, 23))
        self.deleteBonesBtn.setObjectName("deleteBonesBtn")
        self.buildBonesBtn = QtWidgets.QPushButton(self.widget_3)
        self.buildBonesBtn.setGeometry(QtCore.QRect(90, 31, 75, 23))
        self.buildBonesBtn.setObjectName("buildBonesBtn")
        self.saveModsBtn = QtWidgets.QPushButton(self.widget_3)
        self.saveModsBtn.setGeometry(QtCore.QRect(250, 31, 75, 23))
        self.saveModsBtn.setObjectName("saveModsBtn")
        self.buildRigBtn = QtWidgets.QPushButton(self.widget_3)
        self.buildRigBtn.setGeometry(QtCore.QRect(170, 31, 75, 23))
        self.buildRigBtn.setObjectName("buildRigBtn")
        self.restoreModsBtn = QtWidgets.QPushButton(self.widget_3)
        self.restoreModsBtn.setGeometry(QtCore.QRect(250, 61, 75, 23))
        self.restoreModsBtn.setObjectName("restoreModsBtn")
        self.deleteRigBtn = QtWidgets.QPushButton(self.widget_3)
        self.deleteRigBtn.setGeometry(QtCore.QRect(169, 61, 75, 23))
        self.deleteRigBtn.setObjectName("deleteRigBtn")
        self.rebuildProxyBtn = QtWidgets.QPushButton(self.widget_3)
        self.rebuildProxyBtn.setGeometry(QtCore.QRect(430, 3, 81, 23))
        self.rebuildProxyBtn.setObjectName("rebuildProxyBtn")
        self.verticalLayout.addWidget(self.widget_3)
        self.cardLister = CardLister(self.widget_4)
        self.cardLister.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.cardLister.setObjectName("cardLister")
        self.verticalLayout.addWidget(self.cardLister)
        self.widget_5 = QtWidgets.QWidget(self.splitter)
        self.widget_5.setObjectName("widget_5")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.widget_5)
        self.verticalLayout_2.setContentsMargins(-1, 0, -1, 0)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.widget_6 = QtWidgets.QWidget(self.widget_5)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.widget_6.sizePolicy().hasHeightForWidth())
        self.widget_6.setSizePolicy(sizePolicy)
        self.widget_6.setMinimumSize(QtCore.QSize(0, 60))
        self.widget_6.setMaximumSize(QtCore.QSize(16777215, 80))
        self.widget_6.setObjectName("widget_6")
        self.duplicateCardBtn = QtWidgets.QPushButton(self.widget_6)
        self.duplicateCardBtn.setGeometry(QtCore.QRect(60, 2, 75, 23))
        self.duplicateCardBtn.setObjectName("duplicateCardBtn")
        self.insertJointBtn = QtWidgets.QPushButton(self.widget_6)
        self.insertJointBtn.setGeometry(QtCore.QRect(60, 32, 75, 23))
        self.insertJointBtn.setObjectName("insertJointBtn")
        self.addTipBtn = QtWidgets.QPushButton(self.widget_6)
        self.addTipBtn.setGeometry(QtCore.QRect(140, 32, 75, 23))
        self.addTipBtn.setObjectName("addTipBtn")
        self.deleteJointBtn = QtWidgets.QPushButton(self.widget_6)
        self.deleteJointBtn.setGeometry(QtCore.QRect(220, 32, 75, 23))
        self.deleteJointBtn.setObjectName("deleteJointBtn")
        self.mergeCardBtn = QtWidgets.QPushButton(self.widget_6)
        self.mergeCardBtn.setGeometry(QtCore.QRect(140, 2, 75, 23))
        self.mergeCardBtn.setObjectName("mergeCardBtn")
        self.splitCardBtn = QtWidgets.QPushButton(self.widget_6)
        self.splitCardBtn.setGeometry(QtCore.QRect(220, 2, 75, 23))
        self.splitCardBtn.setObjectName("splitCardBtn")
        self.pushButton_15 = QtWidgets.QPushButton(self.widget_6)
        self.pushButton_15.setGeometry(QtCore.QRect(320, 2, 75, 23))
        self.pushButton_15.setObjectName("pushButton_15")
        self.pushButton_16 = QtWidgets.QPushButton(self.widget_6)
        self.pushButton_16.setGeometry(QtCore.QRect(400, 2, 75, 23))
        self.pushButton_16.setObjectName("pushButton_16")
        self.label = QtWidgets.QLabel(self.widget_6)
        self.label.setGeometry(QtCore.QRect(10, 10, 46, 13))
        self.label.setObjectName("label")
        self.label_2 = QtWidgets.QLabel(self.widget_6)
        self.label_2.setGeometry(QtCore.QRect(10, 37, 46, 13))
        self.label_2.setObjectName("label_2")
        self.verticalLayout_2.addWidget(self.widget_6)
        self.jointLister = JointLister(self.widget_5)
        self.jointLister.setColumnCount(6)
        self.jointLister.setObjectName("jointLister")
        self.jointLister.setColumnCount(6)
        self.jointLister.setRowCount(0)
        item = QtWidgets.QTableWidgetItem()
        self.jointLister.setHorizontalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        self.jointLister.setHorizontalHeaderItem(1, item)
        item = QtWidgets.QTableWidgetItem()
        self.jointLister.setHorizontalHeaderItem(2, item)
        item = QtWidgets.QTableWidgetItem()
        self.jointLister.setHorizontalHeaderItem(3, item)
        item = QtWidgets.QTableWidgetItem()
        self.jointLister.setHorizontalHeaderItem(4, item)
        item = QtWidgets.QTableWidgetItem()
        self.jointLister.setHorizontalHeaderItem(5, item)
        self.verticalLayout_2.addWidget(self.jointLister)
        self.verticalLayout_3.addWidget(self.splitter)
        self.widget_2 = QtWidgets.QWidget(self.splitter_2)
        self.widget_2.setMaximumSize(QtCore.QSize(303, 16777215))
        self.widget_2.setObjectName("widget_2")
        self.verticalLayout_5 = QtWidgets.QVBoxLayout(self.widget_2)
        self.verticalLayout_5.setContentsMargins(-1, 0, -1, -1)
        self.verticalLayout_5.setObjectName("verticalLayout_5")
        self.widget_7 = QtWidgets.QWidget(self.widget_2)
        self.widget_7.setObjectName("widget_7")
        self.verticalLayout_4 = QtWidgets.QVBoxLayout(self.widget_7)
        self.verticalLayout_4.setContentsMargins(-1, 0, -1, -1)
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.widget_8 = QtWidgets.QWidget(self.widget_7)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.widget_8.sizePolicy().hasHeightForWidth())
        self.widget_8.setSizePolicy(sizePolicy)
        self.widget_8.setMinimumSize(QtCore.QSize(0, 95))
        self.widget_8.setMaximumSize(QtCore.QSize(16777215, 95))
        self.widget_8.setObjectName("widget_8")
        self.cardName = QtWidgets.QLabel(self.widget_8)
        self.cardName.setGeometry(QtCore.QRect(10, 0, 151, 20))
        self.cardName.setText("")
        self.cardName.setObjectName("cardName")
        self.cardType = QtWidgets.QLabel(self.widget_8)
        self.cardType.setGeometry(QtCore.QRect(180, 0, 81, 20))
        self.cardType.setText("")
        self.cardType.setObjectName("cardType")
        self.cardDescription = QtWidgets.QLabel(self.widget_8)
        self.cardDescription.setGeometry(QtCore.QRect(10, 20, 261, 71))
        self.cardDescription.setText("")
        self.cardDescription.setWordWrap(True)
        self.cardDescription.setObjectName("cardDescription")
        self.verticalLayout_4.addWidget(self.widget_8)
        self.cardParams = CardParams(self.widget_7)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.cardParams.sizePolicy().hasHeightForWidth())
        self.cardParams.setSizePolicy(sizePolicy)
        self.cardParams.setMinimumSize(QtCore.QSize(0, 250))
        self.cardParams.setObjectName("cardParams")
        self.cardParams.setColumnCount(2)
        self.cardParams.setRowCount(0)
        item = QtWidgets.QTableWidgetItem()
        self.cardParams.setHorizontalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        self.cardParams.setHorizontalHeaderItem(1, item)
        self.cardParams.horizontalHeader().setVisible(False)
        self.cardParams.horizontalHeader().setStretchLastSection(True)
        self.cardParams.verticalHeader().setVisible(False)
        self.verticalLayout_4.addWidget(self.cardParams)
        self.verticalLayout_5.addWidget(self.widget_7)
        spacerItem = QtWidgets.QSpacerItem(20, 466, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_5.addItem(spacerItem)
        self.controllerEdit = QtWidgets.QWidget(self.widget_2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.controllerEdit.sizePolicy().hasHeightForWidth())
        self.controllerEdit.setSizePolicy(sizePolicy)
        self.controllerEdit.setMinimumSize(QtCore.QSize(0, 400))
        self.controllerEdit.setMaximumSize(QtCore.QSize(16777215, 400))
        self.controllerEdit.setObjectName("controllerEdit")
        self.verticalLayout_6 = QtWidgets.QVBoxLayout(self.controllerEdit)
        self.verticalLayout_6.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_6.setObjectName("verticalLayout_6")
        self.testLayout = QtWidgets.QVBoxLayout()
        self.testLayout.setObjectName("testLayout")
        self.verticalLayout_6.addLayout(self.testLayout)
        self.verticalLayout_5.addWidget(self.controllerEdit)
        self.horizontalLayout_2.addWidget(self.splitter_2)
        self.tabWidget.addTab(self.tab_3, "")
        self.tab_4 = QtWidgets.QWidget()
        self.tab_4.setObjectName("tab_4")
        self.visGroups = QtWidgets.QListWidget(self.tab_4)
        self.visGroups.setGeometry(QtCore.QRect(10, 10, 256, 311))
        self.visGroups.setObjectName("visGroups")
        self.equipVisControl = QtWidgets.QPushButton(self.tab_4)
        self.equipVisControl.setGeometry(QtCore.QRect(280, 10, 151, 23))
        self.equipVisControl.setObjectName("equipVisControl")
        self.unequipVisControl = QtWidgets.QPushButton(self.tab_4)
        self.unequipVisControl.setGeometry(QtCore.QRect(280, 50, 151, 23))
        self.unequipVisControl.setObjectName("unequipVisControl")
        self.pruneVisGroups = QtWidgets.QPushButton(self.tab_4)
        self.pruneVisGroups.setGeometry(QtCore.QRect(280, 90, 151, 23))
        self.pruneVisGroups.setObjectName("pruneVisGroups")
        self.visGroupNameEntry = QtWidgets.QLineEdit(self.tab_4)
        self.visGroupNameEntry.setGeometry(QtCore.QRect(10, 360, 171, 20))
        self.visGroupNameEntry.setObjectName("visGroupNameEntry")
        self.assignVisGroup = QtWidgets.QPushButton(self.tab_4)
        self.assignVisGroup.setGeometry(QtCore.QRect(280, 360, 151, 23))
        self.assignVisGroup.setObjectName("assignVisGroup")
        self.label_3 = QtWidgets.QLabel(self.tab_4)
        self.label_3.setGeometry(QtCore.QRect(11, 340, 251, 16))
        self.label_3.setObjectName("label_3")
        self.groupLevel = QtWidgets.QSpinBox(self.tab_4)
        self.groupLevel.setGeometry(QtCore.QRect(230, 360, 41, 21))
        self.groupLevel.setMinimum(1)
        self.groupLevel.setObjectName("groupLevel")
        self.label_4 = QtWidgets.QLabel(self.tab_4)
        self.label_4.setGeometry(QtCore.QRect(194, 362, 31, 16))
        self.label_4.setObjectName("label_4")
        self.tabWidget.addTab(self.tab_4, "")
        self.tab_5 = QtWidgets.QWidget()
        self.tab_5.setObjectName("tab_5")
        self.tabWidget.addTab(self.tab_5, "")
        self.horizontalLayout.addWidget(self.tabWidget)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1234, 21))
        self.menubar.setObjectName("menubar")
        self.menuTools = QtWidgets.QMenu(self.menubar)
        self.menuTools.setObjectName("menuTools")
        self.menuVisibility = QtWidgets.QMenu(self.menuTools)
        self.menuVisibility.setObjectName("menuVisibility")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.actionCard_Orients = QtWidgets.QAction(MainWindow)
        self.actionCard_Orients.setCheckable(True)
        self.actionCard_Orients.setObjectName("actionCard_Orients")
        self.actionReconnect_Real_Joints = QtWidgets.QAction(MainWindow)
        self.actionReconnect_Real_Joints.setObjectName("actionReconnect_Real_Joints")
        self.actionCard_Orients_2 = QtWidgets.QAction(MainWindow)
        self.actionCard_Orients_2.setObjectName("actionCard_Orients_2")
        self.actionConnectors = QtWidgets.QAction(MainWindow)
        self.actionConnectors.setObjectName("actionConnectors")
        self.actionHandles = QtWidgets.QAction(MainWindow)
        self.actionHandles.setObjectName("actionHandles")
        self.actionMatch_Selected_Orients = QtWidgets.QAction(MainWindow)
        self.actionMatch_Selected_Orients.setObjectName("actionMatch_Selected_Orients")
        self.menuVisibility.addAction(self.actionCard_Orients_2)
        self.menuVisibility.addAction(self.actionConnectors)
        self.menuVisibility.addAction(self.actionHandles)
        self.menuTools.addAction(self.actionReconnect_Real_Joints)
        self.menuTools.addAction(self.menuVisibility.menuAction())
        self.menuTools.addAction(self.actionMatch_Selected_Orients)
        self.menubar.addAction(self.menuTools.menuAction())

        self.retranslateUi(MainWindow)
        self.tabWidget.setCurrentIndex(2)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QtWidgets.QApplication.translate("MainWindow", "MainWindow", None, -1))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab), QtWidgets.QApplication.translate("MainWindow", "Start", None, -1))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_2), QtWidgets.QApplication.translate("MainWindow", "Util", None, -1))
        self.makeCardBtn.setText(QtWidgets.QApplication.translate("MainWindow", "Make Card", None, -1))
        self.selectAllBtn.setText(QtWidgets.QApplication.translate("MainWindow", "Select All", None, -1))
        self.deleteBonesBtn.setText(QtWidgets.QApplication.translate("MainWindow", "Delete Bones", None, -1))
        self.buildBonesBtn.setText(QtWidgets.QApplication.translate("MainWindow", "Build Bones", None, -1))
        self.saveModsBtn.setText(QtWidgets.QApplication.translate("MainWindow", "Save Mods", None, -1))
        self.buildRigBtn.setText(QtWidgets.QApplication.translate("MainWindow", "Build Rig", None, -1))
        self.restoreModsBtn.setText(QtWidgets.QApplication.translate("MainWindow", "Restore Mods", None, -1))
        self.deleteRigBtn.setText(QtWidgets.QApplication.translate("MainWindow", "Delete Rig", None, -1))
        self.rebuildProxyBtn.setText(QtWidgets.QApplication.translate("MainWindow", "Rebuild Proxy", None, -1))
        self.cardLister.headerItem().setText(0, QtWidgets.QApplication.translate("MainWindow", "Name", None, -1))
        self.cardLister.headerItem().setText(1, QtWidgets.QApplication.translate("MainWindow", "Vis", None, -1))
        self.cardLister.headerItem().setText(2, QtWidgets.QApplication.translate("MainWindow", "Type", None, -1))
        self.cardLister.headerItem().setText(3, QtWidgets.QApplication.translate("MainWindow", "Start", None, -1))
        self.cardLister.headerItem().setText(4, QtWidgets.QApplication.translate("MainWindow", "Repeat", None, -1))
        self.cardLister.headerItem().setText(5, QtWidgets.QApplication.translate("MainWindow", "End", None, -1))
        self.cardLister.headerItem().setText(6, QtWidgets.QApplication.translate("MainWindow", "Mirror", None, -1))
        self.cardLister.headerItem().setText(7, QtWidgets.QApplication.translate("MainWindow", "Side", None, -1))
        self.duplicateCardBtn.setText(QtWidgets.QApplication.translate("MainWindow", "Duplicate", None, -1))
        self.insertJointBtn.setText(QtWidgets.QApplication.translate("MainWindow", "Insert", None, -1))
        self.addTipBtn.setText(QtWidgets.QApplication.translate("MainWindow", "Add Tip", None, -1))
        self.deleteJointBtn.setText(QtWidgets.QApplication.translate("MainWindow", "Delete", None, -1))
        self.mergeCardBtn.setText(QtWidgets.QApplication.translate("MainWindow", "Merge", None, -1))
        self.splitCardBtn.setText(QtWidgets.QApplication.translate("MainWindow", "Split", None, -1))
        self.pushButton_15.setText(QtWidgets.QApplication.translate("MainWindow", "Add Card Ik", None, -1))
        self.pushButton_16.setText(QtWidgets.QApplication.translate("MainWindow", "Rem Card Ik", None, -1))
        self.label.setText(QtWidgets.QApplication.translate("MainWindow", "Cards", None, -1))
        self.label_2.setText(QtWidgets.QApplication.translate("MainWindow", "Joints", None, -1))
        self.jointLister.horizontalHeaderItem(0).setText(QtWidgets.QApplication.translate("MainWindow", "Name", None, -1))
        self.jointLister.horizontalHeaderItem(1).setText(QtWidgets.QApplication.translate("MainWindow", "Helper", None, -1))
        self.jointLister.horizontalHeaderItem(2).setText(QtWidgets.QApplication.translate("MainWindow", "Output", None, -1))
        self.jointLister.horizontalHeaderItem(3).setText(QtWidgets.QApplication.translate("MainWindow", "Handles", None, -1))
        self.jointLister.horizontalHeaderItem(4).setText(QtWidgets.QApplication.translate("MainWindow", "Orient To", None, -1))
        self.jointLister.horizontalHeaderItem(5).setText(QtWidgets.QApplication.translate("MainWindow", "Child Of", None, -1))
        self.cardParams.horizontalHeaderItem(0).setText(QtWidgets.QApplication.translate("MainWindow", "1", None, -1))
        self.cardParams.horizontalHeaderItem(1).setText(QtWidgets.QApplication.translate("MainWindow", "2", None, -1))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_3), QtWidgets.QApplication.translate("MainWindow", "Editor", None, -1))
        self.equipVisControl.setText(QtWidgets.QApplication.translate("MainWindow", "Equip Vis Control", None, -1))
        self.unequipVisControl.setText(QtWidgets.QApplication.translate("MainWindow", "Unequip Vis Control", None, -1))
        self.pruneVisGroups.setText(QtWidgets.QApplication.translate("MainWindow", "Prune Unused Vis Groups", None, -1))
        self.assignVisGroup.setText(QtWidgets.QApplication.translate("MainWindow", "Assign", None, -1))
        self.label_3.setText(QtWidgets.QApplication.translate("MainWindow", "Assign to Group", None, -1))
        self.label_4.setText(QtWidgets.QApplication.translate("MainWindow", "Level", None, -1))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_4), QtWidgets.QApplication.translate("MainWindow", "Vis Groups", None, -1))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_5), QtWidgets.QApplication.translate("MainWindow", "Space", None, -1))
        self.menuTools.setTitle(QtWidgets.QApplication.translate("MainWindow", "Tools", None, -1))
        self.menuVisibility.setTitle(QtWidgets.QApplication.translate("MainWindow", "Visibility", None, -1))
        self.actionCard_Orients.setText(QtWidgets.QApplication.translate("MainWindow", "Card Orients", None, -1))
        self.actionReconnect_Real_Joints.setText(QtWidgets.QApplication.translate("MainWindow", "Reconnect Real Joints", None, -1))
        self.actionCard_Orients_2.setText(QtWidgets.QApplication.translate("MainWindow", "Card Orients", None, -1))
        self.actionConnectors.setText(QtWidgets.QApplication.translate("MainWindow", "Connectors", None, -1))
        self.actionHandles.setText(QtWidgets.QApplication.translate("MainWindow", "Handles", None, -1))
        self.actionMatch_Selected_Orients.setText(QtWidgets.QApplication.translate("MainWindow", "Match Selected Orients", None, -1))

from motiga.tool.fossil.cardlister import CardLister
from motiga.tool.fossil.jointlister import JointLister
from motiga.tool.fossil.cardparams import CardParams
