import os, requests

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtUiTools import QUiLoader

from constants import APP_NAME, APP_VERSION, APP_GHAPI_URL, ABOUT_TEXT
from util import config_theme, apply_dark_theme
from util import download_steam_app_list_thread
from util import open_webbrowser_thread


class PupguiGameListDialog(QObject):

    def __init__(self, pupgui2_base_dir, parent=None):
        super(PupguiGameListDialog, self).__init__(parent)
        self.pupgui2_base_dir = pupgui2_base_dir
        self.parent = parent

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
        self.ui.btnClose.clicked.connect(self.btn_close_clicked)

    def btn_close_clicked(self):
        self.ui.close()
