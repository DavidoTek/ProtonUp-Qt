#!/usr/bin/env python3
import sys
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from protonup_mainwindow import Ui_MainWindow
from pupgui_installdialog import PupguiInstallDialog

import protonup.api as papi


APP_NAME = 'ProtonUp-Qt'
APP_VERSION = '1.4.0'
PROTONUP_VERSION = '0.1.4'  # same as in requirements.txt


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

        self.ui.comboInstallDirectory.addItem(papi.install_directory())

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
