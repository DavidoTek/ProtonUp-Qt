import threading, webbrowser

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

import protonup.api as papi


class installProtonThread(threading.Thread):
    def __init__(self, proton_version, main_window):
        threading.Thread.__init__(self)
        self.proton_version = proton_version
        self.main_window = main_window
    def run(self):
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
        self.resize(240, 100)
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
    
    def btnInfoClicked(self):
        webbrowser.open('https://github.com/GloriousEggroll/proton-ge-custom/releases/tag/' + self.comboProtonVersion.currentText())

    def btnInstallClicked(self):
        install_thread = installProtonThread(self.comboProtonVersion.currentText(), self.main_window)
        install_thread.start()
        self.close()

    def btnCancelClicked(self):
        self.close()