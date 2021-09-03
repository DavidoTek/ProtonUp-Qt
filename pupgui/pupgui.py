#!/usr/bin/env python3
import sys, os
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from protonup_mainwindow import Ui_MainWindow
from pupgui_installdialog import PupguiInstallDialog

import protonup.api as papi


APP_NAME = 'ProtonUp-Qt'
APP_VERSION = '1.4.1'
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

        self._available_releases = []

        self.ui.btnAddVersion.clicked.connect(self.btnAddVersionClicked)
        self.ui.btnRemoveSelected.clicked.connect(self.btnRemoveSelectedClicked)
        self.ui.btnClose.clicked.connect(self.btnCloseClicked)
        self.ui.btnAbout.clicked.connect(self.btnAboutClicked)

        i = 0
        current_install_dir = papi.install_directory()
        for install_dir in available_install_directories():
            self.ui.comboInstallDirectory.addItem(install_dir)
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
        current = self.ui.listInstalledVersions.currentItem()
        if not current:
            return
        ver = current.text().replace('Proton-', '')
        papi.remove_proton(ver)
        self.ui.statusBar.showMessage('Removed Proton-' + ver, timeout=3000)
        self.updateInfo()

    def btnCloseClicked(self):
        self.close()
    
    def btnAboutClicked(self):
        QMessageBox.about(self, 'About ' + APP_NAME + ' ' + APP_VERSION, APP_NAME + ' v' + APP_VERSION + ' by DavidoTek: https://github.com/DavidoTek/ProtonUp-Qt\nGUI for ProtonUp v' + PROTONUP_VERSION + ': https://github.com/AUNaseef/protonup\n\nCopyright (C) 2021 DavidoTek, licensed under GPLv3')
        QMessageBox.aboutQt(self)

    def comboInstallDirectoryCurrentIndexChanged(self):
        install_dir = papi.install_directory(self.ui.comboInstallDirectory.currentText())
        self.ui.statusBar.showMessage('Changed install directory to ' + install_dir, timeout=3000)
        self.updateInfo()

    def updateInfo(self):
        # installed versions
        self.ui.listInstalledVersions.clear()
        for item in papi.installed_versions():
            self.ui.listInstalledVersions.addItem(item)

if __name__ == '__main__':
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec()) 
