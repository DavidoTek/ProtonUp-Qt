import os
import pkgutil

from PySide6.QtCore import Signal, QDataStream, QByteArray, QObject
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QFileDialog, QLineEdit
from PySide6.QtUiTools import QUiLoader

from pupgui2.util import config_custom_install_location, get_install_location_from_directory_name, get_dict_key_from_value, get_combobox_index_by_value


class PupguiCustomInstallDirectoryDialog(QObject):

    custom_id_set = Signal(str)

    def __init__(self, install_dir, parent=None):
        super(PupguiCustomInstallDirectoryDialog, self).__init__(parent)

        self.install_loc = get_install_location_from_directory_name(install_dir)
        self.launcher = self.install_loc.get('launcher', '')

        self.install_locations_dict = {
            'steam': 'Steam',
            'lutris': 'Lutris',
            'heroicwine': 'Heroic (Wine)',
            'heroicproton': 'Heroic (Proton)',
            'bottles': 'Bottles'
        }

        self.load_ui()
        self.setup_ui()
        self.ui.show()

    def load_ui(self):
        data = pkgutil.get_data(__name__, 'resources/ui/pupgui2_custominstalldirectorydialog.ui')
        ui_file = QDataStream(QByteArray(data))
        loader = QUiLoader()
        self.ui = loader.load(ui_file.device())

    def setup_ui(self):
        self.ui.setWindowTitle(self.tr('Custom Install Directory'))

        self.txtIdBrowseAction = self.ui.txtInstallDirectory.addAction(QIcon.fromTheme('document-open'), QLineEdit.TrailingPosition)
        self.txtIdBrowseAction.triggered.connect(self.txt_id_browse_action_triggered)

        self.ui.txtInstallDirectory.setText(config_custom_install_location().get('install_dir', ''))

        self.ui.comboLauncher.addItems([
            display_name for display_name in self.install_locations_dict.values()
        ])

        self.set_selected_launcher(self.install_locations_dict[self.launcher] or 'steam')  # Default combobox selection to "Steam" if unknown launcher for some reason

        self.ui.btnSave.clicked.connect(self.btn_save_clicked)
        self.ui.btnDefault.clicked.connect(self.btn_default_clicked)
        self.ui.btnClose.clicked.connect(self.ui.close)

        self.is_valid_custom_install_path = lambda path: len(path.strip()) > 0 and os.path.isdir(os.path.expanduser(path)) and os.access(os.path.expanduser(path), os.W_OK)
        self.ui.txtInstallDirectory.textChanged.connect(lambda text: self.ui.btnSave.setEnabled(self.is_valid_custom_install_path(text)))

    def btn_save_clicked(self):
        install_dir = os.path.expanduser(self.ui.txtInstallDirectory.text().strip())
        if not install_dir.endswith(os.sep):
            install_dir += '/'
        launcher = get_dict_key_from_value(self.install_locations_dict, self.ui.comboLauncher.currentText()) or ''

        if self.is_valid_custom_install_path(install_dir):
            config_custom_install_location(install_dir, launcher)
            print(f'New Custom Install Directory set to: {install_dir}')

        self.custom_id_set.emit(install_dir)
        self.ui.close()

    def btn_default_clicked(self):
        self.ui.txtInstallDirectory.setText('')
        config_custom_install_location(remove=True)
        print(f'Removed custom install directory')

        self.custom_id_set.emit('')

    def txt_id_browse_action_triggered(self):
        dialog = QFileDialog(self.ui)
        dialog.setFileMode(QFileDialog.Directory)
        dialog.setOption(QFileDialog.ShowDirsOnly)
        dialog.setWindowTitle(self.tr('Select Custom Install Directory — ProtonUp-Qt'))
        dialog.setDirectory(os.path.expanduser('~'))
        dialog.fileSelected.connect(self.ui.txtInstallDirectory.setText)
        dialog.open()

    def set_selected_launcher(self, ctool_name: str):
        if ctool_name:
            index = get_combobox_index_by_value(self.ui.comboLauncher, ctool_name)
            if index >= 0:
                self.ui.comboLauncher.setCurrentIndex(index)