import os

from PySide6.QtCore import Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDialog, QFileDialog, QLabel, QPushButton, QLineEdit, QComboBox, QFormLayout

from pupgui2.util import config_custom_install_location


class PupguiCustomInstallDirectoryDialog(QDialog):

    custom_id_set = Signal()

    def __init__(self, parent=None):
        super(PupguiCustomInstallDirectoryDialog, self).__init__(parent)

        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle(self.tr('Custom Install Directory'))
        self.setModal(True)
        self.setMinimumSize(320, 120)

        formLayout = QFormLayout()
        self.txtInstallDirectory = QLineEdit()
        self.txtIdBrowseAction = self.txtInstallDirectory.addAction(QIcon.fromTheme('document-open'), QLineEdit.TrailingPosition)
        self.txtIdBrowseAction.triggered.connect(self.txt_id_browse_action_triggered)
        self.comboLauncher = QComboBox()
        self.btnSave = QPushButton(self.tr('Save'))
        formLayout.addRow(QLabel(self.tr('Directory:')), self.txtInstallDirectory)
        formLayout.addRow(QLabel(self.tr('Launcher:')), self.comboLauncher)
        formLayout.addWidget(self.btnSave)
        self.setLayout(formLayout)

        self.txtInstallDirectory.textChanged.connect(self.txt_install_directory_text_changed)
        self.comboLauncher.addItems([
            'steam',
            'lutris',
            'heroicwine',
            'heroicproton',
            'bottles'
            ])
        self.btnSave.clicked.connect(self.btn_save_clicked)

        self.show()

    def txt_install_directory_text_changed(self, text):
        if text.strip() == '':
            self.btnSave.setText(self.tr('Reset'))
        else:
            self.btnSave.setText(self.tr('Save'))

    def btn_save_clicked(self):
        install_dir = self.txtInstallDirectory.text().strip()
        launcher = self.comboLauncher.currentText()

        if install_dir == '':
            config_custom_install_location(install_dir='remove')
            print('custom install directory: removed')

        if os.path.exists(install_dir):
            config_custom_install_location(install_dir, launcher)
            print('custom install directory: set to', install_dir)

        self.custom_id_set.emit()
        self.close()

    def txt_id_browse_action_triggered(self):
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.Directory)
        dialog.setOption(QFileDialog.ShowDirsOnly)
        dialog.setDirectory(os.path.expanduser('~'))
        dialog.fileSelected.connect(self.txtInstallDirectory.setText)
        dialog.open()
