import os
import pkgutil

from typing import List, Callable, Tuple, Union
from datetime import datetime

from PySide6.QtCore import QObject, Signal, Slot, QDataStream, QByteArray, Qt
from PySide6.QtGui import QPixmap, QBrush, QColor, QKeySequence, QShortcut
from PySide6.QtWidgets import QLabel, QComboBox, QPushButton, QTableWidgetItem
from PySide6.QtUiTools import QUiLoader

from pupgui2.constants import PROTONDB_COLORS, STEAM_APP_PAGE_URL, AWACY_WEB_URL, PROTONDB_APP_PAGE_URL, LUTRIS_WEB_URL
from pupgui2.datastructures import AWACYStatus, SteamApp, SteamDeckCompatEnum, LutrisGame, HeroicGame
from pupgui2.lutrisutil import get_lutris_game_list
from pupgui2.steamutil import steam_update_ctools, get_steam_game_list
from pupgui2.steamutil import is_steam_running, get_steam_ctool_list
from pupgui2.steamutil import get_protondb_status
from pupgui2.heroicutil import get_heroic_game_list, is_heroic_launcher
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
        self.games: List[Union[SteamApp, LutrisGame, HeroicGame]] = []

        self.install_loc = get_install_location_from_directory_name(install_dir)
        self.launcher = self.install_loc.get('launcher', '')
        self.should_show_steam_warning = (is_steam_running() or os.path.exists('/.flatpak-info')) and self.launcher == 'steam'

        self.load_ui()
        self.setup_ui()
        self.ui.show()

    def load_ui(self):
        data = pkgutil.get_data(__name__, 'resources/ui/pupgui2_gamelistdialog.ui')
        ui_file = QDataStream(QByteArray(data))
        self.ui = QUiLoader().load(ui_file.device())

    def setup_ui(self):
        if self.launcher == 'steam':
            self.setup_steam_list_ui()
        elif self.launcher == 'lutris':
            self.setup_lutris_list_ui()
        elif is_heroic_launcher(self.launcher):
            self.setup_heroic_list_ui()

        self.ui.btnSearch.setVisible(False)
        self.ui.searchBox.setVisible(False)  # Hide searchbox by default

        self.set_apply_btn_text()
        self.ui.setWindowTitle(self.tr('Game List for {LAUNCHER}').format(LAUNCHER=self.launcher.capitalize() if not is_heroic_launcher(self.launcher) else 'Heroic'))

        self.ui.lblSteamRunningWarning.setVisible(self.should_show_steam_warning)  # Only show warning if Steam is running, and make it grey if we're running in Flatpak
        self.ui.tableGames.horizontalHeaderItem(0).setToolTip(self.tr('Installed games: {NO_INSTALLED}').format(NO_INSTALLED=str(len(self.games))))

        self.ui.tableGames.itemDoubleClicked.connect(self.item_doubleclick_action)
        self.ui.btnApply.clicked.connect(self.btn_apply_clicked)
        self.ui.btnSearch.clicked.connect(self.btn_search_clicked)
        self.ui.btnRefreshGames.clicked.connect(self.btn_refresh_games_clicked)
        self.ui.searchBox.textChanged.connect(self.search_gamelist_games)

        # Hide Search button and disable shortcut if no games
        if len(self.games) > 0:
            self.ui.btnSearch.setVisible(True)
            QShortcut(QKeySequence.Find, self.ui).activated.connect(self.btn_search_clicked)

    def setup_steam_list_ui(self):
        self.ui.tableGames.setHorizontalHeaderLabels([self.tr('Game'), self.tr('Compatibility Tool'), self.tr('Deck compatibility'), self.tr('Anticheat'), 'ProtonDB'])
        self.ui.tableGames.horizontalHeaderItem(3).setToolTip('https://areweanticheatyet.com')
        self.ui.lblSteamRunningWarning.setStyleSheet('QLabel { color: grey; }' if os.path.exists('/.flatpak-info') else self.ui.lblSteamRunningWarning.styleSheet())

        self.update_game_list_steam()
        self.protondb_status_fetched.connect(self.update_protondb_status)

        self.ui.tableGames.setColumnWidth(0, 300)
        self.ui.tableGames.setColumnWidth(3, 70)
        self.ui.tableGames.setColumnWidth(4, 70)
    
    def setup_lutris_list_ui(self):
        self.ui.tableGames.setHorizontalHeaderLabels([self.tr('Game'), self.tr('Runner'), self.tr('Install Location'), self.tr('Installed Date'), ''])
        self.update_game_list_lutris()

        self.ui.tableGames.setColumnWidth(0, 300)
        self.ui.tableGames.setColumnWidth(1, 70)
        self.ui.tableGames.setColumnWidth(2, 280)
        self.ui.tableGames.setColumnWidth(3, 30)
        self.ui.tableGames.setColumnHidden(4, True)

    def setup_heroic_list_ui(self):
        self.ui.tableGames.setHorizontalHeaderLabels([self.tr('Game'), self.tr('Compatibility Tool'), self.tr('Install Location'), self.tr('Runner'), ''])
        self.update_game_list_heroic()

        self.ui.tableGames.setColumnWidth(0, 270)
        self.ui.tableGames.setColumnWidth(1, 170)
        self.ui.tableGames.setColumnWidth(2, 250)
        self.ui.tableGames.setColumnWidth(3, 40)
        self.ui.tableGames.setColumnHidden(4, True)

    def update_game_list_steam(self, cached=True):
        """ update the game list for the Steam launcher """
        self.games = get_steam_game_list(steam_config_folder=self.install_loc.get('vdf_dir'), cached=cached)
        ctools = [c if c != 'SteamTinkerLaunch' else 'Proton-stl' for c in sort_compatibility_tool_names(list_installed_ctools(self.install_dir, without_version=True), reverse=True)]
        ctools.extend(t.ctool_name for t in get_steam_ctool_list(steam_config_folder=self.install_loc.get('vdf_dir'), cached=True))

        self.ui.tableGames.setRowCount(len(self.games))

        game_id_table_lables = []
        for i, game in enumerate(self.games):
            game_item = QTableWidgetItem(game.game_name)
            game_item.setData(Qt.UserRole, f'{STEAM_APP_PAGE_URL}{game.app_id}')  # e.g. https://store.steampowered.com/app/620
            game_item.setToolTip(f'{game.game_name} ({game.app_id})')

            self.ui.tableGames.setItem(i, 0, game_item)

            # Compat Tool combobox
            combo = QComboBox()
            combo.addItems(['-'] + ctools)
            if game.compat_tool not in ctools:
                combo.addItem(game.compat_tool)

            combo.setCurrentText('-' if game.compat_tool is None else game.compat_tool)
            combo.currentTextChanged.connect(lambda text,game=game: self.queue_ctool_change_steam(text, game))

            compat_item = QTableWidgetItem()
            compat_item.setData(Qt.DisplayRole, combo.currentText())

            self.ui.tableGames.setItem(i, 1, compat_item)
            self.ui.tableGames.setCellWidget(i, 1, combo)

            # ProtonDB status
            btn_fetch_protondb = QPushButton(self.tr('click'))
            btn_fetch_protondb.clicked.connect(lambda checked=False, game=game: get_protondb_status(game, self.protondb_status_fetched))

            self.ui.tableGames.setItem(i, 4, QTableWidgetItem())
            self.ui.tableGames.setCellWidget(i, 4, btn_fetch_protondb)

            lbltxt = self.get_steamdeck_compatibility(game)
            self.ui.tableGames.setItem(i, 2, QTableWidgetItem(lbltxt))

            # AWACY status
            lblicon = QLabel()
            p = QPixmap()
            awacy_tooltip, awacy_icon = self.get_steamapp_awacystatus(game)
            p.loadFromData(pkgutil.get_data(__name__, os.path.join('resources/img', awacy_icon)))
            lblicon.setToolTip(awacy_tooltip)
            lblicon.setPixmap(p)
            lblicon.setAlignment(Qt.AlignCenter)

            lblicon_item = QTableWidgetItem()
            lblicon_item.setData(Qt.DisplayRole, game.awacy_status.value)
            lblicon_item.setTextAlignment(Qt.AlignCenter)

            search_str = ("" if game.awacy_status == AWACYStatus.UNKNOWN else game.game_name)
            lblicon_item.setData(Qt.UserRole, AWACY_WEB_URL.format(GAMENAME=search_str))

            self.ui.tableGames.setItem(i, 3, lblicon_item)
            self.ui.tableGames.setCellWidget(i, 3, lblicon)

            game_id_table_lables.append(game.app_id)

    def update_game_list_lutris(self):
        """ update the game list for the Lutris launcher """
        # Filter blank runners and Steam games, because we can't change any compat tool options for Steam games via Lutris
        # Steam games can be seen from the Steam games list, so no need to duplicate it here
        self.games = list(filter(lambda lutris_game: (lutris_game.runner is not None and lutris_game.runner != 'steam' and len(lutris_game.runner) > 0), get_lutris_game_list(self.install_loc)))

        self.ui.tableGames.setRowCount(len(self.games))

        # Not sure if we can allow compat tool updating from here, as Lutris allows configuring more than just Wine version
        # It lets you set Wine/DXVK/vkd3d/etc independently, so for now the dialog just displays game information
        for i, game in enumerate(self.games): 
            name_item = QTableWidgetItem(game.name)
            name_item.setToolTip(f'{game.name} ({game.slug})')
            if game.installer_slug:
                # Only games with an installer_slug will have a Lutris web URL - Could be an edge case that runners get removed/updated from lutris.net?
                name_item.setData(Qt.UserRole, f'{LUTRIS_WEB_URL}{game.slug}')

            runner_item = QTableWidgetItem(game.runner.capitalize())
            runner_item.setTextAlignment(Qt.AlignCenter)
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
            install_dir_text = game.install_dir or self.tr('Unknown')
            install_dir_item = QTableWidgetItem(install_dir_text)
            self.set_item_data_directory(install_dir_item, install_dir_text)

            install_date = datetime.fromtimestamp(int(game.installed_at)).isoformat().split('T')
            install_date_short = f'{install_date[0]}'
            install_date_tooltip = self.tr('Installed at {DATE} ({TIME})').format(DATE=install_date[0], TIME=install_date[1])

            install_date_item = QTableWidgetItem(install_date_short)
            install_date_item.setData(Qt.UserRole, int(game.installed_at))
            install_date_item.setToolTip(install_date_tooltip)
            install_date_item.setTextAlignment(Qt.AlignCenter)

            self.ui.tableGames.setItem(i, 0, name_item)
            self.ui.tableGames.setItem(i, 1, runner_item)
            self.ui.tableGames.setItem(i, 2, install_dir_item)
            self.ui.tableGames.setItem(i, 3, install_date_item)

    def update_game_list_heroic(self):
        heroic_dir = os.path.join(os.path.expanduser(self.install_loc.get('install_dir')), '../..')
        self.games: List[HeroicGame] = list(filter(lambda heroic_game: (heroic_game.is_installed and len(heroic_game.runner) > 0 and not heroic_game.is_dlc), get_heroic_game_list(heroic_dir)))

        self.ui.tableGames.setRowCount(len(self.games))

        for i, game in enumerate(self.games):
            title_item = QTableWidgetItem(game.title)
            if game.store_url:
                title_item.setData(Qt.UserRole, game.store_url)

            title_tooltip = game.title
            if game.executable:
                title_tooltip += f' ({game.executable})'
            title_item.setToolTip(title_tooltip)

            compat_item = QTableWidgetItem()
            # Wine games
            if game.platform.lower() == 'windows':
                compat_item_text = game.wine_info.get('name', '').split('-', 1)[1].strip()
                compat_tool_bin_path = game.wine_info.get('bin', '')

                compat_tool_tooltip = self.tr('Name: {compat_item_text}').format(compat_item_text=compat_item_text)
                if compat_tool_bin_path:
                    compat_tool_tooltip += self.tr('\nPath: {compat_tool_bin_path}').format(compat_tool_bin_path=compat_tool_bin_path)

                    compat_tool_folder = os.path.join(compat_tool_bin_path.split(compat_item_text)[0], compat_item_text)  # wine_info name is always "<tool_type> - <tool_folder_name>", compat_text_item is always "<tool_folder_name>" if we have the path
                    compat_item.setData(Qt.UserRole, lambda path: os.system(f'xdg-open "{compat_tool_folder}"'))
                compat_tool_tooltip += self.tr('\nType: {wine_type}').format(wine_type=game.wine_info.get("type", "").capitalize()) if game.wine_info.get('type', '') else ''
            else:
                # Linux/Browser games
                compat_item_text = self.tr('Browser') if game.platform.lower() == 'browser' else self.tr('Native')
                compat_tool_tooltip = self.tr('Type: {PLATFORM}').format(PLATFORM=game.platform)

            compat_item.setText(compat_item_text)
            compat_item.setToolTip(compat_tool_tooltip)
            compat_item.setTextAlignment(Qt.AlignCenter)

            install_path_item = QTableWidgetItem(game.install_path)
            if game.platform.lower() == 'browser':
                # Browser game paths are browserUrl, so the path won't exist -- Ignore this and set the tooltip and xdg-open action to open the URL 
                self.set_item_data_directory(install_path_item, game.install_path, tooltip_exists=self.tr('Double-click to open in browser'), ignore_invalid_path=True)
            else:
                self.set_item_data_directory(install_path_item, game.install_path)
            
            runner_item = QTableWidgetItem(game.runner)
            runner_item.setTextAlignment(Qt.AlignCenter)

            self.ui.tableGames.setItem(i, 0, title_item)
            self.ui.tableGames.setItem(i, 1, compat_item)
            self.ui.tableGames.setItem(i, 2, install_path_item)
            self.ui.tableGames.setItem(i, 3, runner_item)

    def set_apply_btn_text(self):
        """ Set text for Apply button to 'Close' if the games list is empty, if the current launcher is not Steam or if there are no queued changes."""

        txt = self.tr('Close') if len(self.games) <= 0 or self.launcher != 'steam' or len(self.queued_changes) <= 0 else self.tr('Apply')
        self.ui.btnApply.setText(txt)

    def btn_apply_clicked(self):
        self.update_queued_ctools_steam()
        self.ui.close()

    def btn_refresh_games_clicked(self):
        self.queued_changes = {}
        if self.launcher == 'steam':
            self.update_game_list_steam(cached=False)
        elif self.launcher == 'lutris':
            self.update_game_list_lutris()
        elif is_heroic_launcher(self.launcher):
            self.update_game_list_heroic()

    def btn_search_clicked(self):
        self.ui.searchBox.setVisible(not self.ui.searchBox.isVisible())
        self.ui.btnSearch.setText(self.tr('Done') if self.ui.searchBox.isVisible() else self.tr('Search'))  # "Done" is not good text, try something else
        self.ui.lblSteamRunningWarning.setVisible(self.should_show_steam_warning and not self.ui.searchBox.isVisible())
        self.ui.searchBox.setFocus()

        self.search_gamelist_games(self.ui.searchBox.text() if self.ui.searchBox.isVisible() else '')

    def search_gamelist_games(self, text):
        for row in range(self.ui.tableGames.rowCount()):
            should_hide: bool = not text.lower() in self.ui.tableGames.item(row, 0).text().lower()
            self.ui.tableGames.setRowHidden(row, should_hide)

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
            pdb_item.setSelected(False)

    def queue_ctool_change_steam(self, ctool_name: str, game: SteamApp):
        """ add compatibility tool changes to queue (Steam) """
        ctool_name = None if ctool_name in {'-', ''} else ctool_name

        self.queued_changes[game] = ctool_name
        self.ui.tableGames.item(self.ui.tableGames.currentRow(), 1).setData(Qt.DisplayRole, ctool_name)
        self.set_apply_btn_text()

    def update_queued_ctools_steam(self):
        """ update the compatibility tools for all queued games (Steam) """
        if len(self.queued_changes) > 0:
            steam_update_ctools(self.queued_changes, steam_config_folder=self.install_loc.get('vdf_dir'))
            self.game_property_changed.emit(True)

    def item_doubleclick_action(self, item):
        """ open link attached for QTableWidgetItem in browser """
        item_url = item.data(Qt.UserRole)
        if isinstance(item_url, str):
            open_webbrowser_thread(item_url)  # Str UserRole should always hold URL
        elif isinstance(item_url, Callable):
            item_url(item.text())

    def set_item_data_directory(self, item: QTableWidgetItem, path: str,
                                    tooltip_exists: str = 'Double click to browse...',
                                    tooltip_invalid: str = 'Install location does not exist!',
                                    ignore_invalid_path: bool = False):
        """ Set the Qt.UserRole data for a QTableWidgetItem to a lambda which uses xdg-open to open a given path, if it exists. """

        # (hacky way to) show default tooltips in parameters while allowing translation (make sure they match the default parameters)
        if tooltip_exists == 'Double click to browse...':
            tooltip_exists = self.tr('Double click to browse...')
        if tooltip_invalid == 'Install location does not exist!':
            tooltip_invalid = self.tr('Install location does not exist!')

        if os.path.isdir(path) or ignore_invalid_path:
            item.setToolTip(tooltip_exists)
            item.setData(Qt.UserRole, lambda path: os.system(f'xdg-open "{path}"'))
        else:
            item.setToolTip(tooltip_invalid)

    def get_steamapp_awacystatus(self, game: SteamApp) -> Tuple[str, str]:
        """ Return translated status text and icon representing AreWeAntiCheatYet.com status for a Steam game """
        awacy_status: str = ''
        awacy_icon: str = ''

        if game.awacy_status == AWACYStatus.ASUPPORTED:
            awacy_status = self.tr('Support was explicitly enabled / works out of the box')
            awacy_icon = 'awacy_supported.png'
        elif game.awacy_status == AWACYStatus.PLANNED:
            awacy_status = self.tr('Game plans to support Proton/Wine')
            awacy_icon = 'awacy_planned.png'
        elif game.awacy_status == AWACYStatus.RUNNING:
            awacy_status = self.tr('No official statement but runs fine (may require tinkering)')
            awacy_icon = 'awacy_running.png'
        elif game.awacy_status == AWACYStatus.BROKEN:
            awacy_status = self.tr('Anti-Cheat stops game from running properly')
            awacy_icon = 'awacy_broken.png'
        elif game.awacy_status == AWACYStatus.DENIED:
            awacy_status = self.tr('Linux support was explicitly denied')
            awacy_status = 'awacy_denied.png'
        else:
            awacy_status = self.tr('Anti-Cheat status unknown')
            awacy_icon = 'awacy_unknown.png'

        return awacy_status, awacy_icon

    def get_steamdeck_compatibility(self, game: SteamApp) -> str:
        """ Return translated Steam Deck compatibility rating text for a Steam game """
        deckc = game.get_deck_compat_category()
        deckt = game.get_deck_recommended_tool()

        if deckc == SteamDeckCompatEnum.UNKNOWN:
            return self.tr('Unknown')
        elif deckc == SteamDeckCompatEnum.UNSUPPORTED:
            return self.tr('Unsupported')
        elif deckc == SteamDeckCompatEnum.PLAYABLE:
            if deckt == '':
                return self.tr('Playable')
            elif deckt == 'native':
                return self.tr('Native (playable)')
            else:
                return self.tr('Playable using {compat_tool}').format(compat_tool=deckt)
        elif deckc == SteamDeckCompatEnum.VERIFIED:
            if deckt == '':
                return self.tr('Verified')
            elif deckt == 'native':
                return self.tr('Native (verified)')
            else:
                return self.tr('Verified for {compat_tool}').format(compat_tool=deckt)
        else:
            return ''
