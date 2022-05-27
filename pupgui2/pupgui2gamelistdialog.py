import pkgutil

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtUiTools import QUiLoader

from .util import list_installed_ctools, sort_compatibility_tool_names
from .steamutil import steam_update_ctool
from .steamutil import get_steam_game_list
from .steamutil import get_steam_ctool_list
from .util import get_install_location_from_directory_name
from .datastructures import AWACYStatus, SteamDeckCompatEnum


class PupguiGameListDialog(QObject):

    game_property_changed = Signal(bool)

    def __init__(self, install_dir, parent=None):
        super(PupguiGameListDialog, self).__init__(parent)
        self.install_dir = install_dir
        self.parent = parent

        install_loc = get_install_location_from_directory_name(self.install_dir)
        if not 'vdf_dir' in install_loc:
            return

        self.load_ui()
        self.setup_ui()
        self.ui.show()

    def load_ui(self):
        data = pkgutil.get_data(__name__, 'resources/ui/pupgui2_gamelistdialog.ui')
        ui_file = QDataStream(QByteArray(data))
        loader = QUiLoader()
        self.ui = loader.load(ui_file.device())

    def setup_ui(self):
        self.update_game_list()

        self.ui.tableGames.setHorizontalHeaderLabels([self.tr('Game'), self.tr('Compatibility Tool'), self.tr('Deck compatibility'), self.tr('Anticheat')])
        self.ui.tableGames.setColumnWidth(3, 20)
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

            lblicon = QLabel()
            p = QPixmap()
            if game.awacy_status == AWACYStatus.ASUPPORTED:
                lblicon.setToolTip(self.tr('Support was explicitly enabld / works out of the box'))
                p.loadFromData(pkgutil.get_data(__name__, 'resources/img/awacy_supported.png'))
            elif game.awacy_status == AWACYStatus.PLANNED:
                lblicon.setToolTip(self.tr('Game plans to support Proton/Wine'))
                p.loadFromData(pkgutil.get_data(__name__, 'resources/img/awacy_planned.png'))
            elif game.awacy_status == AWACYStatus.RUNNING:
                lblicon.setToolTip(self.tr('No official statement but runs fine (may require tinkering)'))
                p.loadFromData(pkgutil.get_data(__name__, 'resources/img/awacy_running.png'))
            elif game.awacy_status == AWACYStatus.BROKEN:
                lblicon.setToolTip(self.tr('Anti-Cheat stops game from running properly'))
                p.loadFromData(pkgutil.get_data(__name__, 'resources/img/awacy_broken.png'))
            elif game.awacy_status == AWACYStatus.DENIED:
                lblicon.setToolTip(self.tr('Linux support was explicitly denied'))
                p.loadFromData(pkgutil.get_data(__name__, 'resources/img/awacy_denied.png'))
            else:
                lblicon.setToolTip(self.tr('Anti-Cheat status unknown'))
                p.loadFromData(pkgutil.get_data(__name__, 'resources/img/awacy_unknown.png'))
            lblicon.setPixmap(p)
            self.ui.tableGames.setCellWidget(i, 3, lblicon)

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
