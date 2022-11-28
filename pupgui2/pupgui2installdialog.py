import threading

from PySide6.QtCore import Signal, QLocale
from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QTextEdit, QComboBox
from PySide6.QtWidgets import QSizePolicy, QHBoxLayout, QVBoxLayout, QSpacerItem

from pupgui2.util import open_webbrowser_thread, config_advanced_mode


class PupguiInstallDialog(QDialog):

    is_fetching_releases = Signal(bool)
    compat_tool_selected = Signal(dict)

    def __init__(self, install_location, ct_loader, parent=None):
        super(PupguiInstallDialog, self).__init__(parent)
        self.install_location = install_location
        advanced_mode = (config_advanced_mode() == 'enabled')
        self.ct_objs = ct_loader.get_ctobjs(self.install_location, advanced_mode=advanced_mode)

    def setup_ui(self):
        self.setWindowTitle(self.tr('Install Compatibility Tool'))
        self.setModal(True)

        self.btnInfo = QPushButton(self.tr('Info'))
        self.btnInstall = QPushButton(self.tr('Install'))
        self.btnCancel = QPushButton(self.tr('Cancel'))
        button_box = QHBoxLayout()
        button_box.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        button_box.addWidget(self.btnInfo)
        button_box.addWidget(self.btnInstall)
        button_box.addWidget(self.btnCancel)
        self.comboCompatTool = QComboBox()
        self.comboCompatToolVersion = QComboBox()
        self.txtDescription = QTextEdit()
        self.txtDescription.setReadOnly(True)
        self.txtDescription.setMaximumHeight(95)
        vbox = QVBoxLayout()
        vbox.addWidget(QLabel(self.tr('Compatibility tool:')))
        vbox.addWidget(self.comboCompatTool)
        vbox.addWidget(QLabel(self.tr('Version:')))
        vbox.addWidget(self.comboCompatToolVersion)
        vbox.addWidget(QLabel(self.tr('Description:')))
        vbox.addWidget(self.txtDescription)
        vbox.addLayout(button_box)
        self.setLayout(vbox)
        self.btnInfo.clicked.connect(self.btn_info_clicked)
        self.btnInstall.clicked.connect(self.btn_install_clicked)
        self.btnCancel.clicked.connect(self.btn_cancel_clicked)
        self.comboCompatTool.currentIndexChanged.connect(self.combo_compat_tool_current_index_changed)
        self.is_fetching_releases.connect(lambda x: self.comboCompatTool.setEnabled(not x))
        self.is_fetching_releases.connect(lambda x: self.btnInfo.setEnabled(not x))
        self.is_fetching_releases.connect(lambda x: self.btnInstall.setEnabled(not x))

        for ctobj in self.ct_objs:
            self.comboCompatTool.addItem(ctobj['name'])
        self.comboCompatToolVersion.setStyleSheet('QComboBox { combobox-popup: 0; }')

    def btn_info_clicked(self):
        for ctobj in self.ct_objs:
            if ctobj['name'] == self.comboCompatTool.currentText():
                ver = self.comboCompatToolVersion.currentText()
                if ver == '':
                    open_webbrowser_thread(ctobj['installer'].get_info_url(ver).replace('tag', ''))
                else:
                    open_webbrowser_thread(ctobj['installer'].get_info_url(ver))

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
        """ fetch and show available releases for selected compatibility tool """
        for ctobj in self.ct_objs:
            if ctobj['name'] == self.comboCompatTool.currentText():
                def update_releases():
                    self.is_fetching_releases.emit(True)
                    vers = ctobj['installer'].fetch_releases()
                    self.comboCompatToolVersion.clear()
                    for ver in vers:
                        self.comboCompatToolVersion.addItem(ver)
                    self.comboCompatToolVersion.setCurrentIndex(0)
                    self.is_fetching_releases.emit(False)
                t = threading.Thread(target=update_releases)
                t.start()
                self.update_description(ctobj)
                return

    def update_description(self, ctobj):
        """ get (translated) description and update description text """
        app_lang = QLocale.languageToCode(QLocale().language())
        app_lname = QLocale().name()

        if app_lname in ctobj['description']:  # Examples: zh_TW, de_DE
            desc = ctobj['description'][app_lname]
        elif app_lang in ctobj['description']:  # Examples: de, nl
            desc = ctobj['description'][app_lang]
        else:
            desc = ctobj['description']['en']
        
        self.txtDescription.setHtml(desc)
