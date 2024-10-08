import os
import pkgutil

from PySide6.QtCore import Signal, QDataStream, QByteArray, QObject, QDir
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QFileDialog, QLineEdit
from PySide6.QtUiTools import QUiLoader

from pupgui2.util import config_custom_install_location, get_install_location_from_directory_name, get_dict_key_from_value, get_combobox_index_by_value
from pupgui2.constants import HOME_DIR


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
            'bottles': 'Bottles',
            'winezgui': 'WineZGUI',
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

        self.ui.txtInstallDirectory.textChanged.connect(lambda text: self.ui.btnSave.setEnabled(self.is_valid_custom_install_path(text)))
        custom_install_directory = config_custom_install_location().get('install_dir', '')
        self.ui.txtInstallDirectory.setText(custom_install_directory)
        self.ui.btnDefault.setEnabled(self.has_custom_install_directory(custom_install_directory))  # Don't enable btnDefault if there is no Custom Install Directory set

        self.ui.comboLauncher.addItems([
            display_name for display_name in self.install_locations_dict.values()
        ])

        self.set_selected_launcher(self.install_locations_dict[self.launcher] if self.launcher in self.install_locations_dict else 'steam')  # Default combobox selection to "Steam" if unknown launcher for some reason

        self.ui.btnSave.clicked.connect(self.btn_save_clicked)
        self.ui.btnDefault.clicked.connect(self.btn_default_clicked)
        self.ui.btnClose.clicked.connect(self.ui.close)

    def btn_save_clicked(self):
        install_dir: str = os.path.expanduser(self.ui.txtInstallDirectory.text().strip())
        if not install_dir.endswith(os.sep):
            install_dir += '/'
        launcher = get_dict_key_from_value(self.install_locations_dict, self.ui.comboLauncher.currentText()) or ''

        if self.is_valid_custom_install_path(install_dir):
            config_custom_install_location(install_dir, launcher)

        self.custom_id_set.emit(install_dir)
        self.ui.close()

    def btn_default_clicked(self):
        self.ui.txtInstallDirectory.setText('')

        custom_install_directory = config_custom_install_location(remove=True).get('install_dir', '')
        self.ui.btnDefault.setEnabled(self.has_custom_install_directory(custom_install_directory))

        self.custom_id_set.emit('')

    def txt_id_browse_action_triggered(self):
        # Open dialog at entered path if it exists, and fall back to HOME_DIR
        txt_install_dir: str = os.path.expanduser(self.ui.txtInstallDirectory.text())
        initial_dir = txt_install_dir if self.is_valid_custom_install_path(txt_install_dir) else HOME_DIR

        dialog = QFileDialog(self.ui, directory=initial_dir)
        dialog.setFileMode(QFileDialog.Directory)
        dialog.setOption(QFileDialog.ShowDirsOnly)
        dialog.setFilter(QDir.Dirs | QDir.Hidden | QDir.NoDotAndDotDot)
        dialog.setWindowTitle(self.tr('Select Custom Install Directory — ProtonUp-Qt'))
        dialog.fileSelected.connect(self.ui.txtInstallDirectory.setText)
        dialog.open()

    def set_selected_launcher(self, ctool_name: str):
        if not ctool_name:
            return

        if (index := get_combobox_index_by_value(self.ui.comboLauncher, ctool_name)) >= 0:
            self.ui.comboLauncher.setCurrentIndex(index)

    def is_valid_custom_install_path(self, path: str) -> bool:
        expand_path = os.path.expanduser(path)
        return len(path.strip()) > 0 and os.path.isdir(expand_path) and os.access(expand_path, os.W_OK)

    def has_custom_install_directory(self, custom_install_directory: str = '') -> bool:

        """
        Returns whether a Custom Install Directory is set to a Truthy value.
        If `custom_install_directory` is not passed, it will be retrieved.

        Return Type: bool
        """

        if not custom_install_directory:
            return bool(config_custom_install_location().get('install_dir', ''))

        return bool(custom_install_directory)
