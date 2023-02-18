import os
import pkgutil

from typing import List, Callable
from datetime import datetime

from PySide6.QtCore import QObject, Signal, Slot, QDataStream, QByteArray, Qt
from PySide6.QtGui import QPixmap, QBrush, QColor
from PySide6.QtWidgets import QLabel, QComboBox, QPushButton, QTableWidgetItem
from PySide6.QtUiTools import QUiLoader

from pupgui2.constants import PROTONDB_COLORS, STEAM_APP_PAGE_URL, AWACY_WEB_URL, PROTONDB_APP_PAGE_URL, LUTRIS_WEB_URL
from pupgui2.datastructures import AWACYStatus, SteamApp, SteamDeckCompatEnum
from pupgui2.lutrisutil import get_lutris_game_list, LutrisGame
from pupgui2.steamutil import steam_update_ctools, get_steam_game_list
from pupgui2.steamutil import is_steam_running, get_steam_ctool_list
from pupgui2.steamutil import get_protondb_status
from pupgui2.util import list_installed_ctools, sort_compatibility_tool_names, open_webbrowser_thread
from pupgui2.util import get_install_location_from_directory_name


class PupguiGameListDialog(QObject):

    game_property_changed = Signal(bool)
    protondb_status_fetched = Signal(SteamApp)

    def __init__(self, install_dir, parent=None):
        super(PupguiGameListDialog, self).__init__(parent)
        self.install_dir = install_dir
        self.parent = parent
        self.queued_changes = {}

        self.install_loc = get_install_location_from_directory_name(install_dir)
        self.launcher = self.install_loc.get('launcher')

        self.load_ui()
        self.setup_ui()
        self.protondb_status_fetched.connect(self.update_protondb_status)
        self.ui.show()

    def load_ui(self):
        data = pkgutil.get_data(__name__, 'resources/ui/pupgui2_gamelistdialog.ui')
        ui_file = QDataStream(QByteArray(data))
        loader = QUiLoader()
        self.ui = loader.load(ui_file.device())

    def setup_ui(self):
        if self.launcher == 'steam':
            self.setup_steam_list_ui()
        elif self.launcher == 'lutris':
            self.setup_lutris_list_ui()

        self.ui.tableGames.itemDoubleClicked.connect(self.item_doubleclick_action)
        self.ui.btnApply.clicked.connect(self.btn_apply_clicked)

    def setup_steam_list_ui(self):
        self.ui.tableGames.setHorizontalHeaderLabels([self.tr('Game'), self.tr('Compatibility Tool'), self.tr('Deck compatibility'), self.tr('Anticheat'), 'ProtonDB'])
        self.ui.tableGames.horizontalHeaderItem(3).setToolTip('https://areweanticheatyet.com')
        self.update_game_list_steam()

        if os.path.exists('/.flatpak-info'):
            self.ui.lblSteamRunningWarning.setVisible(True)
            self.ui.lblSteamRunningWarning.setStyleSheet('QLabel { color: grey; }')
        elif is_steam_running():
            self.ui.lblSteamRunningWarning.setVisible(True)
        else:
            self.ui.lblSteamRunningWarning.setVisible(False)

        self.ui.tableGames.setColumnWidth(0, 300)
        self.ui.tableGames.setColumnWidth(3, 70)
        self.ui.tableGames.setColumnWidth(4, 70)
    
    def setup_lutris_list_ui(self):
        self.ui.tableGames.setHorizontalHeaderLabels([self.tr('Game'), self.tr('Runner'), self.tr('Install Location'), self.tr('Installed Date'), ''])
        self.update_game_list_lutris()

        self.ui.lblSteamRunningWarning.setVisible(False)

        self.ui.tableGames.setColumnWidth(0, 300)
        self.ui.tableGames.setColumnWidth(1, 70)
        self.ui.tableGames.setColumnWidth(2, 280)
        self.ui.tableGames.setColumnWidth(3, 30)
        self.ui.tableGames.setColumnHidden(4, True)

        self.ui.btnApply.setText(self.tr('Close'))

    def update_game_list_steam(self):
        """ update the game list for the Steam launcher """
        self.games = get_steam_game_list(steam_config_folder=self.install_loc.get('vdf_dir'))
        ctools = [c if c != 'SteamTinkerLaunch' else 'Proton-stl' for c in sort_compatibility_tool_names(list_installed_ctools(self.install_dir, without_version=True), reverse=True) ]
        ctools.extend(t.ctool_name for t in get_steam_ctool_list(steam_config_folder=self.install_loc.get('vdf_dir')))

        self.ui.tableGames.setRowCount(len(self.games))

        game_id_table_lables = []
        for i, game in enumerate(self.games):
            game_item = QTableWidgetItem(game.game_name)
            game_item.setData(Qt.UserRole, f'{STEAM_APP_PAGE_URL}{game.app_id}')  # e.g. https://store.steampowered.com/app/620
            game_item.setToolTip(f'{game.game_name} ({game.app_id})')

            self.ui.tableGames.setItem(i, 0, game_item)

            # Compat Tool combobox
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

            compat_item = QTableWidgetItem()
            compat_item.setData(Qt.DisplayRole, combo.currentText())

            self.ui.tableGames.setItem(i, 1, compat_item)
            self.ui.tableGames.setCellWidget(i, 1, combo)

            # ProtonDB status
            btn_fetch_protondb = QPushButton(self.tr('click'))
            btn_fetch_protondb.clicked.connect(lambda checked=False, game=game: self.btn_fetch_protondb_clicked(game))

            fetch_protondb_item = QTableWidgetItem()
            fetch_protondb_item.setData(Qt.DisplayRole, '')  # Shouldn't need to be set, should always be invisible

            self.ui.tableGames.setItem(i, 4, fetch_protondb_item)
            self.ui.tableGames.setCellWidget(i, 4, btn_fetch_protondb)

            # SteamDeck compatibility
            deckc = game.get_deck_compat_category()
            deckt = game.get_deck_recommended_tool()
            lbltxt = ''
            if deckc == SteamDeckCompatEnum.UNKNOWN:
                lbltxt = self.tr('Unknown')
            elif deckc == SteamDeckCompatEnum.UNSUPPORTED:
                lbltxt = self.tr('Unsupported')
            elif deckc == SteamDeckCompatEnum.PLAYABLE:
                if deckt == '':
                    lbltxt = self.tr('Playable')
                elif deckt == 'native':
                    lbltxt = self.tr('Native (playable)')
                else:
                    lbltxt = self.tr('Playable using {compat_tool}').format(compat_tool=deckt)
            elif deckc == SteamDeckCompatEnum.VERIFIED:
                if deckt == '':
                    lbltxt = self.tr('Verified')
                elif deckt == 'native':
                    lbltxt = self.tr('Native (verified)')
                else:
                    lbltxt = self.tr('Verified for {compat_tool}').format(compat_tool=deckt)

            self.ui.tableGames.setItem(i, 2, QTableWidgetItem(lbltxt))

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

            # Used for sorting
            lblicon_item = QTableWidgetItem()
            lblicon_item.setData(Qt.DisplayRole, game.awacy_status.value)
            lblicon_item.setData(Qt.UserRole, AWACY_WEB_URL)

            self.ui.tableGames.setItem(i, 3, lblicon_item)
            self.ui.tableGames.setCellWidget(i, 3, lblicon)

            game_id_table_lables.append(game.app_id)

    def update_game_list_lutris(self):
        """ update the game list for the Lutris launcher """
        # Filter blank runners and Steam games, because we can't change any compat tool options for Steam games via Lutris
        # Steam games can be seen from the Steam games list, so no need to duplicate it here
        games: List[LutrisGame] = list(filter(lambda lutris_game: (lutris_game.runner is not None and lutris_game.runner != 'steam' and len(lutris_game.runner) > 0), get_lutris_game_list(self.install_loc)))

        self.ui.tableGames.setRowCount(len(games))

        # Not sure if we can allow compat tool updating from here, as Lutris allows configuring more than just Wine version
        # It lets you set Wine/DXVK/vkd3d/etc independently, so for now the dialog just displays game information
        for i, game in enumerate(games): 
            name_item = QTableWidgetItem(game.name)
            name_item.setToolTip(f'{game.name} ({game.slug})')
            if game.installer_slug:
                # Only games with an installer_slug will have a Lutris web URL - Could be an edge case that runners get removed/updated from lutris.net?
                name_item.setData(Qt.UserRole, f'{LUTRIS_WEB_URL}{game.slug}')

            runner_item = QTableWidgetItem(game.runner.capitalize())
            # Display wine runner information in tooltip
            if game.runner == 'wine':
                game_cfg = game.get_game_config()
                runnerinfo = game_cfg.get('wine', {})

                wine_ver = runnerinfo.get('version')
                dxvk_ver = runnerinfo.get('dxvk_version')
                vkd3d_ver = runnerinfo.get('vkd3d_version')

                tooltip = ''
                tooltip += f'Wine version: {wine_ver}' if wine_ver else ''
                tooltip += f'\nDXVK version: {dxvk_ver}' if dxvk_ver else ''
                tooltip += f'\nvkd3d version: {vkd3d_ver}' if vkd3d_ver else ''

                runner_item.setToolTip(tooltip)

            # Some games may be in Lutris but not have a valid install path, though the yml should *usually* have some path
            install_dir_text = game.install_dir or 'Unknown'
            install_dir_item = QTableWidgetItem(install_dir_text)
            if install_dir_text == 'Unknown':
                install_dir_item.setForeground(QBrush(QColor(PROTONDB_COLORS.get('gold'))))
            else:
                if os.path.isdir(install_dir_text):
                    # Set double click action to open valid install dir with xdg-open
                    install_dir_item.setToolTip('Double-click to browse...')
                    install_dir_item.setData(Qt.UserRole, lambda url: os.system(f'xdg-open "{url}"'))
                else:
                    install_dir_item.setToolTip('Install location does not exist!')

            install_date = datetime.fromtimestamp(int(game.installed_at)).isoformat().split('T')
            install_date_short = f'{install_date[0]}'
            install_date_tooltip = f'Installed at {install_date[0]} ({install_date[1]})'

            install_date_item = QTableWidgetItem(install_date_short)
            install_date_item.setData(Qt.UserRole, int(game.installed_at))
            install_date_item.setToolTip(install_date_tooltip)

            self.ui.tableGames.setItem(i, 0, name_item)
            self.ui.tableGames.setItem(i, 1, runner_item)
            self.ui.tableGames.setItem(i, 2, install_dir_item)
            self.ui.tableGames.setItem(i, 3, install_date_item)

    def btn_apply_clicked(self):
        self.update_queued_ctools_steam()
        self.ui.close()

    def btn_fetch_protondb_clicked(self, game: SteamApp):
        get_protondb_status(game, self.protondb_status_fetched)

    @Slot(SteamApp)
    def update_protondb_status(self, game: SteamApp):
        """ Slot is gets called when get_protondb_status finishes """
        if not game:
            print('Warning: update_protondb_status called with game=None')
            return
        pdb_tier = game.protondb_summary.get('tier', '?')

        if self.games.index(game) != None:
            # Use QTableWidgetItem to replace Button widget
            pdb_item = self.ui.tableGames.item(self.ui.tableGames.currentRow(), 4)
            pdb_item.setData(Qt.DisplayRole, pdb_tier)
            pdb_item.setData(Qt.UserRole, f'{PROTONDB_APP_PAGE_URL}{game.app_id}')  # e.g. https://www.protondb.com/app/412830
            pdb_item.setForeground(QBrush(QColor(PROTONDB_COLORS.get(pdb_tier))))
            pdb_item.setToolTip(self.tr('Confidence: {confidence}\nScore: {score}\nTrending: {trending}')
                .format(confidence=game.protondb_summary.get('confidence', '?'),
                        score=game.protondb_summary.get('score', '?'),
                        trending=game.protondb_summary.get('trendingTier', '?')))

            self.ui.tableGames.removeCellWidget(self.ui.tableGames.currentRow(), 4)

    def queue_ctool_change_steam(self, ctool_name: str, game: SteamApp):
        """ add compatibility tool changes to queue (Steam) """
        if ctool_name in {'-', ''}:
            ctool_name = None
        self.queued_changes[game] = ctool_name

        self.ui.tableGames.item(self.ui.tableGames.currentRow(), 1).setData(Qt.DisplayRole, ctool_name)

    def update_queued_ctools_steam(self):
        """ update the compatibility tools for all queued games (Steam) """
        if len(self.queued_changes) == 0:
            return
        steam_update_ctools(self.queued_changes, steam_config_folder=self.install_loc.get('vdf_dir'))
        self.game_property_changed.emit(True)

    def item_doubleclick_action(self, item):
        """ open link attached for QTableWidgetItem in browser """
        item_url = item.data(Qt.UserRole)
        if isinstance(item_url, str):
            open_webbrowser_thread(item_url)  # Str UserRole should always hold URL
        elif isinstance(item_url, Callable):
            item_url(item.text())

