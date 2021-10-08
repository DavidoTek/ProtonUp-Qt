import threading, webbrowser

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

import protonup.api as papi


class installProtonThread(threading.Thread):
    def __init__(self, proton_version, main_window, is_reinstall=False):
        threading.Thread.__init__(self)
        self.proton_version = proton_version
        self.main_window = main_window
        self.is_reinstall = is_reinstall
    
    def run(self):
        if self.is_reinstall:
            papi.remove_proton(self.proton_version)
            self.main_window.ui.statusBar.showMessage('Reinstalling Proton-' + self.proton_version + '...')
        else:
            self.main_window.ui.statusBar.showMessage('Installing Proton-' + self.proton_version + '...')
        papi.get_proton(self.proton_version)
        self.main_window.ui.statusBar.showMessage('Installed Proton-' + self.proton_version)
        self.main_window.updateInfo()


class PupguiInstallDialog(QDialog):
    def __init__(self, parent=None):
        super(PupguiInstallDialog, self).__init__(parent)
        self.main_window = parent
        self.setupUi()
    
    def setupUi(self):
        self.setFixedSize(250, 100)
        self.setWindowTitle('Install Proton')

        self.btnInfo = QPushButton('Info')
        self.btnInstall = QPushButton('Install')
        self.btnCancel = QPushButton('Cancel')

        button_box = QHBoxLayout()
        button_box.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        button_box.addWidget(self.btnInfo)
        button_box.addWidget(self.btnInstall)
        button_box.addWidget(self.btnCancel)

        self.comboProtonVersion = QComboBox()
        for item in self.main_window._available_releases:
            self.comboProtonVersion.addItem(item)

        vbox = QVBoxLayout()
        vbox.addWidget(QLabel('Select Proton-GE version to be installed'))
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
        install_thread = installProtonThread(self.comboProtonVersion.currentText(), self.main_window, is_reinstall=self.checkCurrentVersionInstallStatus())
        install_thread.start()
        self.close()

    def btnCancelClicked(self):
        self.close()

    def comboProtonVersionCurrentIndexChanged(self):
        self.checkCurrentVersionInstallStatus()
    
    def checkCurrentVersionInstallStatus(self):
        current_version = 'Proton-' + self.comboProtonVersion.currentText()
        if current_version in papi.installed_versions():
            self.btnInstall.setText('Reinstall')
            return True
        else:
            self.btnInstall.setText('Install')
            return False
