import os
from util import open_webbrowser_thread
from steamutil import get_steam_game_list
from constants import STEAM_APP_PAGE_URL

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtUiTools import QUiLoader

from pupgui2ctbatchupdatedialog import PupguiCtBatchUpdateDialog


class PupguiCtInfoDialog(QObject):

    batch_update_complete = Signal(bool)

    def __init__(self, pupgui2_base_dir, parent=None, ctool='', install_loc=None, install_dir=''):
        super(PupguiCtInfoDialog, self).__init__(parent)
        self.pupgui2_base_dir = pupgui2_base_dir
        self.parent = parent
        self.ctool = ctool
        self.games = []
        self.install_loc = install_loc
        self.install_dir = install_dir

        self.load_ui()
        self.setup_ui()
        self.ui.show()

    def load_ui(self):
        ui_file_name = os.path.join(self.pupgui2_base_dir, 'ui/pupgui2_ctinfodialog.ui')
        ui_file = QFile(ui_file_name)
        if not ui_file.open(QIODevice.ReadOnly):
            print(f'Cannot open {ui_file_name}: {ui_file.errorString()}')
            return
        loader = QUiLoader()
        self.ui = loader.load(ui_file, self.parent)
        ui_file.close()
    
    def setup_ui(self):
        self.ui.txtToolName.setText(self.ctool)
        self.ui.txtLauncherName.setText(self.install_loc.get('display_name'))
        self.ui.txtInstallDirectory.setText(self.install_dir)
        self.ui.btnBatchUpdate.setVisible(False)

        self.update_game_list()

        if self.install_loc.get('launcher') == 'steam' and 'vdf_dir' in self.install_loc:
            if 'Proton' in self.ctool:  # 'batch update' option for Proton-GE
                self.ui.btnBatchUpdate.setVisible(True)
                self.ui.btnBatchUpdate.clicked.connect(self.btn_batch_update_clicked)
        else:
            self.ui.txtNumGamesUsingTool.setText(self.tr('todo'))

        self.ui.btnClose.clicked.connect(self.btn_close_clicked)

        self.ui.listGames.itemDoubleClicked.connect(self.list_games_item_double_clicked)

    def update_game_list(self):
        if self.install_loc.get('launcher') == 'steam' and 'vdf_dir' in self.install_loc:
            self.games = get_steam_game_list(self.install_loc.get('vdf_dir'), self.ctool)
            self.ui.txtNumGamesUsingTool.setText(str(len(self.games)))
        
        self.ui.listGames.clear()
        for game in self.games:
            self.ui.listGames.addItem(game.get_app_id_str() + ': ' + game.game_name)

        self.batch_update_complete.emit(True)

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
        ctbu_dialog.batch_update_complete.connect(self.update_game_list)
