import boto3
from PySide6.QtCore import QStringListModel
from PySide6.QtGui import QStandardItemModel, QStandardItem, QIcon
from dateutil.tz import tzutc
import datetime
from PySide6.QtWidgets import QStyle, QCommonStyle, QMessageBox

import S3Object
import S3Tasks

ObjectsModel = QStandardItemModel()
ObjectsPropertiesModel = QStandardItemModel()
currentObjectList = {}
currentBucket = ""
currentPrefix = ""
style = QCommonStyle()

SIZE_UNIT = [" KB", " MB", " GB", " TB"]
SIZE_POWER = 1024

s3 = boto3.client('s3')

def list_objects(bucketName, Delimiter="", Prefix=""):
    objlist = {}
    if "" == bucketName:
        return objlist
    response = s3.list_objects(Bucket=bucketName, Delimiter=Delimiter, Prefix=Prefix)
    if "Contents" in response:
        for obj in response['Contents']:
            key = obj['Key']

            if "" != Prefix:
                _, _, key = key.partition(Prefix)

            if "" == key:
                continue
            if (-1 == key.find('/')):
                obj["Type"] = "File"
                obj["Key"] = key
                objlist[key] = obj
            else:
                d = key.split("/", 1)[0] + "/"
                o = {
                    "Key": d,
                    "Type": "Dir",
                }
                if d not in objlist:
                    objlist[d] =  o
    S3Object.currentObjectList = objlist
    return objlist

def update_objects_listview():
    if "" != S3Object.currentBucket:
        update_objects_model(S3Object.currentBucket, S3Object.style, Delimiter="", Prefix=S3Object.currentPrefix)

def update_objects_model(bucketName, w, Delimiter="", Prefix=""):
    S3Object.currentBucket = bucketName
    S3Object.style = w
    S3Object.currentPrefix = Prefix
    objlist = list_objects(bucketName, Delimiter=Delimiter, Prefix=Prefix)
    ObjectsModel.setRowCount(len(objlist))
    ObjectsModel.setColumnCount(5)
    ObjectsModel.setHorizontalHeaderLabels(["Name", "Size", "Type", "Last Modified", "Storage Type"])

    i = 0
    for obj in objlist.values():
        item_name = QStandardItem(obj["Key"])
        ObjectsModel.setItem(i, 0, item_name)
        item_name.setEditable(False)
        if -1 != obj["Key"].find('/'):
            item_name.setIcon(w.standardIcon(QStyle.SP_DirIcon))
        else:
            item_name.setIcon(w.standardIcon(QStyle.SP_FileIcon))

        if "Size" in obj:
            objSize = obj["Size"]
            objsizestr = str(objSize) + " bytes"
            for unit in SIZE_UNIT:
                if objSize > SIZE_POWER:
                    objSize = objSize / SIZE_POWER
                    objsizestr = "{:.2f}".format(objSize) + unit

            item_size = QStandardItem(objsizestr)
        else:
            item_size = QStandardItem("")
        item_size.setEditable(False)
        ObjectsModel.setItem(i, 1, item_size)

        if "Type" in obj:
            item_type = QStandardItem(obj["Type"])
        else:
            item_type = QStandardItem("")
        item_type.setEditable(False)
        ObjectsModel.setItem(i, 2, item_type)

        if "LastModified" in obj:
            dt = obj["LastModified"].strftime("%m/%d/%Y %H:%M:%S")
            item_lastmodified = QStandardItem(dt)
        else:
            item_lastmodified = QStandardItem("")
        item_lastmodified.setEditable(False)
        ObjectsModel.setItem(i, 3, item_lastmodified)

        if "StorageClass" in obj:
            item_storageClass = QStandardItem(obj["StorageClass"])
        else:
            item_storageClass = QStandardItem("")
        item_storageClass.setEditable(False)
        ObjectsModel.setItem(i, 4, item_storageClass)

        i = i+1

def flat_dict(parent,value):
    kv = {}
    if not isinstance(value, dict):
        kv[parent] = value
    else:
        for k, v in value.items():
            if "" == parent:
                newParent = k
            else:
                newParent = parent + "." + k
            if isinstance(v, dict):
                _kv = flat_dict(newParent, v)
                kv.update(_kv)
            else:
                kv[newParent] = v

    return kv

def update_object_properties_model(bucketName, objKey, objFullKey):
    if objKey in S3Object.currentObjectList:
        obj_properties = S3Object.currentObjectList[objKey]
        ObjectsPropertiesModel.setHorizontalHeaderLabels(["Property", "Value"])
        ObjectsPropertiesModel.setColumnCount(2)
        i = 0
        flat_obj_properties = flat_dict("", obj_properties)
        ObjectsPropertiesModel.setRowCount(len(flat_obj_properties))

        for k, v in flat_obj_properties.items():
            if isinstance(v, datetime.datetime):
                v = v.strftime("%m/%d/%Y %H:%M:%S")
            elif isinstance(v, int):
                v = str(v)

            item_k = QStandardItem(k)
            item_k.setEditable(False)
            item_v = QStandardItem(v)
            item_v.setEditable(False)
            ObjectsPropertiesModel.setItem(i, 0, item_k)
            ObjectsPropertiesModel.setItem(i, 1, item_v)
            i = i + 1

def delete_object_with_item(index):
    item = ObjectsModel.itemFromIndex(index)
    obj_name = item.text()
    obj_key = currentPrefix + obj_name
    ret = QMessageBox.warning(None, "Delete Object", "Do you want to delete {0}".format(obj_key),
                              QMessageBox.Yes | QMessageBox.No,
                              QMessageBox.Yes)
    if ret == QMessageBox.Yes:
        print("delete {0}".format(obj_key))
        s3.delete_object(
            Bucket = currentBucket,
            Key = obj_key
        )
    update_objects_listview()

def download_objects_from_indexes(indexes, dir):
    for index in indexes:
        item = ObjectsModel.itemFromIndex(index)
        obj_name = item.text()
        obj_size = int(S3Object.currentObjectList[obj_name]["Size"])
        obj_key = currentPrefix + obj_name
        S3Tasks.download_file(currentBucket, obj_key, dir, obj_name, obj_size)

def create_folder(bucket, prefix, dir):
    if not dir.endswith('/'):
        dir = dir + '/'
    s3.put_object(Body="", Bucket=bucket, Key=prefix+dir)


