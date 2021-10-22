import webbrowser

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *


class PupguiInstallDialog(QDialog):
    compat_tool_selected = Signal(dict)

    def __init__(self, install_location, ct_loader, parent=None):
        super(PupguiInstallDialog, self).__init__(parent)
        self.install_location = install_location
        self.ct_objs = ct_loader.get_ctobjs(self.install_location['launcher'])
        self.setupUi()
    
    def setupUi(self):
        self.setWindowTitle('Install Compatibility Tool')
        self.setWindowIcon(QIcon.fromTheme('pupgui2'))

        self.btnInfo = QPushButton('Info')
        self.btnInstall = QPushButton('Install')
        self.btnCancel = QPushButton('Cancel')
        button_box = QHBoxLayout()
        button_box.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        button_box.addWidget(self.btnInfo)
        button_box.addWidget(self.btnInstall)
        button_box.addWidget(self.btnCancel)
        self.comboCompatTool = QComboBox()
        self.comboCompatToolVersion = QComboBox()
        vbox = QVBoxLayout()
        vbox.addWidget(QLabel('Compatibility tool:'))
        vbox.addWidget(self.comboCompatTool)
        vbox.addWidget(QLabel('Version:'))
        vbox.addWidget(self.comboCompatToolVersion)
        vbox.addLayout(button_box)
        self.setLayout(vbox)
        self.btnInfo.clicked.connect(self.btn_info_clicked)
        self.btnInstall.clicked.connect(self.btn_install_clicked)
        self.btnCancel.clicked.connect(self.btn_cancel_clicked)
        self.comboCompatTool.currentIndexChanged.connect(self.combo_compat_tool_current_index_changed)

        for ctobj in self.ct_objs:
            self.comboCompatTool.addItem(ctobj['name'])
    
    def btn_info_clicked(self):
        for ctobj in self.ct_objs:
            if ctobj['name'] == self.comboCompatTool.currentText():
                webbrowser.open(ctobj['installer'].get_info_url(self.comboCompatToolVersion.currentText()))

    def btn_install_clicked(self):
        current_version = self.comboCompatTool.currentText()
        self.compat_tool_selected.emit({
            'name': self.comboCompatTool.currentText(),
            'version': self.comboCompatToolVersion.currentText(),
            'install_dir': self.install_location['install_dir']
        })
        self.close()

    def btn_cancel_clicked(self):
        self.close()
    
    def combo_compat_tool_current_index_changed(self):
        self.comboCompatToolVersion.clear()
        for ctobj in self.ct_objs:
            if ctobj['name'] == self.comboCompatTool.currentText():
                for ver in ctobj['installer'].fetch_releases():
                    self.comboCompatToolVersion.addItem(ver)
                return
