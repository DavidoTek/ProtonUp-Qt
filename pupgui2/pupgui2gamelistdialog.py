import os

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtUiTools import QUiLoader

from util import list_installed_ctools, sort_compatibility_tool_names
from steamutil import steam_update_ctool
from steamutil import get_steam_game_list
from steamutil import get_steam_ctool_list
from util import get_install_location_from_directory_name
from datastructures import SteamDeckCompatEnum


class PupguiGameListDialog(QObject):

    game_property_changed = Signal(bool)

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

        self.ui.tableGames.setHorizontalHeaderLabels([self.tr('Game'), self.tr('Compatibility Tool'), self.tr('Deck compatibility')])
        self.ui.btnClose.clicked.connect(self.btn_close_clicked)

    def update_game_list(self):
        install_loc = get_install_location_from_directory_name(self.install_dir)
        games = get_steam_game_list(steam_config_folder=install_loc.get('vdf_dir'))
        ctools = sort_compatibility_tool_names(list_installed_ctools(self.install_dir, without_version=True), reverse=True)
        for t in get_steam_ctool_list(steam_config_folder=install_loc.get('vdf_dir')):
            ctools.append(t.ctool_name)

        self.ui.tableGames.setRowCount(len(games))

        game_id_table_lables = []
        i = 0
        for game in games:
            self.ui.tableGames.setCellWidget(i, 0, QLabel(game.game_name))

            combo = QComboBox()
            combo.addItem('-')
            combo.addItems(ctools)
            if game.compat_tool not in ctools:
                combo.addItem(game.compat_tool)
            if game.compat_tool is None:
                combo.setCurrentText('-')
            else:
                combo.setCurrentText(game.compat_tool)
            combo.currentTextChanged.connect(lambda text,game=game: self.update_ctool(text, game))
            self.ui.tableGames.setCellWidget(i, 1, combo)

            deckc = game.get_deck_compat_category()
            deckt = game.get_deck_recommended_tool()
            if deckc == SteamDeckCompatEnum.UNKNOWN:
                self.ui.tableGames.setCellWidget(i, 2, QLabel(self.tr('Unknown')))
            elif deckc == SteamDeckCompatEnum.UNSUPPORTED:
                self.ui.tableGames.setCellWidget(i, 2, QLabel(self.tr('Unsupported')))
            elif deckc == SteamDeckCompatEnum.PLAYABLE:
                if deckt == '':
                    lbltxt = self.tr('Playable')
                else:
                    lbltxt = self.tr('Playable using {compat_tool}').format(compat_tool=deckt)
                self.ui.tableGames.setCellWidget(i, 2, QLabel(lbltxt))
            elif deckc == SteamDeckCompatEnum.VERIFIED:
                if deckt == '':
                    lbltxt = self.tr('Verified')
                else:
                    lbltxt = self.tr('Verified for {compat_tool}').format(compat_tool=deckt)
                self.ui.tableGames.setCellWidget(i, 2, QLabel(lbltxt))

            game_id_table_lables.append(game.app_id)
            i += 1
        self.ui.tableGames.setVerticalHeaderLabels(game_id_table_lables)

    def btn_close_clicked(self):
        self.ui.close()

    def update_ctool(self, ctool_name: str, game):
        if ctool_name == '-':
            ctool_name = None
        install_loc = get_install_location_from_directory_name(self.install_dir)
        steam_update_ctool(game, ctool_name, steam_config_folder=install_loc.get('vdf_dir'))
        self.game_property_changed.emit(True)
