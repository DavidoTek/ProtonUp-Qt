import os
import pkgutil

from PySide6.QtCore import Signal, QDataStream, QByteArray, QObject
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QFileDialog, QLabel, QPushButton, QLineEdit, QComboBox, QFormLayout
from PySide6.QtUiTools import QUiLoader

from pupgui2.util import config_custom_install_location


class PupguiCustomInstallDirectoryDialog(QObject):

    custom_id_set = Signal()

    def __init__(self, parent=None):
        super(PupguiCustomInstallDirectoryDialog, self).__init__(parent)

        self.load_ui()
        self.setup_ui()
        self.ui.show()

        self.ui.setFixedSize(self.ui.size())

    def load_ui(self):
        data = pkgutil.get_data(__name__, 'resources/ui/pupgui2_custominstalldirectorydialog.ui')
        ui_file = QDataStream(QByteArray(data))
        loader = QUiLoader()
        self.ui = loader.load(ui_file.device())

    def setup_ui(self):
        self.ui.setWindowTitle(self.tr('Custom Install Directory'))

        self.txtIdBrowseAction = self.ui.txtInstallDirectory.addAction(QIcon.fromTheme('document-open'), QLineEdit.TrailingPosition)
        self.txtIdBrowseAction.triggered.connect(self.txt_id_browse_action_triggered)

        self.ui.comboLauncher.addItems([
            'steam',
            'lutris',
            'heroicwine',
            'heroicproton',
            'bottles'
        ])

        self.ui.btnSave.clicked.connect(self.btn_save_clicked)
        self.ui.btnDefault.clicked.connect(self.btn_default_clicked)
        self.ui.btnCancel.clicked.connect(self.ui.close)

        self.is_valid_custom_install_path = lambda path: len(path.strip()) > 0 and os.path.isdir(path) and os.access(path, os.W_OK)  # Maybe too expensive?
        self.ui.txtInstallDirectory.textChanged.connect(lambda text: self.ui.btnSave.setEnabled(self.is_valid_custom_install_path(text)))

    def btn_save_clicked(self):
        install_dir = self.ui.txtInstallDirectory.text().strip()
        launcher = self.ui.comboLauncher.currentText()

        if self.is_valid_custom_install_path(install_dir):
            config_custom_install_location(install_dir, launcher)
            print(f'New Custom Install Directory set to: {install_dir}')

        self.custom_id_set.emit()
        self.ui.close()

    def btn_default_clicked(self):
        config_custom_install_location(install_dir='remove')
        print('custom install directory: removed')

    def txt_id_browse_action_triggered(self):
        dialog = QFileDialog(self.ui)
        dialog.setFileMode(QFileDialog.Directory)
        dialog.setOption(QFileDialog.ShowDirsOnly)
        dialog.setDirectory(os.path.expanduser('~'))
        dialog.fileSelected.connect(self.ui.txtInstallDirectory.setText)
        dialog.open()
