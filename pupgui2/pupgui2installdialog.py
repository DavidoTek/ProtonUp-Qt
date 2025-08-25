import os
import threading
import pkgutil

from PySide6.QtCore import Signal, QLocale, QDataStream, QByteArray
from PySide6.QtGui import QIcon, QPixmap, Qt
from PySide6.QtWidgets import QDialog
from PySide6.QtUiTools import QUiLoader

from pupgui2.util import open_webbrowser_thread, config_advanced_mode, get_combobox_index_by_value


RELEASES_PER_PAGE = 50  # Number of releases to fetch per page


class PupguiInstallDialog(QDialog):

    is_fetching_releases = Signal(bool)
    compat_tool_selected = Signal(dict)

    def __init__(self, install_location, ct_loader, parent=None):
        super(PupguiInstallDialog, self).__init__(parent)
        self.install_location = install_location
        advanced_mode = (config_advanced_mode() == 'enabled')
        self.ct_objs = ct_loader.get_ctobjs(self.install_location, advanced_mode=advanced_mode)
        self.current_ct_obj = None
        self.loaded_page = 1
        self.more_releases_loadable = True  # Set to False when no more versions are available

        self.load_ui()
        self.load_assets()
        self.setup_ui()
        self.ui.show()

    def load_ui(self):
        data = pkgutil.get_data(__name__, 'resources/ui/pupgui2_installdialog.ui')
        ui_file = QDataStream(QByteArray(data))
        self.ui = QUiLoader().load(ui_file.device())

    def load_assets(self):
        p = QPixmap()
        p.loadFromData(pkgutil.get_data(__name__, os.path.join('resources/img/arrow_down.png')))
        self.arrow_down_icon = QIcon(p)

    def setup_ui(self):
        self.ui.btnInfo.clicked.connect(self.btn_info_clicked)
        self.ui.btnInstall.clicked.connect(self.btn_install_clicked)
        self.ui.btnCancel.clicked.connect(lambda: self.ui.close())
        self.ui.comboCompatTool.currentIndexChanged.connect(self.combo_compat_tool_current_index_changed)
        self.ui.comboCompatTool.view().setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.ui.comboCompatToolVersion.currentIndexChanged.connect(self.combo_compat_tool_version_current_index_changed)
        self.ui.comboCompatToolVersion.view().setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.is_fetching_releases.connect(lambda x: self.ui.comboCompatTool.setEnabled(not x))
        self.is_fetching_releases.connect(lambda x: self.ui.comboCompatToolVersion.setEnabled(not x))
        self.is_fetching_releases.connect(lambda x: self.ui.btnInfo.setEnabled(not x))
        self.is_fetching_releases.connect(lambda x: self.ui.btnInstall.setEnabled(not x))

        combobox_style = 'QComboBox { combobox-popup: 0; } QComboBox QAbstractItemView::item { padding: 3px; }'
        self.ui.comboCompatTool.setStyleSheet(combobox_style)
        self.ui.comboCompatToolVersion.setStyleSheet(combobox_style)

        self.ui.comboCompatTool.addItems([ctobj['name'] for ctobj in self.ct_objs])

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

    def update_releases(self):
        """
        Update the versions combobox with the releases of the selected compatibility tool.
        It will add additional releases to the combobox when self.loaded_page is >1.
        """
        if not self.current_ct_obj:
            print("Error, InstallDialog: Could not find compatibility tool object.")
            return

        def _threadupdate_releases_thread():
            self.is_fetching_releases.emit(True)

            if self.loaded_page == 1:
                self.ui.comboCompatToolVersion.clear()
            else:
                self.ui.comboCompatToolVersion.removeItem(self.ui.comboCompatToolVersion.count() - 1)

            vers = self.current_ct_obj['installer'].fetch_releases(count=RELEASES_PER_PAGE, page=self.loaded_page)

            # If the number of fetched releases is less than RELEASES_PER_PAGE, there are no more releases to fetch
            if len(vers) < RELEASES_PER_PAGE:
                self.more_releases_loadable = False

            # Stops install dialog UI elements from being enabled when rate-limited to prevent switching/installing tools
            if len(vers) > 0:
                self.ui.comboCompatToolVersion.addItems(vers)
                # Only set current index to 0 on initial load, not when loading more
                if self.loaded_page == 1:
                    self.ui.comboCompatToolVersion.setCurrentIndex(0)

                if self.more_releases_loadable:
                    self.ui.comboCompatToolVersion.addItem(self.tr('Load more...'))
                    self.ui.comboCompatToolVersion.setItemIcon(self.ui.comboCompatToolVersion.count() - 1, self.arrow_down_icon)

            self.is_fetching_releases.emit(False)

        t = threading.Thread(target=_threadupdate_releases_thread)
        t.start()

    def combo_compat_tool_current_index_changed(self):
        """ fetch and show available releases for selected compatibility tool """
        for ctobj in self.ct_objs:
            if ctobj['name'] == self.ui.comboCompatTool.currentText():
                self.current_ct_obj = ctobj
                self.loaded_page = 1
                self.more_releases_loadable = True
                self.update_releases()
                self.update_description(ctobj)
                return

    def combo_compat_tool_version_current_index_changed(self):
        """ load more releases when the "Load more..." item is selected """
        # The last item in the combobox is the "Load more..." item if self.more_releases_loadable is True
        if not self.more_releases_loadable:
            return

        if self.ui.comboCompatToolVersion.currentIndex() == self.ui.comboCompatToolVersion.count() - 1:
            self.loaded_page += 1
            self.update_releases()

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
