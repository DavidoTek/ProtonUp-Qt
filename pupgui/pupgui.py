#!/usr/bin/env python3
import sys, os, subprocess
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from pupgui_mainwindow import Ui_MainWindow
from pupgui_installdialog import PupguiInstallDialog

import protonup.api as papi


APP_NAME = 'ProtonUp-Qt'
APP_VERSION = '1.4.4'
PROTONUP_VERSION = '0.1.4'  # same as in requirements.txt


POSSIBLE_INSTALL_LOCATIONS = [
    {'install_dir': '~/.steam/root/compatibilitytools.d/', 'display_name': 'Steam'},
    {'install_dir': '~/.var/app/com.valvesoftware.Steam/data/Steam/compatibilitytools.d/', 'display_name': 'Steam (Flatpak)'}
]
def available_install_directories():
    """
    List available install directories
    Return Type: str[]
    """
    available_dirs = []
    for loc in POSSIBLE_INSTALL_LOCATIONS:
        install_dir = os.path.expanduser(loc['install_dir'])
        if os.path.exists(install_dir):
            available_dirs.append(install_dir)
    return available_dirs


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.pending_proton_downloads = []

        self._available_releases = []

        self.ui.btnAddVersion.clicked.connect(self.btnAddVersionClicked)
        self.ui.btnRemoveSelected.clicked.connect(self.btnRemoveSelectedClicked)
        self.ui.btnClose.clicked.connect(self.btnCloseClicked)
        self.ui.btnAbout.clicked.connect(self.btnAboutClicked)

        i = 0
        current_install_dir = papi.install_directory()
        for install_dir in available_install_directories():
            self.ui.comboInstallDirectory.addItem(QIcon.fromTheme('steam'), install_dir)
            if current_install_dir == install_dir:
                self.ui.comboInstallDirectory.setCurrentIndex(i)
            i += 1

        self.ui.comboInstallDirectory.currentIndexChanged.connect(self.comboInstallDirectoryCurrentIndexChanged)

        self.updateInfo()
        self._available_releases = papi.fetch_releases()    # ToDo: separate thread

        app_status_label = QLabel(APP_NAME + ' ' + APP_VERSION)
        self.ui.statusBar.addPermanentWidget(app_status_label)

        self.setWindowIcon(QIcon.fromTheme('pupgui'))

    def btnAddVersionClicked(self):
        PupguiInstallDialog(self).show()

    def btnRemoveSelectedClicked(self):
        for item in self.ui.listInstalledVersions.selectedItems():
            ver = item.text().replace('Proton-', '')
            papi.remove_proton(ver)
            self.ui.statusBar.showMessage('Removed Proton-' + ver)
        self.updateInfo()

    def btnCloseClicked(self):
        self.close()
    
    def btnAboutClicked(self):
        QMessageBox.about(self, 'About ' + APP_NAME + ' ' + APP_VERSION, APP_NAME + ' v' + APP_VERSION + ' by DavidoTek: https://github.com/DavidoTek/ProtonUp-Qt\nGUI for ProtonUp v' + PROTONUP_VERSION + ': https://github.com/AUNaseef/protonup\n\nCopyright (C) 2021 DavidoTek, licensed under GPLv3')
        QMessageBox.aboutQt(self)

    def comboInstallDirectoryCurrentIndexChanged(self):
        install_dir = papi.install_directory(self.ui.comboInstallDirectory.currentText())
        self.ui.statusBar.showMessage('Changed install directory to ' + install_dir)
        self.updateInfo()

    def updateInfo(self, only_update_downloads=False):
        self.ui.txtActiveDownloads.setText(str(len(self.pending_proton_downloads)))
        if(len(self.pending_proton_downloads) > 0):
            self.ui.comboInstallDirectory.setEnabled(False)
        else:
            self.ui.comboInstallDirectory.setEnabled(True)
        
        if only_update_downloads:
            return
        # installed versions
        self.ui.listInstalledVersions.clear()
        for item in papi.installed_versions():
            self.ui.listInstalledVersions.addItem(item)


def apply_dark_theme(app):
    is_plasma = 'plasma' in os.environ.get('DESKTOP_SESSION')
    darkmode_enabled = False
    
    try:
        ret = subprocess.run(['gsettings', 'get', 'org.gnome.desktop.interface', 'gtk-theme'], capture_output=True).stdout.decode('utf-8').strip().strip("'").lower()
        if ret.endswith('-dark'):
            darkmode_enabled = True
    except:
        pass

    if not is_plasma and darkmode_enabled:
        app.setStyle("Fusion")

        palette_dark = QPalette()
        palette_dark.setColor(QPalette.Window, QColor(30, 30, 30))
        palette_dark.setColor(QPalette.WindowText, Qt.white)
        palette_dark.setColor(QPalette.Base, QColor(12, 12, 12))
        palette_dark.setColor(QPalette.AlternateBase, QColor(30, 30, 30))
        palette_dark.setColor(QPalette.ToolTipBase, Qt.white)
        palette_dark.setColor(QPalette.ToolTipText, Qt.white)
        palette_dark.setColor(QPalette.Text, Qt.white)
        palette_dark.setColor(QPalette.Button, QColor(30, 30, 30))
        palette_dark.setColor(QPalette.ButtonText, Qt.white)
        palette_dark.setColor(QPalette.BrightText, Qt.red)
        palette_dark.setColor(QPalette.Link, QColor(40, 120, 200))
        palette_dark.setColor(QPalette.Highlight, QColor(40, 120, 200))
        palette_dark.setColor(QPalette.HighlightedText, Qt.black)

        app.setPalette(palette_dark)


if __name__ == '__main__':
    app = QApplication(sys.argv)

    apply_dark_theme(app)

    window = MainWindow()
    window.show()

    sys.exit(app.exec()) 
