import pkgutil

from pupgui2.constants import STEAM_APP_PAGE_URL
from pupgui2.datastructures import BasicCompatTool, CTType
from pupgui2.lutrisutil import get_lutris_game_list
from pupgui2.pupgui2ctbatchupdatedialog import PupguiCtBatchUpdateDialog
from pupgui2.steamutil import get_steam_game_list
from pupgui2.util import open_webbrowser_thread

from PySide6.QtCore import QObject, Signal, QDataStream, QByteArray
from PySide6.QtWidgets import QTableWidgetItem
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import Qt

class PupguiCtInfoDialog(QObject):

    batch_update_complete = Signal(bool)

    def __init__(self, parent=None, ctool: BasicCompatTool = None, install_loc=None):
        super(PupguiCtInfoDialog, self).__init__(parent)
        self.parent = parent
        self.ctool = ctool
        self.games = []
        self.install_loc = install_loc

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

        if self.install_loc.get('launcher') == 'steam' and 'vdf_dir' in self.install_loc:
            if self.ctool.ct_type != CTType.STEAM_RT:
                self.update_game_list_steam()
                if 'Proton' in self.ctool.displayname and self.ctool.ct_type == CTType.CUSTOM:  # 'batch update' option for Proton-GE
                    self.ui.btnBatchUpdate.setVisible(True)
                    self.ui.btnBatchUpdate.clicked.connect(self.btn_batch_update_clicked)
        elif self.install_loc.get('launcher') == 'lutris':
            self.update_game_list_lutris()
        else:
            self.ui.txtNumGamesUsingTool.setText('-')
            self.ui.listGames.setHorizontalHeaderLabels(['', ''])
            self.ui.listGames.setEnabled(False)

        self.ui.btnClose.clicked.connect(self.btn_close_clicked)

        self.ui.listGames.cellDoubleClicked.connect(self.list_games_cell_double_clicked)

    def update_game_list_steam(self):
        if self.install_loc.get('launcher') == 'steam' and 'vdf_dir' in self.install_loc:
            self.games = get_steam_game_list(self.install_loc.get('vdf_dir'), self.ctool.get_internal_name())
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
        self.ui.listGames.clear()

        lutris_games = [game for game in get_lutris_game_list(self.install_loc) if game.runner == 'wine' and game.get_game_config().get('wine', {}).get('version') == self.ctool.displayname]

        self.ui.listGames.setRowCount(len(lutris_games))
        self.ui.listGames.setHorizontalHeaderLabels([self.tr('Slug'), self.tr('Name')])
        self.ui.txtNumGamesUsingTool.setText(str(len(lutris_games)))
        for i, game in enumerate(lutris_games):
            self.ui.listGames.setItem(i, 0, QTableWidgetItem(game.slug))
            self.ui.listGames.setItem(i, 1, QTableWidgetItem(game.name))

    def btn_close_clicked(self):
        self.ui.close()

    def list_games_cell_double_clicked(self, row):
        if self.install_loc.get('launcher') == 'steam':
            steam_game_id = str(self.ui.listGames.item(row, 0).text())
            open_webbrowser_thread(STEAM_APP_PAGE_URL + steam_game_id)

    def btn_batch_update_clicked(self):
        steam_config_folder = self.install_loc.get('vdf_dir')
        ctbu_dialog = PupguiCtBatchUpdateDialog(parent=self.ui, games=self.games, steam_config_folder=steam_config_folder)
        ctbu_dialog.batch_update_complete.connect(self.update_game_list_steam)
