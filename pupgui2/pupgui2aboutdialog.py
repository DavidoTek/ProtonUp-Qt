import os, requests

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtUiTools import QUiLoader

from constants import APP_NAME, APP_VERSION, APP_GHAPI_URL, ABOUT_TEXT
from util import config_theme, apply_dark_theme
from util import download_steam_app_list_thread
from util import open_webbrowser_thread


class PupguiAboutDialog(QObject):

    def __init__(self, pupgui2_base_dir, parent=None):
        super(PupguiAboutDialog, self).__init__(parent)
        self.pupgui2_base_dir = pupgui2_base_dir
        self.parent = parent

        self.load_ui()
        self.setup_ui()
        self.ui.show()

        self.ui.setFixedSize(self.ui.size())

    def load_ui(self):
        ui_file_name = os.path.join(self.pupgui2_base_dir, 'ui/pupgui2_aboutdialog.ui')
        ui_file = QFile(ui_file_name)
        if not ui_file.open(QIODevice.ReadOnly):
            print(f'Cannot open {ui_file_name}: {ui_file.errorString()}')
            return
        loader = QUiLoader()
        self.ui = loader.load(ui_file, self.parent)
        ui_file.close()

    def setup_ui(self):
        self.ui.setWindowTitle(APP_NAME + ' ' + APP_VERSION)

        self.ui.lblAppIcon.setPixmap(QIcon.fromTheme('net.davidotek.pupgui2').pixmap(QSize(96, 96)))
        self.ui.lblAboutText.setText(ABOUT_TEXT)
        self.ui.lblAboutText.setTextFormat(Qt.RichText)
        self.ui.lblAboutText.setOpenExternalLinks(True)
        self.ui.comboColorTheme.addItems([self.tr('light'), self.tr('dark'), self.tr('system (restart required)')])
        self.ui.comboColorTheme.setCurrentIndex(['light', 'dark', 'system', None].index(config_theme()))

        self.ui.btnClose.clicked.connect(self.btn_close_clicked)
        self.ui.btnAboutQt.clicked.connect(self.btn_aboutqt_clicked)
        self.ui.btnCheckForUpdates.clicked.connect(self.btn_check_for_updates_clicked)
        self.ui.comboColorTheme.currentIndexChanged.connect(self.combo_color_theme_current_index_changed)

        if os.getenv('APPIMAGE') is None:
            self.ui.btnCheckForUpdates.setText(self.tr('Update Steam game list'))

    def combo_color_theme_current_index_changed(self):
        config_theme(['light', 'dark', 'system'][self.ui.comboColorTheme.currentIndex()])
        apply_dark_theme(QApplication.instance())

    def btn_close_clicked(self):
        self.ui.close()

    def btn_aboutqt_clicked(self):
        QMessageBox.aboutQt(self.parent)

    def btn_check_for_updates_clicked(self):
        if os.getenv('APPIMAGE'):
            releases = requests.get(APP_GHAPI_URL + '?per_page=1').json()
            if len(releases) == 0:
                return
            newest_release = releases[0]
            v_current = self.tag_name_to_version(APP_VERSION)
            v_newest = self.tag_name_to_version(newest_release['tag_name'])
            if (10000 * int(v_current[0]) + 100 * int(v_current[1]) + int(v_current[2])) < (10000 * int(v_newest[0]) + 100 * int(v_newest[1]) + int(v_newest[2])):
                QMessageBox.information(self.ui, self.tr('Update available'),
                self.tr('There is a newer version available.\nYou are running {APP_VERSION} but {newest_version} is available.')
                .format(APP_VERSION='v' + APP_VERSION, newest_version=newest_release['tag_name']))
                open_webbrowser_thread(newest_release['html_url'])
            else:
                QMessageBox.information(self.ui, self.tr('Up to date'), self.tr('You are running the newest version!'))
        download_steam_app_list_thread(force_download=True)

    def tag_name_to_version(self, tag_name : str):
        tag_name = tag_name.replace('v', '')
        vers = tag_name.split('.')
        if len(vers) != 3:
            return [0, 0, 0]
        return vers
