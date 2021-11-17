import os, requests, webbrowser
from re import S

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtUiTools import QUiLoader

from constants import APP_NAME, APP_VERSION, APP_GHAPI_URL, ABOUT_TEXT
from util import config_theme, apply_dark_theme


class PupguiCtInfoDialog(QObject):

    def __init__(self, pupgui2_base_dir, parent=None, ctool='', games=[], install_loc=None, install_dir=''):
        super(PupguiCtInfoDialog, self).__init__(parent)
        self.pupgui2_base_dir = pupgui2_base_dir
        self.parent = parent
        self.ctool = ctool
        self.games = games
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

        if self.install_loc.get('launcher') == 'steam' and 'vdf_dir' in self.install_loc:
            self.ui.txtNumGamesUsingTool.setText(str(len(self.games)))
        else:
            self.ui.txtNumGamesUsingTool.setText(self.tr('todo'))

        self.ui.btnClose.clicked.connect(self.btn_close_clicked)

        for game in self.games:
            self.ui.listGames.addItem(game)

    def btn_close_clicked(self):
        self.ui.close()
