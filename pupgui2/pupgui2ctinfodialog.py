import pkgutil
import os

from pupgui2.constants import STEAM_APP_PAGE_URL
from pupgui2.datastructures import BasicCompatTool, CTType, SteamApp, LutrisGame, HeroicGame
from pupgui2.lutrisutil import get_lutris_game_list, is_lutris_game_using_wine
from pupgui2.pupgui2ctbatchupdatedialog import PupguiCtBatchUpdateDialog
from pupgui2.steamutil import get_steam_game_list
from pupgui2.util import open_webbrowser_thread, get_random_game_name
from pupgui2.heroicutil import get_heroic_game_list, is_heroic_launcher

from PySide6.QtCore import QObject, Signal, QDataStream, QByteArray
from PySide6.QtWidgets import QTableWidgetItem
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import Qt
from PySide6.QtGui import QShortcut, QKeySequence


class PupguiCtInfoDialog(QObject):

    batch_update_complete = Signal(bool)

    def __init__(self, parent=None, ctool: BasicCompatTool = None, install_loc=None):
        super(PupguiCtInfoDialog, self).__init__(parent)
        self.parent = parent
        self.ctool = ctool
        self.games: list[SteamApp | LutrisGame | HeroicGame] = []
        self.install_loc = install_loc
        self.is_batch_update_available = False

        self.load_ui()
        self.setup_ui()
        self.ui.show()

    def load_ui(self):
        data = pkgutil.get_data(__name__, 'resources/ui/pupgui2_ctinfodialog.ui')
        ui_file = QDataStream(QByteArray(data))
        loader = QUiLoader()
        self.ui = loader.load(ui_file.device())

    def setup_ui(self):
        self.ui.txtToolName.setText(self.ctool.displayname)
        self.ui.txtLauncherName.setText(self.install_loc.get('display_name'))
        self.ui.txtInstallDirectory.setText(self.ctool.get_install_dir())
        self.ui.btnBatchUpdate.setVisible(False)
        self.ui.searchBox.setVisible(False)

        self.update_game_list()

        self.ui.btnSearch.clicked.connect(self.btn_search_clicked)
        self.ui.btnRefreshGames.clicked.connect(self.btn_refresh_games_clicked)
        self.ui.btnClose.clicked.connect(lambda: self.ui.close())
        self.ui.listGames.cellDoubleClicked.connect(self.list_games_cell_double_clicked)
        self.ui.searchBox.textChanged.connect(self.search_ctinfo_games)

        QShortcut(QKeySequence.Find, self.ui).activated.connect(self.btn_search_clicked)

    def update_game_list(self, cached=True):
        if self.install_loc.get('launcher') == 'steam' and 'vdf_dir' in self.install_loc:
            self.update_game_list_steam(cached=cached)
            if 'Proton' in self.ctool.displayname and self.ctool.ct_type == CTType.CUSTOM:  # 'batch update' option for Proton-GE
                self.is_batch_update_available = True
                self.ui.btnBatchUpdate.setVisible(not self.ui.searchBox.isVisible())
                self.ui.btnBatchUpdate.clicked.connect(self.btn_batch_update_clicked)
        elif self.install_loc.get('launcher') == 'lutris':
            self.update_game_list_lutris()
        elif is_heroic_launcher(self.install_loc.get('launcher')):
            self.update_game_list_heroic()
        else:
            self.ui.txtNumGamesUsingTool.setText('-')
            self.ui.listGames.setHorizontalHeaderLabels(['', ''])
            self.ui.listGames.setEnabled(False)

        self.update_game_list_ui()

    def update_game_list_steam(self, cached=True):
        if self.install_loc.get('launcher') == 'steam' and 'vdf_dir' in self.install_loc:
            self.games = get_steam_game_list(self.install_loc.get('vdf_dir'), self.ctool, cached=cached)
            self.ui.txtNumGamesUsingTool.setText(str(len(self.games)))

        self.ui.listGames.clear()
        self.ui.listGames.setRowCount(len(self.games))
        self.ui.listGames.setHorizontalHeaderLabels([self.tr('AppID'), self.tr('Name')])
        for i, game in enumerate(self.games):
            dataitem_appid = QTableWidgetItem()
            dataitem_appid.setData(Qt.DisplayRole, int(game.get_app_id_str()))

            self.ui.listGames.setItem(i, 0, dataitem_appid)
            self.ui.listGames.setItem(i, 1, QTableWidgetItem(game.game_name))

        self.batch_update_complete.emit(True)

    def update_game_list_lutris(self):
        self.games = [game for game in get_lutris_game_list(self.install_loc) if is_lutris_game_using_wine(game, self.ctool.displayname)]

        self.setup_game_list(len(self.games), [self.tr('Slug'), self.tr('Name')])

        for i, game in enumerate(self.games):
            self.ui.listGames.setItem(i, 0, QTableWidgetItem(game.slug))
            self.ui.listGames.setItem(i, 1, QTableWidgetItem(game.name))

    def update_game_list_heroic(self):
        heroic_dir = os.path.join(os.path.expanduser(self.install_loc.get('install_dir')), '../..')
        self.games = [game for game in get_heroic_game_list(heroic_dir) if game.is_installed and self.ctool.displayname in game.wine_info.get('name', '')]

        self.setup_game_list(len(self.games), [self.tr('Runner'), self.tr('Game')])

        for i, game in enumerate(self.games):
            self.ui.listGames.setItem(i, 0, QTableWidgetItem(game.runner))
            self.ui.listGames.setItem(i, 1, QTableWidgetItem(game.title))

    def setup_game_list(self, row_count: int, header_labels: list[str]):
        self.ui.listGames.clear()
        self.ui.listGames.setRowCount(row_count)
        self.ui.listGames.setHorizontalHeaderLabels(header_labels)
        self.ui.txtNumGamesUsingTool.setText(str(row_count))        

    def update_game_list_ui(self):
        # switch between showing the QTableWidget (listGames) or the QLabel (lblGamesList)
        self.ui.stackTableOrText.setCurrentIndex(0 if len(self.games) > 0 and not self.ctool.is_global else 1)
        self.ui.btnBatchUpdate.setEnabled(len(self.games) > 0 and not self.ctool.is_global)
        self.ui.btnSearch.setEnabled(len(self.games) > 0 and not self.ctool.is_global)

        if self.ctool.is_global:
            self.ui.lblGamesList.setText(self.tr('Tool is Global'))

        if len(self.games) < 0 or self.ctool.is_global:
            self.ui.btnClose.setFocus()

    def list_games_cell_double_clicked(self, row):
        if self.install_loc.get('launcher') == 'steam':
            steam_game_id = str(self.ui.listGames.item(row, 0).text())
            open_webbrowser_thread(STEAM_APP_PAGE_URL + steam_game_id)

    def btn_batch_update_clicked(self):
        steam_config_folder = self.install_loc.get('vdf_dir')
        ctbu_dialog = PupguiCtBatchUpdateDialog(parent=self.ui, current_ctool_name=self.ctool.displayname, games=self.games, steam_config_folder=steam_config_folder)
        ctbu_dialog.batch_update_complete.connect(self.update_game_list_steam)

    def btn_refresh_games_clicked(self):
        self.update_game_list(cached=False)

    def btn_search_clicked(self):
        if not self.ui.btnSearch.isEnabled():
            return

        # Generate random tooltip here, updating so if a game is removed on refresh, we won't list a game no longer listed
        # If game is not found, fall back to tooltip defined in UI file
        if tooltip_game_name := get_random_game_name(self.games):
            self.ui.searchBox.setToolTip(self.tr('e.g. {GAME_NAME}').format(GAME_NAME=tooltip_game_name))

        self.ui.searchBox.setVisible(not self.ui.searchBox.isVisible())
        self.ui.btnBatchUpdate.setVisible(self.is_batch_update_available and not self.ui.searchBox.isVisible())
        self.ui.searchBox.setFocus()

        self.search_ctinfo_games(self.ui.searchBox.text() if self.ui.searchBox.isVisible() else '')

    def search_ctinfo_games(self, text):
        for row in range(self.ui.listGames.rowCount()):
            should_hide: bool = not text.lower() in self.ui.listGames.item(row, 1).text().lower()
            self.ui.listGames.setRowHidden(row, should_hide)
