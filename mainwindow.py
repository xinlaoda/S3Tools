# This Python file uses the following encoding: utf-8
import os
from pathlib import Path
import sys
from enum import Enum

import boto3.resources.model
from PySide6.QtWidgets import QApplication, QMainWindow, QAbstractItemView, QStyle, QFileDialog, \
    QHeaderView, QInputDialog, QMessageBox, QCheckBox
from PySide6.QtCore import QFile, QFileInfo
from PySide6.QtUiTools import QUiLoader

import S3Bucket
import S3Object
import S3Tasks
from NewBucketDialog import NewBucketDialog

class TabIndex(Enum):
    PropertiesTabIndex = 0
    TasksTabIndex = 1

class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.currentBucket = ""
        self.objPrefix = []
        self.load_ui()
        self.set_bucket_list()
        self.set_object_list()
        self.set_tab_list()
        self.setup_ui()
        self.connect_action()

    def load_ui(self):
        loader = QUiLoader()
        path = os.fspath(Path(__file__).resolve().parent / "form.ui")
        ui_file = QFile(path)
        ui_file.open(QFile.ReadOnly)
        self.window = loader.load(ui_file, self)
        ui_file.close()

    def setup_ui(self):
        self.window.btnPathUp.setIcon(self.style().standardIcon(QStyle.SP_FileDialogToParent))
        self.window.S3ObjPath.setReadOnly(True)
        self.window.btnAddBucket.setIcon(self.style().standardIcon(QStyle.SP_FileDialogNewFolder))
        self.window.btnDelBucket.setIcon(self.style().standardIcon(QStyle.SP_BrowserStop))
        self.window.btnRefleshBucket.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        self.window.btnNewObjFolder.setIcon(self.style().standardIcon(QStyle.SP_FileDialogNewFolder))
        self.window.btnDelObject.setIcon(self.style().standardIcon(QStyle.SP_BrowserStop))
        self.window.btnRefleshObj.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        self.window.btnUploadObject.setIcon(self.style().standardIcon(QStyle.SP_ArrowUp))
        self.window.btnDownloadObject.setIcon(self.style().standardIcon(QStyle.SP_ArrowDown))

    def set_bucket_list(self):
        self.btnBucketRefleshClick()

    def set_object_list(self):
        self.window.ObjtableView.setModel(S3Object.ObjectsModel)
        self.window.ObjtableView.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.window.ObjtableView.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

    def set_tab_list(self):
        self.window.PropertiesTableView.setModel(S3Object.ObjectsPropertiesModel)
        self.window.PropertiesTableView.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

        # Tasks list
        self.window.TaskListView.setModel(S3Tasks.TasksModel)
        S3Tasks.TasksModel.setHorizontalHeaderLabels(["Task", "Size", "%", "Progress", "Status", "Speed"])
        self.window.TaskListView.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        task_progress_delegate = S3Tasks.ProgressDelegate(self.window.TaskListView)
        self.window.TaskListView.setItemDelegateForColumn(3, task_progress_delegate)
        # S3Tasks.update_tasks()


    def connect_action(self):
        self.window.btnRefleshBucket.clicked.connect(self.btnBucketRefleshClick)
        self.window.BucketlistView.clicked.connect(self.BucketListClick)
        self.window.btnDelBucket.clicked.connect(self.BucketDeleteClick)
        self.window.btnAddBucket.clicked.connect(self.BucketNewClick)
        self.window.ObjtableView.doubleClicked.connect(self.ObjListDoubleClick)
        self.window.ObjtableView.clicked.connect(self.ObjListClick)
        self.window.btnPathUp.clicked.connect(self.PathUpClick)
        self.window.btnUploadObject.clicked.connect(self.UploadClick)
        self.window.btnRefleshObj.clicked.connect(self.ObjRefreshClick)
        self.window.btnDelObject.clicked.connect(self.ObjDeleteClick)
        self.window.btnDownloadObject.clicked.connect(self.ObjDownloadClick)
        self.window.btnNewObjFolder.clicked.connect(self.NewObjFolderClick)

    # actions
    def btnBucketRefleshClick(self):
        self.window.BucketlistView.setModel(S3Bucket.list_bucket_with_icon(self.style()))

    def BucketListClick(self, index):
        self.currentBucket = index.data()
        self.window.S3ObjPath.setText("")
        self.objPrefix = []
        S3Object.update_objects_model(index.data(), self.style())
        self.window.btnUploadObject.setEnabled(True)
        self.window.btnRefleshObj.setEnabled(True)
        self.window.btnNewObjFolder.setEnabled(True)
        self.window.btnDelBucket.setEnabled(True)

    def BucketDeleteClick(self):
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Critical)
        delButton = msgBox.addButton("Delete Bucket", QMessageBox.YesRole)
        delButton.setEnabled(False)
        msgBox.addButton("Cancel", QMessageBox.NoRole)
        msgBox.setText("Delete Bucket: {0}".format(self.currentBucket))
        msgBox.setInformativeText("Delete bucket will delete all objects in this bucket!")
        cb = QCheckBox("I confirm permanent deletion of the bucket")
        msgBox.setCheckBox(cb)
        cb.stateChanged.connect(lambda state: delButton.setEnabled(state))
        msgBox.exec()
        if (msgBox.clickedButton() == delButton):
            S3Bucket.delete_bucket(self.currentBucket)
            self.btnBucketRefleshClick()
            self.currentBucket = ""
            self.ObjRefreshClick()

    def BucketNewClick(self):
        newBucketDlg = NewBucketDialog()
        if newBucketDlg.exec_():
            bucket, region = newBucketDlg.get_select_bucket_region()
            S3Bucket.new_bucket(bucket, region)
            self.btnBucketRefleshClick()
        else:
            print("Cancel")

    def ObjListDoubleClick(self, index):
        model = index.model()
        name_index = index.siblingAtColumn(0)
        pathName = model.data(name_index)
        if pathName.find('/') != -1:
            currentPath = self.window.S3ObjPath.text()
            prefix = currentPath + pathName
            self.objPrefix.append(pathName)
            self.window.S3ObjPath.setText(prefix)
            S3Object.update_objects_model(self.currentBucket, self.style(), Delimiter='', Prefix=prefix)

    def ObjListClick(self, index):
        self.window.btnDelObject.setEnabled(True)
        self.window.btnDownloadObject.setEnabled(True)
        model = index.model()
        name_index = index.siblingAtColumn(0)
        obj_key = model.data(name_index)
        # if obj_key.find('/') == -1:
        self.window.tabWidget.setCurrentIndex(TabIndex.PropertiesTabIndex.value)
        obj_key_full = self.window.S3ObjPath.text() + obj_key
        S3Object.update_object_properties_model(self.currentBucket, obj_key, obj_key_full)

    def PathUpClick(self):
        curPath = self.window.S3ObjPath.text()
        upPath = "".join(self.objPrefix[0:len(self.objPrefix)-1])
        self.objPrefix = self.objPrefix[0:-1]
        self.window.S3ObjPath.setText(upPath)
        S3Object.update_objects_model(self.currentBucket, self.style(), Delimiter='', Prefix=upPath)

    def UploadClick(self):
        fileName = QFileDialog.getOpenFileName(self, caption="Upload file", dir=".", filter="All Files (*.*)")
        if not fileName[0] == "":
            # Upload file
            fileInfo = QFileInfo(fileName[0])
            file = fileInfo.fileName()
            size = fileInfo.size()
            prefix = self.window.S3ObjPath.text()
            key = prefix + file
            S3Tasks.upload_file(self.currentBucket, key, fileName[0], size)

    def ObjRefreshClick(self):
        obj_key_full = self.window.S3ObjPath.text()
        S3Object.update_objects_model(self.currentBucket, self.style(), Delimiter='', Prefix=obj_key_full)

    def ObjDeleteClick(self):
        model = self.window.ObjtableView.selectionModel()
        indexes = model.selectedRows()
        for index in indexes:
            S3Object.delete_object_with_item(index)

    def ObjDownloadClick(self):
        download_dir = QFileDialog.getExistingDirectory(self, caption="Download File to ",
                                                   options=QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks)
        if "" != download_dir:
            self.window.tabWidget.setCurrentIndex(TabIndex.TasksTabIndex.value)
            model = self.window.ObjtableView.selectionModel()
            indexes = model.selectedRows()
            S3Object.download_objects_from_indexes(indexes, download_dir)

    def NewObjFolderClick(self):
        prefix = self.window.S3ObjPath.text()
        dir, ok = QInputDialog.getText(self, "Create Folder", "Folder Name: " )
        if ok and "" != dir:
            S3Object.create_folder(self.currentBucket, prefix, dir)
            self.ObjRefreshClick()

if __name__ == "__main__":
    app = QApplication([])
    mainWindow = MainWindow()
    mainWindow.window.show()
    app.setQuitOnLastWindowClosed(False)
    sys.exit(app.exec())
