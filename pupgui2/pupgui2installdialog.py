import threading
import pkgutil

from PySide6.QtCore import Signal, QLocale, QDataStream, QByteArray
from PySide6.QtWidgets import QDialog
from PySide6.QtUiTools import QUiLoader

from pupgui2.util import open_webbrowser_thread, config_advanced_mode, get_combobox_index_by_value


class PupguiInstallDialog(QDialog):

    is_fetching_releases = Signal(bool)
    compat_tool_selected = Signal(dict)

    def __init__(self, install_location, ct_loader, parent=None):
        super(PupguiInstallDialog, self).__init__(parent)
        self.install_location = install_location
        advanced_mode = (config_advanced_mode() == 'enabled')
        self.ct_objs = ct_loader.get_ctobjs(self.install_location, advanced_mode=advanced_mode)

        self.load_ui()
        self.setup_ui()
        self.ui.show()

    def load_ui(self):
        data = pkgutil.get_data(__name__, 'resources/ui/pupgui2_installdialog.ui')
        ui_file = QDataStream(QByteArray(data))
        self.ui = QUiLoader().load(ui_file.device())

    def setup_ui(self):
        self.ui.btnInfo.clicked.connect(self.btn_info_clicked)
        self.ui.btnInstall.clicked.connect(self.btn_install_clicked)
        self.ui.btnCancel.clicked.connect(lambda: self.ui.close())
        self.ui.comboCompatTool.currentIndexChanged.connect(self.combo_compat_tool_current_index_changed)
        self.is_fetching_releases.connect(lambda x: self.ui.comboCompatTool.setEnabled(not x))
        self.is_fetching_releases.connect(lambda x: self.ui.comboCompatToolVersion.setEnabled(not x))
        self.is_fetching_releases.connect(lambda x: self.ui.btnInfo.setEnabled(not x))
        self.is_fetching_releases.connect(lambda x: self.ui.btnInstall.setEnabled(not x))

        self.ui.comboCompatTool.addItems([ctobj['name'] for ctobj in self.ct_objs])
        self.ui.comboCompatToolVersion.setStyleSheet('QComboBox { combobox-popup: 0; }')

    def btn_info_clicked(self):
        for ctobj in self.ct_objs:
            if ctobj['name'] == self.ui.comboCompatTool.currentText():
                ver = self.ui.comboCompatToolVersion.currentText()
                open_webbrowser_thread(ctobj['installer'].get_info_url(ver) if ver else ctobj['installer'].get_info_url(ver).replace('tag', ''))
                return

    def btn_install_clicked(self):
        self.compat_tool_selected.emit({
            'name': self.ui.comboCompatTool.currentText(),
            'version': self.ui.comboCompatToolVersion.currentText(),
            'install_dir': self.install_location['install_dir']
        })
        self.ui.close()

    def combo_compat_tool_current_index_changed(self):
        """ fetch and show available releases for selected compatibility tool """
        for ctobj in self.ct_objs:
            if ctobj['name'] == self.ui.comboCompatTool.currentText():
                def update_releases():
                    self.is_fetching_releases.emit(True)
                    self.ui.comboCompatToolVersion.clear()
                    vers = ctobj['installer'].fetch_releases()
                    # Stops install dialog UI elements from being enabled when rate-limited to prevent switching/installing tools
                    if len(vers) > 0:
                        self.ui.comboCompatToolVersion.addItems(vers)
                        self.ui.comboCompatToolVersion.setCurrentIndex(0)
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
        
        self.ui.txtDescription.setHtml(desc)

    def set_selected_compat_tool(self, ctool_name: str):
        """ Set compat tool dropdown selected index to the index of the compat tool name passed """
        if ctool_name:
            index = get_combobox_index_by_value(self.ui.comboCompatTool, ctool_name)
            if index >= 1:
                self.ui.comboCompatTool.setCurrentIndex(index)
