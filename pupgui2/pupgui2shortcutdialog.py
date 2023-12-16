import pkgutil
from collections import Counter

from PySide6.QtCore import Qt, QObject, Signal, QDataStream, QByteArray
from PySide6.QtWidgets import QLineEdit
from PySide6.QtUiTools import QUiLoader

from pupgui2.datastructures import SteamApp
from pupgui2.steamutil import calc_shortcut_app_id, get_steam_user_list, determine_most_recent_steam_user
from pupgui2.steamutil import get_steam_shortcuts_list, write_steam_shortcuts_list
from pupgui2.util import host_path_exists


class ShortcutDialogLineEdit(QLineEdit):

    def __init__(self, parent=None, default_cursor_position: int = -1, *args, **kwargs,):
        super(ShortcutDialogLineEdit, self).__init__(parent, *args, **kwargs)

        self.default_cursor_position = default_cursor_position
        if self.default_cursor_position >= 0:
            self.setCursorPosition(self.default_cursor_position)
        
        self.was_focused = False

    def focusOutEvent(self, arg__1):
        super().focusOutEvent(arg__1)  # Super handles focusing events etc
        self.was_focused = False

        updated_cursor_pos = len(self.text()) if self.default_cursor_position == -1 else self.default_cursor_position
        self.setCursorPosition(updated_cursor_pos)  # Move cursor back to default position (ex: start for Game Name field)

    def focusInEvent(self, arg__1):
        super().focusInEvent(arg__1)

        # Only call focusWithTextSelection for tab focus, because mousePressEvent will capture select on mousee click focus
        # mousePressEvent is fired after focusInEvent, and the click event in mousePressEvent clears the selection if we call focusWithTextSelection here
        # We can call focusWithTextSelection here and set self.was_focused because you can only focus onto the same widget with a tab once, pressing tab again moves the focus away
        if arg__1.reason() in [ Qt.FocusReason.TabFocusReason, Qt.FocusReason.OtherFocusReason ]:
            self.focusWithTextSelection()

    def mousePressEvent(self, arg__1):
        super().mousePressEvent(arg__1)
        self.focusWithTextSelection()

    def focusWithTextSelection(self):
        if not self.was_focused:
            self.selectAll()
            self.was_focused = True


