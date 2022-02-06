import logging
import boto3
from PySide6.QtCore import QStringListModel
from PySide6.QtGui import QStandardItemModel, QStandardItem, QIcon
from  PySide6 import QtGui
from PySide6.QtWidgets import QStyle
from botocore.exceptions import ClientError
import rc_icons

s3 = boto3.client('s3')
ec2 = boto3.client('ec2')

def list_bucket():
    bucketsModel = QStringListModel()
    buckets = []

    response = s3.list_buckets()

    print('Existing buckets:')
    for bucket in response['Buckets']:
        buckets.append(bucket["Name"])

    bucketsModel.setStringList(buckets)
    return bucketsModel

def list_bucket_with_icon(w):
    bucketsModel = QStandardItemModel()
    buckets = []
    response = s3.list_buckets()
    for bucket in response['Buckets']:
        item = QStandardItem(bucket["Name"])
        item.setEditable(False)
        item.setIcon(w.standardIcon(QStyle.SP_DirClosedIcon))
        bucketsModel.appendRow(item)
    return bucketsModel

def get_regions():
    regions = []
    response = ec2.describe_regions()
    if "Regions" in response:
        for r in response["Regions"]:
            regions.append(r["RegionName"])
    return regions

def new_bucket(name, region):
    response = s3.create_bucket(
        Bucket = name,
        CreateBucketConfiguration={
            'LocationConstraint': region
        }
    )
    print(response)


def delete_bucket(bucket):
    print(f"Delete Bucket: {(bucket)}")
    ContinuationToken = ""
    isTruncated = True
    while(isTruncated):
        if ContinuationToken != "":
            response = s3.list_objects_v2(
                Bucket = bucket,
                ContinuationToken = ContinuationToken
            )
        else:
            response = s3.list_objects_v2(
                Bucket=bucket
            )
        isTruncated = response["IsTruncated"]
        if (isTruncated):
            ContinuationToken = response["ContinuationToken"]
        if "Contents" in response:
            obj_keys = []
            contents = response["Contents"]
            for i in contents:
                obj_keys.append({
                    "Key": i["Key"]
                })
            # delete obj
            del_response = s3.delete_objects(
                Bucket = bucket,
                Delete = {
                    'Objects': obj_keys
                }
            )
            if "Errors" in del_response:
                print(del_response["Errors"])
        else:
            # delete bucket
            print("empty bucket, delete it.")
            s3.delete_bucket(Bucket = bucket)

