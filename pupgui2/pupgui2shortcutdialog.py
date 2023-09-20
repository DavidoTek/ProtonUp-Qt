import os
import pkgutil

from PySide6.QtCore import QObject, Signal, Slot, QDataStream, QByteArray, Qt
from PySide6.QtWidgets import QLineEdit
from PySide6.QtUiTools import QUiLoader

from pupgui2.steamutil import get_steam_shortcuts_list, write_steam_shortcuts_list


class PupguiShortcutDialog(QObject):

    def __init__(self, steam_config_folder: str, parent=None):
        """
        ProtonUp-Qt Dialog for editing Steam shortcuts

        Parameters:
            steam_config_folder: str
                Path to Steam config folder (e.g. ~/.steam/root as in install_directory())
            parent: QObject
                Parent QObject, e.g. the main window
        """
        super(PupguiShortcutDialog, self).__init__(parent)

        self.steam_config_folder = steam_config_folder

        self.shortcuts = []

        self.load_ui()
        self.setup_ui()
        self.refresh_shortcut_list()
        self.ui.show()

    def load_ui(self):
        data = pkgutil.get_data(__name__, 'resources/ui/pupgui2_shortcutdialog.ui')
        ui_file = QDataStream(QByteArray(data))
        self.ui = QUiLoader().load(ui_file.device())

    def setup_ui(self):
        self.ui.tableShortcuts.setHorizontalHeaderLabels([self.tr('App Name'), self.tr('Executable'), self.tr('Start Directory'), self.tr('Icon')])

        self.ui.btnSave.clicked.connect(self.btn_save_clicked)
        self.ui.btnClose.clicked.connect(self.btn_close_clicked)

    def refresh_shortcut_list(self):
        self.shortcuts = get_steam_shortcuts_list(self.steam_config_folder)

        self.ui.tableShortcuts.setRowCount(len(self.shortcuts))

        for i, shortcut in enumerate(self.shortcuts):
            txt_name = QLineEdit(shortcut.game_name)
            txt_exe = QLineEdit(shortcut.shortcut_exe)
            txt_path = QLineEdit(shortcut.shortcut_startdir)
            txt_icon = QLineEdit(shortcut.shortcut_icon)

            txt_name.editingFinished.connect(lambda i=i: self.txt_changed(i, 0))
            txt_exe.editingFinished.connect(lambda i=i: self.txt_changed(i, 1))
            txt_path.editingFinished.connect(lambda i=i: self.txt_changed(i, 2))
            txt_icon.editingFinished.connect(lambda i=i: self.txt_changed(i, 3))

            self.ui.tableShortcuts.setCellWidget(i, 0, txt_name)
            self.ui.tableShortcuts.setCellWidget(i, 1, txt_exe)
            self.ui.tableShortcuts.setCellWidget(i, 2, txt_path)
            self.ui.tableShortcuts.setCellWidget(i, 3, txt_icon)

    def txt_changed(self, index: int, col: int) -> None:
        """
        Store changes in the table to self.shortcuts

        Parameters:
            index: int
                Row index of the table / index of self.shortcuts
            col: int
                Column index of the table
                0 = App Name
                1 = Executable Path (verified by os.path.exists before saving)
                2 = Start Directory
                3 = Icon Path (verified by os.path.exists before saving)

        Returns:
            None
        """
        text = self.ui.tableShortcuts.cellWidget(index, col).text()

        if col == 0:
            self.shortcuts[index].game_name = text
        elif col == 1:
            if os.path.isfile(text.replace('"', '', 2)):
                if not text.startswith('"'):
                    text = '"' + text
                if not text.endswith('"'):
                    text = text + '"'
                self.ui.tableShortcuts.cellWidget(index, col).setText(text)
                self.shortcuts[index].shortcut_exe = text
            else:
                self.ui.tableShortcuts.cellWidget(index, col).setText(self.shortcuts[index].shortcut_exe)
        elif col == 2:
            if os.path.exists(text.replace('"', '', 2)):
                if not text.startswith('"'):
                    text = '"' + text
                if not text.endswith('"'):
                    text = text + '"'
                self.ui.tableShortcuts.cellWidget(index, col).setText(text)
                self.shortcuts[index].shortcut_startdir = text
            else:
                self.ui.tableShortcuts.cellWidget(index, col).setText(self.shortcuts[index].shortcut_startdir)
        elif col == 3:
            self.shortcuts[index].shortcut_icon = text

    def btn_save_clicked(self):
        write_steam_shortcuts_list(self.steam_config_folder, self.shortcuts, [])
        self.ui.close()

    def btn_close_clicked(self):
        self.ui.close()
