import threading
import sys
import boto3
from PySide6.QtGui import QStandardItemModel, QStandardItem, QIcon
from PySide6.QtCore import QObject, Signal, Slot, Qt, QSize
from PySide6.QtWidgets import QStyledItemDelegate, QStyleOptionProgressBar, QApplication, QStyle
from datetime import datetime
import S3Object

TasksModel = QStandardItemModel(0, 6)
Tasks = {}
s3 = boto3.client('s3')

def update_tasks():
    # TasksModel.setHorizontalHeaderLabels(["Task", "Size", "%", "Progress", "Status", "Speed"])
    TasksModel.setRowCount(0)
    for task in Tasks.values():
        item_task = QStandardItem(task["Task"])
        item_size = QStandardItem(task["Size"])
        item_p = QStandardItem(task["%"])
        item_progress = QStandardItem()
        item_progress.setData(task["Progress"], Qt.UserRole+1000)
        item_status = QStandardItem(task["Status"])
        item_speed = QStandardItem(task["Speed"])
        TasksModel.appendRow([item_task, item_size, item_p,
                              item_progress, item_status, item_speed])


def add_upload_task(task):
    i = TasksModel.rowCount()
    item_task = QStandardItem(task["Task"])
    item_size = QStandardItem(task["Size"])
    item_p = QStandardItem(task["%"])
    item_progress = QStandardItem(task["Progress"])
    item_status = QStandardItem(task["Status"])
    item_speed = QStandardItem(task["Speed"])
    TasksModel.setItem(i, 0, item_task)
    TasksModel.setItem(i, 1, item_size)
    TasksModel.setItem(i, 2, item_p)
    TasksModel.setItem(i, 3, item_progress)
    TasksModel.setItem(i, 4, item_status)
    TasksModel.setItem(i, 5, item_speed)
    index_p = item_p.index()
    index_progress = item_progress.index()
    return index_p, index_progress


def upload_file(bucket, key, file, size):
    _task = {
        "Task": key,
        "Size": str(size),
        "%": 0,
        "Progress": 0,
        "Status": "Started",
        "Speed": ""
    }
    Tasks[file] = _task
    transfer_callback = TransferCallback(file, size)
    transfer_callback.task_percentageChanged.connect(on_update, type=Qt.QueuedConnection)
    transfer_callback.task_finished.connect(on_finished, type=Qt.QueuedConnection)
    threading.Thread(target=_upload, args=(transfer_callback, bucket, key, file, size)).start()


def _upload(transfer_callback, bucket, key, file, size):
    transfer_callback.task_started.emit()
    s3.upload_file(file, bucket, key, Callback=transfer_callback)
    transfer_callback.task_finished.emit(file)

def download_file(currentBucket, obj_key, dir, file_name, obj_size):
    _task = {
        "Task": obj_key,
        "Size": str(obj_size),
        "%": 0,
        "Progress": 0,
        "Status": "Started",
        "Speed": ""
    }
    Tasks[obj_key] = _task
    transfer_callback = TransferCallback(obj_key, obj_size)
    transfer_callback.task_percentageChanged.connect(on_update, type=Qt.QueuedConnection)
    transfer_callback.task_finished.connect(on_finished, type=Qt.QueuedConnection)
    threading.Thread(target=_download, args=(transfer_callback, currentBucket,
                                             obj_key, dir, file_name, obj_size)).start()

def _download(transfer_callback, currentBucket, obj_key, dir, file_name, obj_size):
    transfer_callback.task_started.emit()
    s3.download_file(currentBucket, obj_key, dir+'/'+file_name, Callback=transfer_callback)
    transfer_callback.task_finished.emit(obj_key)

@Slot()
def on_update():
    update_tasks()

@Slot()
def on_finished(file):
    Tasks[file]["Status"] = "Completed"
    update_tasks()
    S3Object.update_objects_listview()

class TransferCallback(QObject):
    task_started = Signal()
    task_finished = Signal(str)
    task_percentageChanged = Signal()

    def __init__(self, target_file, target_size, parent=None):
        super().__init__(parent)
        self.__target_size = target_size
        self.__target_file = target_file
        self._total_transferred = 0
        self.__start_time = datetime.now()
        self._lock = threading.Lock()
        self.thread_info = {}

    def __call__(self, bytes_transferred):
        thread = threading.current_thread()
        with self._lock:
            cur_time = datetime.now()
            interval_time = (cur_time - self.__start_time).seconds
            self._total_transferred += bytes_transferred
            if 0 != interval_time:
                speed = self._total_transferred / interval_time
                Tasks[self.__target_file]["Speed"] = f"{(speed / 1024):.2f}KB/s"
            if thread.ident not in self.thread_info.keys():
                self.thread_info[thread.ident] = bytes_transferred
            else:
                self.thread_info[thread.ident] += bytes_transferred
            target = self.__target_size
            Tasks[self.__target_file]["%"] = f"{(self._total_transferred / target) * 100:.2f}%"
            Tasks[self.__target_file]["Progress"] = int(self._total_transferred / target * 100)
            self.task_percentageChanged.emit()

class ProgressDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        progress = index.data(Qt.UserRole + 1000)
        if index.column() == 3 and progress != None:
            opt = QStyleOptionProgressBar()
            opt.rect = option.rect
            opt.minimum = 0
            opt.maximum = 100
            opt.progress = progress
            opt.text = "{}%".format(progress)
            opt.textVisible = True
            painter.save()
            painter.translate(option.rect.topLeft())
            QApplication.style().drawControl(QStyle.CE_ProgressBar, opt, painter)
            painter.restore()
        else:
            QStyledItemDelegate.paint(self, painter, option, index)
