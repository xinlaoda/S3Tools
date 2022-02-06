from PySide6.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout, QLabel, QWidget, \
    QLineEdit, QHBoxLayout, QComboBox

import S3Bucket


class NewBucketDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("New Bucket")
        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.layout = QVBoxLayout()

        nameWidget = QWidget()
        nameLabel = QLabel("Bucket Name: ")
        self.nameInput = QLineEdit()
        nameLayout = QHBoxLayout()
        nameLayout.addWidget(nameLabel)
        nameLayout.addWidget(self.nameInput)
        nameWidget.setLayout(nameLayout)

        regionWidget = QWidget()
        regionLable = QLabel("Region: ")
        self.regionSelect = QComboBox()
        regionLayout = QHBoxLayout()
        regionLayout.addWidget(regionLable)
        regionLayout.addWidget(self.regionSelect)
        regionWidget.setLayout(regionLayout)
        regions = S3Bucket.get_regions()
        for r in regions:
            self.regionSelect.addItem(r)

        self.layout.addWidget(nameWidget)
        self.layout.addWidget(regionWidget)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)

    def get_select_bucket_region(self):
        return self.nameInput.text(), self.regionSelect.currentText()