class PupguiShortcutDialog(QObject):

    def __init__(self, steam_config_folder: str, game_property_changed: Signal, parent=None):
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
        self.game_property_changed = game_property_changed

        self.shortcuts = []
        self.discarded_shortcuts = []

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
        self.ui.btnAdd.clicked.connect(self.btn_add_clicked)
        self.ui.btnRemove.clicked.connect(self.btn_remove_clicked)

    def prepare_table_row(self, i: int, shortcut: SteamApp):
        txt_name = ShortcutDialogLineEdit(shortcut.game_name, default_cursor_position=0)
        txt_exe = ShortcutDialogLineEdit(shortcut.shortcut_exe)
        txt_path = ShortcutDialogLineEdit(shortcut.shortcut_startdir)
        txt_icon = ShortcutDialogLineEdit(shortcut.shortcut_icon)

        txt_name.setToolTip(shortcut.game_name)
        txt_exe.setToolTip(shortcut.shortcut_exe)
        txt_path.setToolTip(shortcut.shortcut_startdir)
        txt_icon.setToolTip(shortcut.shortcut_icon)

        txt_name.setPlaceholderText(shortcut.game_name)
        txt_exe.setPlaceholderText(shortcut.shortcut_exe)
        txt_path.setPlaceholderText(shortcut.shortcut_startdir)
        txt_icon.setPlaceholderText(shortcut.shortcut_icon)

        txt_name.editingFinished.connect(lambda i=i: self.txt_changed(i, 0))
        txt_exe.editingFinished.connect(lambda i=i: self.txt_changed(i, 1))
        txt_path.editingFinished.connect(lambda i=i: self.txt_changed(i, 2))
        txt_icon.editingFinished.connect(lambda i=i: self.txt_changed(i, 3))

        self.ui.tableShortcuts.setCellWidget(i, 0, txt_name)
        self.ui.tableShortcuts.setCellWidget(i, 1, txt_exe)
        self.ui.tableShortcuts.setCellWidget(i, 2, txt_path)
        self.ui.tableShortcuts.setCellWidget(i, 3, txt_icon)

    def refresh_shortcut_list(self):
        self.shortcuts = get_steam_shortcuts_list(self.steam_config_folder)

        self.ui.tableShortcuts.setRowCount(len(self.shortcuts))

        for i, shortcut in enumerate(self.shortcuts):
            self.prepare_table_row(i, shortcut)

    def txt_changed(self, index: int, col: int) -> None:
        """
        Store changes in the table to self.shortcuts

        Parameters:
            index: int
                Row index of the table / index of self.shortcuts
            col: int
                Column index of the table
                0 = App Name
                1 = Executable Path (verified by host_path_exists before saving)
                2 = Start Directory (verified by host_path_exists before saving)
                3 = Icon Path

        Returns:
            None
        """
        text = self.ui.tableShortcuts.cellWidget(index, col).text()

        if col == 0:
            self.shortcuts[index].game_name = text
        elif col == 1:
            if host_path_exists(text.replace('"', '', 2), is_file=True):
                if not text.startswith('"'):
                    text = '"' + text
                if not text.endswith('"'):
                    text = text + '"'
                self.ui.tableShortcuts.cellWidget(index, col).setText(text)
                self.shortcuts[index].shortcut_exe = text
            else:
                self.ui.tableShortcuts.cellWidget(index, col).setText(self.shortcuts[index].shortcut_exe)
        elif col == 2:
            if host_path_exists(text.replace('"', '', 2), is_file=False):
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

        self.ui.tableShortcuts.cellWidget(index, col).setToolTip(text)

    def btn_save_clicked(self):
        # remove all shortcuts that have no name or executable
        filtered_shortcuts = list(filter(lambda s: s.game_name != '' and s.shortcut_exe != '', self.shortcuts))

        for s in filtered_shortcuts:
            if s.app_id == -1:  # calculate app_id for new shortcuts
                s.app_id = calc_shortcut_app_id(s.game_name, s.shortcut_exe)

        write_steam_shortcuts_list(self.steam_config_folder, filtered_shortcuts, self.discarded_shortcuts)
        self.game_property_changed.emit(True)
        self.ui.close()

    def btn_close_clicked(self):
        self.ui.close()

    def btn_add_clicked(self):
        # new id should be higher than last one
        highest_id = 0
        for shortcut in self.shortcuts:
            sid = int(shortcut.shortcut_id)
            if sid > highest_id:
                highest_id = sid

        new_shortcut = SteamApp()

        # guess for which user new shortcuts should be created
        # if there are already other shortcuts, take the most common user
        # otherwise, determine the most recent user (currently logged in)
        if len(self.shortcuts) > 0:
            new_shortcut.shortcut_user = Counter([s.shortcut_user for s in self.shortcuts]).most_common(1)[0][0]
        else:
            steam_users = get_steam_user_list(self.steam_config_folder)
            most_recent_user = determine_most_recent_steam_user(steam_users)
            if not most_recent_user:
                return
            new_shortcut.shortcut_user = str(most_recent_user.get_short_id())

        new_shortcut.shortcut_id = str(highest_id+1)
        self.shortcuts.append(new_shortcut)

        self.ui.tableShortcuts.setRowCount(len(self.shortcuts))
        self.prepare_table_row(len(self.shortcuts) - 1, new_shortcut)

    def btn_remove_clicked(self):
        for sr in self.ui.tableShortcuts.selectedRanges():
            for i in range(sr.topRow(), sr.bottomRow()+1):
                sid = self.shortcuts[i].shortcut_id
                if sid not in self.discarded_shortcuts:
                    self.discarded_shortcuts.append(sid)
                self.ui.tableShortcuts.cellWidget(i, 0).setStyleSheet('QLineEdit { color: red; }')
