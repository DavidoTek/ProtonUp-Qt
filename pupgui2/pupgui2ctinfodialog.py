import pkgutil
import os

from .datastructures import BasicCompatTool, CTType
from .util import open_webbrowser_thread
from .steamutil import get_steam_game_list
from .lutrisutil import get_lutris_game_list
from .constants import STEAM_APP_PAGE_URL

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtUiTools import QUiLoader

from .pupgui2ctbatchupdatedialog import PupguiCtBatchUpdateDialog


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
        else:
            self.update_game_list_lutris()

        self.ui.btnClose.clicked.connect(self.btn_close_clicked)

        self.ui.listGames.itemDoubleClicked.connect(self.list_games_item_double_clicked)

    def update_game_list_steam(self):
        if self.install_loc.get('launcher') == 'steam' and 'vdf_dir' in self.install_loc:
            self.games = get_steam_game_list(self.install_loc.get('vdf_dir'), self.ctool.displayname)
            self.ui.txtNumGamesUsingTool.setText(str(len(self.games)))

        self.ui.listGames.clear()
        for game in self.games:
            self.ui.listGames.addItem(game.get_app_id_str() + ': ' + game.game_name)

        self.batch_update_complete.emit(True)

    def update_game_list_lutris(self):
        self.ui.listGames.clear()
        for game in get_lutris_game_list(self.install_loc):
            if game.runner == 'wine':
                cfg = game.get_game_config()
                if self.ctool.displayname == cfg.get('wine', {}).get('version'):
                    self.ui.listGames.addItem(game.name)

    def btn_close_clicked(self):
        self.ui.close()

    def list_games_item_double_clicked(self, item):
        if self.install_loc.get('launcher') == 'steam':
            steam_game_id = item.text().split(':')[0]
            if not steam_game_id == '-1':
                open_webbrowser_thread(STEAM_APP_PAGE_URL + steam_game_id)

    def btn_batch_update_clicked(self):
        steam_config_folder = self.install_loc.get('vdf_dir')
        ctbu_dialog = PupguiCtBatchUpdateDialog(parent=self.ui, games=self.games, steam_config_folder=steam_config_folder)
        ctbu_dialog.batch_update_complete.connect(self.update_game_list_steam)
