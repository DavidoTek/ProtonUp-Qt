import os
import pkgutil

from PySide6.QtCore import QObject, Signal, QDataStream, QByteArray
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QComboBox
from PySide6.QtUiTools import QUiLoader

from pupgui2.datastructures import AWACYStatus, SteamApp, SteamDeckCompatEnum
from pupgui2.lutrisutil import get_lutris_game_list
from pupgui2.steamutil import steam_update_ctools, get_steam_game_list
from pupgui2.steamutil import is_steam_running, get_steam_ctool_list
from pupgui2.util import list_installed_ctools, sort_compatibility_tool_names
from pupgui2.util import get_install_location_from_directory_name


class PupguiGameListDialog(QObject):

    game_property_changed = Signal(bool)

    def __init__(self, install_dir, parent=None):
        super(PupguiGameListDialog, self).__init__(parent)
        self.install_dir = install_dir
        self.parent = parent

        self.queued_changes = {}

        self.install_loc = get_install_location_from_directory_name(install_dir)

        self.load_ui()
        self.setup_ui()
        self.ui.show()

    def load_ui(self):
        data = pkgutil.get_data(__name__, 'resources/ui/pupgui2_gamelistdialog.ui')
        ui_file = QDataStream(QByteArray(data))
        loader = QUiLoader()
        self.ui = loader.load(ui_file.device())

    def setup_ui(self):
        if self.install_loc.get('launcher') == 'steam':
            self.ui.tableGames.setHorizontalHeaderLabels([self.tr('Game'), self.tr('Compatibility Tool'), self.tr('Deck compatibility'), self.tr('Anticheat')])
            self.ui.tableGames.horizontalHeaderItem(3).setToolTip('https://areweanticheatyet.com')
            self.update_game_list_steam()

            if os.path.exists('/.flatpak-info'):
                self.ui.lblSteamRunningWarning.setVisible(True)
                self.ui.lblSteamRunningWarning.setStyleSheet('QLabel { color: grey; }')
            elif is_steam_running():
                self.ui.lblSteamRunningWarning.setVisible(True)
            else:
                self.ui.lblSteamRunningWarning.setVisible(False)

        elif self.install_loc.get('launcher') == 'lutris':
            self.update_game_list_lutris()
            self.ui.lblSteamRunningWarning.setVisible(False)

        self.ui.tableGames.setColumnWidth(3, 20)
        self.ui.btnApply.clicked.connect(self.btn_apply_clicked)

    def update_game_list_steam(self):
        """ update the game list for the Steam launcher """
        games = get_steam_game_list(steam_config_folder=self.install_loc.get('vdf_dir'))
        ctools = [c if c != 'SteamTinkerLaunch' else 'Proton-stl' for c in sort_compatibility_tool_names(list_installed_ctools(self.install_dir, without_version=True), reverse=True) ]
        ctools.extend(t.ctool_name for t in get_steam_ctool_list(steam_config_folder=self.install_loc.get('vdf_dir')))

        self.ui.tableGames.setRowCount(len(games))

        game_id_table_lables = []
        for i, game in enumerate(games):
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
            combo.currentTextChanged.connect(lambda text,game=game: self.queue_ctool_change_steam(text, game))
            self.ui.tableGames.setCellWidget(i, 1, combo)

            lbl_deck_compat = QLabel()
            # ProtonDB status
            pdb_tier = game.protondb_summary.get('tier', '?')
            lbl_deck_compat.setToolTip(f'ProtonDB.com: {pdb_tier}')

            # SteamDeck compatibility
            deckc = game.get_deck_compat_category()
            deckt = game.get_deck_recommended_tool()
            if deckc == SteamDeckCompatEnum.UNKNOWN:
                lbl_deck_compat.setText(self.tr('Unknown'))
            elif deckc == SteamDeckCompatEnum.UNSUPPORTED:
                lbl_deck_compat.setText(self.tr('Unsupported'))
            elif deckc == SteamDeckCompatEnum.PLAYABLE:
                if deckt == '':
                    lbltxt = self.tr('Playable')
                elif deckt == 'native':
                    lbltxt = self.tr('Native (playable)')
                else:
                    lbltxt = self.tr('Playable using {compat_tool}').format(compat_tool=deckt)
                lbl_deck_compat.setText(lbltxt)
            elif deckc == SteamDeckCompatEnum.VERIFIED:
                if deckt == '':
                    lbltxt = self.tr('Verified')
                elif deckt == 'native':
                    lbltxt = self.tr('Native (verified)')
                else:
                    lbltxt = self.tr('Verified for {compat_tool}').format(compat_tool=deckt)
                lbl_deck_compat.setText(lbltxt)
            self.ui.tableGames.setCellWidget(i, 2, lbl_deck_compat)

            # AWACY status
            lblicon = QLabel()
            p = QPixmap()
            if game.awacy_status == AWACYStatus.ASUPPORTED:
                lblicon.setToolTip(self.tr('Support was explicitly enabled / works out of the box'))
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
        self.ui.tableGames.setVerticalHeaderLabels(game_id_table_lables)

    def update_game_list_lutris(self):
        """ update the game list for the Lutris launcher """
        games = get_lutris_game_list(self.install_loc)

        self.ui.tableGames.setRowCount(len(games))

        for i, game in enumerate(games):
            self.ui.tableGames.setCellWidget(i, 0, QLabel(game.name))

    def btn_apply_clicked(self):
        self.update_queued_ctools_steam()
        self.ui.close()

    def queue_ctool_change_steam(self, ctool_name: str, game: SteamApp):
        """ add compatibility tool changes to queue (Steam) """
        if ctool_name in {'-', ''}:
            ctool_name = None
        self.queued_changes[game] = ctool_name

    def update_queued_ctools_steam(self):
        """ update the compatibility tools for all queued games (Steam) """
        if len(self.queued_changes) == 0:
            return
        steam_update_ctools(self.queued_changes, steam_config_folder=self.install_loc.get('vdf_dir'))
        self.game_property_changed.emit(True)
