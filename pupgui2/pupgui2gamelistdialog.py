import os, requests

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtUiTools import QUiLoader

from util import list_installed_ctools, sort_compatibility_tool_names
from util import steam_update_ctool
from util import get_steam_game_list
from util import get_install_location_from_directory_name


class PupguiGameListDialog(QObject):

    def __init__(self, pupgui2_base_dir, install_dir, parent=None):
        super(PupguiGameListDialog, self).__init__(parent)
        self.pupgui2_base_dir = pupgui2_base_dir
        self.install_dir = install_dir
        self.parent = parent

        install_loc = get_install_location_from_directory_name(self.install_dir)
        if not 'vdf_dir' in install_loc:
            return

        self.load_ui()
        self.setup_ui()
        self.ui.show()

    def load_ui(self):
        ui_file_name = os.path.join(self.pupgui2_base_dir, 'ui/pupgui2_gamelistdialog.ui')
        ui_file = QFile(ui_file_name)
        if not ui_file.open(QIODevice.ReadOnly):
            print(f'Cannot open {ui_file_name}: {ui_file.errorString()}')
            return
        loader = QUiLoader()
        self.ui = loader.load(ui_file, self.parent)
        ui_file.close()

    def setup_ui(self):
        self.update_game_list()

        self.ui.tableGames.setHorizontalHeaderLabels([self.tr('Game'), self.tr('Compatibility Tool')])
        self.ui.btnClose.clicked.connect(self.btn_close_clicked)

    def update_game_list(self):
        install_loc = get_install_location_from_directory_name(self.install_dir)
        games = get_steam_game_list(steam_config_folder=install_loc.get('vdf_dir'))
        ctools = sort_compatibility_tool_names(list_installed_ctools(self.install_dir))

        self.ui.tableGames.setRowCount(len(games))

        game_id_table_lables = []
        i = 0
        for game in games:
            self.ui.tableGames.setCellWidget(i, 0, QLabel(game.get('game_name')))
            combo = QComboBox()
            combo.addItems(ctools)
            if game.get('compat_tool') not in ctools:
                combo.addItem(game.get('compat_tool'))
            combo.setCurrentText(game.get('compat_tool'))
            # ToDo: connect currentTextChanged to update_tool ?
            self.ui.tableGames.setCellWidget(i, 1, combo)
            game_id_table_lables.append(game.get('id'))
            i += 1
        self.ui.tableGames.setVerticalHeaderLabels(game_id_table_lables)

    def btn_close_clicked(self):
        self.ui.close()

    def update_ctool(self, ctool_name: str, game_id: str = '0'):
        install_loc = get_install_location_from_directory_name(self.install_dir)
        steam_update_ctool(int(game_id), ctool_name, steam_config_folder=install_loc.get('vdf_dir'))
