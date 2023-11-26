import os
import pkgutil
import requests

from PySide6.QtCore import Qt, QObject, QDataStream, QByteArray, QSize
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtUiTools import QUiLoader

from pupgui2.constants import APP_NAME, APP_VERSION, APP_GHAPI_URL, ABOUT_TEXT, BUILD_INFO, APP_THEMES
from pupgui2.constants import DAVIDOTEK_KOFI_URL, PROTONUPQT_GITHUB_URL
from pupgui2.steamutil import install_steam_library_shortcut
from pupgui2.util import config_theme, apply_dark_theme, config_advanced_mode
from pupgui2.util import open_webbrowser_thread
from pupgui2.util import install_directory


class PupguiAboutDialog(QObject):

    def __init__(self, parent=None):
        super(PupguiAboutDialog, self).__init__(parent)
        self.parent = parent
        self.is_update_available = lambda current, newest: tuple(map(int, current.split('.'))) < tuple(map(int, newest.split('.')))

        self.load_ui()
        self.setup_ui()
        self.ui.show()

        self.ui.setFixedSize(self.ui.size())

    def load_ui(self):
        data = pkgutil.get_data(__name__, 'resources/ui/pupgui2_aboutdialog.ui')
        ui_file = QDataStream(QByteArray(data))
        self.ui = QUiLoader().load(ui_file.device())

    def setup_ui(self):
        self.ui.setWindowTitle(f'{APP_NAME} {APP_VERSION}')

        translator_text = QApplication.instance().translate('translator-text', 'Translated by DavidoTek')

        self.ui.lblAppIcon.setPixmap(QIcon.fromTheme('net.davidotek.pupgui2').pixmap(QSize(96, 96)))

        self.ui.lblAboutTranslator.setText(translator_text)
        self.ui.lblAboutVersion.setTextFormat(Qt.RichText)
        self.ui.lblAboutVersion.setOpenExternalLinks(True)
        self.ui.lblAboutVersion.setText(ABOUT_TEXT)

        self.ui.lblBuildInfo.setText(BUILD_INFO)

        try:
            p = QPixmap()
            p.loadFromData(pkgutil.get_data(__name__, 'resources/img/kofi_button_blue.png'))
            self.ui.btnDonate.setIcon(QIcon(p))
            self.ui.btnDonate.setIconSize(p.rect().size())
            self.ui.btnDonate.setFlat(True)
        finally:
            self.ui.btnDonate.setText('')
        self.ui.btnDonate.clicked.connect(lambda: open_webbrowser_thread(DAVIDOTEK_KOFI_URL))

        self.ui.btnGitHub.clicked.connect(lambda: open_webbrowser_thread(PROTONUPQT_GITHUB_URL))

        self.ui.comboColorTheme.addItems([self.tr('light'), self.tr('dark'), self.tr('system (restart required)')])
        self.ui.comboColorTheme.setCurrentIndex(APP_THEMES.index(config_theme()) if config_theme() in APP_THEMES else (len(APP_THEMES) - 1))

        self.ui.btnClose.clicked.connect(lambda: self.ui.close())
        self.ui.btnAboutQt.clicked.connect(lambda: QMessageBox.aboutQt(self.parent))
        self.ui.btnCheckForUpdates.clicked.connect(self.btn_check_for_updates_clicked)
        self.ui.comboColorTheme.currentIndexChanged.connect(self.combo_color_theme_current_index_changed)

        self.ui.checkAdvancedMode.setChecked(config_advanced_mode() == 'enabled')
        self.ui.checkAdvancedMode.stateChanged.connect(lambda: config_advanced_mode('enabled' if self.ui.checkAdvancedMode.isChecked() else 'disabled'))

        self.ui.btnAddSteamShortcut.clicked.connect(self.btn_add_steam_shortcut_clicked)
        self.ui.btnCheckForUpdates.setVisible(os.getenv('APPIMAGE') is not None)

    def combo_color_theme_current_index_changed(self):
        config_theme(APP_THEMES[:-1][self.ui.comboColorTheme.currentIndex()])
        apply_dark_theme(QApplication.instance())

    def btn_check_for_updates_clicked(self):
        releases = requests.get(f'{APP_GHAPI_URL}?per_page=1').json()
        if len(releases) == 0:
            return

        newest_release = releases[0]
        v_newest = newest_release.get('tag_name', 'v0.0.0').replace('v', '')

        if self.is_update_available(APP_VERSION, v_newest):
            QMessageBox.information(
                self.ui,
                self.tr('Update available'),
                self.tr('There is a newer version available.\nYou are running {APP_VERSION} but {newest_version} is available.').format(APP_VERSION=f'v{APP_VERSION}', newest_version=f'v{v_newest}')
            )
            open_webbrowser_thread(newest_release['html_url'])
        else:
            QMessageBox.information(self.ui, self.tr('Up to date'), self.tr('You are running the newest version!'))

    def btn_add_steam_shortcut_clicked(self):
        result = install_steam_library_shortcut(install_directory())
        if result != 1:
            self.ui.btnAddSteamShortcut.setText(self.tr('Added shortcut!'))
            self.ui.btnAddSteamShortcut.setEnabled(False)
