import threading, webbrowser

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

import pupgui_lutrisup as wapi
from pupgui_utils import install_directory


class installProtonThread(threading.Thread):
    def __init__(self, main_window):
        threading.Thread.__init__(self)
        self.main_window = main_window
    
    def run(self):
        while True:
            if len(self.main_window.pending_proton_downloads) == 0:
                break
            winege_version = self.main_window.pending_proton_downloads[0]
            try:
                if winege_version in wapi.installed_versions(install_directory()):
                    wapi.remove_proton(winege_version)
                    self.main_window.ui.statusBar.showMessage('Reinstalling WineGE-' + winege_version + '...')
                else:
                    self.main_window.ui.statusBar.showMessage('Installing WineGE-' + winege_version + '...')
                self.main_window.updateInfo(only_update_downloads=True)
                wapi.get_winege(install_directory(), winege_version, main_window=self.main_window)
                self.main_window.ui.statusBar.showMessage('Installed WineGE-' + winege_version)
            except:
                self.main_window.ui.statusBar.showMessage('Error installing WineGE-' + winege_version + '...')
            self.main_window.pending_proton_downloads.remove(winege_version)
            self.main_window.updateInfo()


class PupguiInstallDialogLutris(QDialog):
    def __init__(self, parent=None):
        super(PupguiInstallDialogLutris, self).__init__(parent)
        self.main_window = parent
        self.setupUi()
    
    def setupUi(self):
        self.setFixedSize(250, 100)
        self.setWindowTitle('Install Wine-GE')

        self.btnInfo = QPushButton('Info')
        self.btnInstall = QPushButton('Install')
        self.btnCancel = QPushButton('Cancel')

        button_box = QHBoxLayout()
        button_box.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        button_box.addWidget(self.btnInfo)
        button_box.addWidget(self.btnInstall)
        button_box.addWidget(self.btnCancel)

        self.comboProtonVersion = QComboBox()
        self.main_window.ui.statusBar.showMessage('Fetching releases...')
        try:
            for item in wapi.fetch_releases():
                self.comboProtonVersion.addItem(item)
            self.main_window.ui.statusBar.clearMessage()
        except:
            self.main_window.ui.statusBar.showMessage('Could not fetch releases.')

        vbox = QVBoxLayout()
        vbox.addWidget(QLabel('Select Wine-GE version to be installed'))
        vbox.addWidget(self.comboProtonVersion)
        vbox.addLayout(button_box)

        self.setLayout(vbox)

        self.btnInfo.clicked.connect(self.btnInfoClicked)
        self.btnInstall.clicked.connect(self.btnInstallClicked)
        self.btnCancel.clicked.connect(self.btnCancelClicked)
        self.comboProtonVersion.currentIndexChanged.connect(self.comboProtonVersionCurrentIndexChanged)
        
        self.checkCurrentVersionInstallStatus()
    
    def btnInfoClicked(self):
        webbrowser.open('https://github.com/GloriousEggroll/proton-ge-custom/releases/tag/' + self.comboProtonVersion.currentText())

    def btnInstallClicked(self):
        current_version = self.comboProtonVersion.currentText()
        if current_version in self.main_window.pending_proton_downloads:
            self.close()
            return
        self.main_window.pending_proton_downloads.append(current_version)
        self.main_window.updateInfo(only_update_downloads=True)
        if len(self.main_window.pending_proton_downloads) == 1:
            install_thread = installProtonThread(self.main_window)
            install_thread.start()
        self.close()

    def btnCancelClicked(self):
        self.close()

    def comboProtonVersionCurrentIndexChanged(self):
        self.checkCurrentVersionInstallStatus()
    
    def checkCurrentVersionInstallStatus(self):
        current_version = 'Proton-' + self.comboProtonVersion.currentText()
        if current_version in wapi.installed_versions(install_directory()):
            self.btnInstall.setText('Reinstall')
            return True
        else:
            self.btnInstall.setText('Install')
            return False
