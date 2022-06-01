import sys, os, shutil
import threading
import pkgutil
from typing import final

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtUiTools import QUiLoader

from .util import apply_dark_theme, create_compatibilitytools_folder, get_installed_ctools
from .util import install_directory, available_install_directories, get_install_location_from_directory_name
from .util import remove_ctool
from .steamutil import get_steam_game_list
from .util import print_system_information
from .util import single_instance
from .util import download_awacy_gamelist
from .constants import APP_NAME, APP_VERSION, BUILD_INFO, TEMP_DIR
from . import ctloader
from .pupgui2installdialog import PupguiInstallDialog
from .pupgui2aboutdialog import PupguiAboutDialog
from .pupgui2ctinfodialog import PupguiCtInfoDialog
from .gamepadinputworker import GamepadInputWorker
from .pupgui2customiddialog import PupguiCustomInstallDirectoryDialog
from .pupgui2gamelistdialog import PupguiGameListDialog
from .resources import ui


class InstallWineThread(threading.Thread):

    def __init__(self, main_window):
        threading.Thread.__init__(self)
        self.main_window = main_window

    def run(self):
        while True:
            if len(self.main_window.pending_downloads) == 0:
                break
            compat_tool = self.main_window.pending_downloads[0]
            try:
                self.install_compat_tool(compat_tool)
            except Exception as e:
                print(e)
            if compat_tool in self.main_window.pending_downloads:
                self.main_window.pending_downloads.remove(compat_tool)
            self.main_window.ui.txtActiveDownloads.setText(str(len(self.main_window.pending_downloads)))

    def install_compat_tool(self, compat_tool):
        tool_name = compat_tool['name']
        tool_ver = compat_tool['version']
        install_dir = compat_tool['install_dir']

        for ctobj in self.main_window.ct_loader.get_ctobjs():
            if ctobj['name'] == tool_name:
                if not ctobj['installer'].is_system_compatible():
                    self.main_window.set_download_progress_percent(-1)
                    break
                ctobj['installer'].download_progress_percent.connect(self.main_window.set_download_progress_percent)
                ctobj['installer'].get_tool(tool_ver, os.path.expanduser(install_dir), TEMP_DIR)
                break


class MainWindow(QObject):

    def __init__(self):
        super(MainWindow, self).__init__()

        self.ct_loader = ctloader.CtLoader()

        self.combo_install_location_index_map = []
        self.updating_combo_install_location = False
        self.pending_downloads = []
        self.current_compat_tool_name = ""
        self.compat_tool_index_map = []

        self.load_ui()
        self.setup_ui()
        self.update_ui()

        self.ui.show()

    def load_ui(self):
        """ load the main window ui file """
        data = pkgutil.get_data(__name__, 'resources/ui/pupgui2_mainwindow.ui')
        ui_file = QDataStream(QByteArray(data))
        loader = QUiLoader()
        self.ui = loader.load(ui_file.device())

    def setup_ui(self):
        """ setup ui - connect signals etc """
        self.progressBarDownload = QProgressBar()
        self.progressBarDownload.setVisible(False)
        self.ui.statusBar().addPermanentWidget(self.progressBarDownload)
        self.ui.setWindowIcon(QIcon.fromTheme('net.davidotek.pupgui2'))

        self.update_combo_install_location()

        self.ui.comboInstallLocation.currentIndexChanged.connect(self.combo_install_location_current_index_changed)
        self.ui.btnManageInstallLocations.clicked.connect(self.btn_manage_install_locations_clicked)
        self.ui.btnAddVersion.clicked.connect(self.btn_add_version_clicked)
        self.ui.btnRemoveSelected.clicked.connect(self.btn_remove_selcted_clicked)
        self.ui.btnShowGameList.clicked.connect(self.btn_show_game_list_clicked)
        self.ui.btnAbout.clicked.connect(self.btn_about_clicked)
        self.ui.btnClose.clicked.connect(self.btn_close_clicked)
        self.ui.listInstalledVersions.itemDoubleClicked.connect(self.list_installed_versions_item_double_clicked)
        self.ui.listInstalledVersions.itemSelectionChanged.connect(self.list_installed_versions_item_selection_changed)
        self.ui.btnShowCtInfo.clicked.connect(self.btn_show_ct_info_clicked)

        self.ui.btnRemoveSelected.setEnabled(False)
        self.ui.btnShowCtInfo.setEnabled(False)

        self.ui.statusBar().showMessage(APP_NAME + ' ' + APP_VERSION)

        self.giw = GamepadInputWorker()
        if os.getenv('PUPGUI2_DISABLE_GAMEPAD', '0') == '0':
            self.giw.start()
            self.giw.press_virtual_key.connect(self.press_virtual_key)
        QApplication.instance().aboutToQuit.connect(self.giw.stop)

    def update_combo_install_location(self):
        self.updating_combo_install_location = True

        self.ui.comboInstallLocation.clear()
        self.combo_install_location_index_map = []

        i = 0
        current_install_dir = install_directory()
        for install_dir in available_install_directories():
            icon_name = get_install_location_from_directory_name(install_dir).get('icon')
            display_name = get_install_location_from_directory_name(install_dir).get('display_name')
            if display_name and not display_name == '':
                self.ui.comboInstallLocation.addItem(QIcon.fromTheme(icon_name), display_name + ' (' + install_dir + ')')
            else:
                self.ui.comboInstallLocation.addItem(install_dir)
            self.combo_install_location_index_map.append(install_dir)
            if current_install_dir == install_dir:
                self.ui.comboInstallLocation.setCurrentIndex(i)
            i += 1

        self.updating_combo_install_location = False

    def update_ui(self):
        """ update ui contents """
        install_loc = get_install_location_from_directory_name(install_directory())

        self.ui.listInstalledVersions.clear()
        self.compat_tool_index_map = get_installed_ctools(install_directory())

        # Launcher specific (Lutris): Show DXVK
        if install_loc.get('launcher') == 'lutris':
            dxvk_dir = os.path.join(install_directory(), '../../runtime/dxvk')
            for ct in get_installed_ctools(dxvk_dir):
                if not 'dxvk' in ct.get_displayname().lower():
                    ct.displayname = 'DXVK ' + ct.displayname
                self.compat_tool_index_map.append(ct)

        # Launcher specific (Steam): Number of games using the compatibility tool
        if install_loc.get('launcher') == 'steam' and 'vdf_dir' in install_loc:
            get_steam_game_list(install_loc.get('vdf_dir'), cached=False)  # update app list cache
            for ct in self.compat_tool_index_map:
                games = get_steam_game_list(install_loc.get('vdf_dir'), ct.get_install_folder(), cached=True)
                ct.no_games = len(games)

        for ct in self.compat_tool_index_map:
            self.ui.listInstalledVersions.addItem(ct.get_displayname(unused_tr=self.tr('unused')))

        self.ui.txtActiveDownloads.setText(str(len(self.pending_downloads)))
        if len(self.pending_downloads) == 0:
            self.ui.statusBar().showMessage(APP_NAME + ' ' + APP_VERSION)
            self.progressBarDownload.setVisible(False)
            self.ui.comboInstallLocation.setEnabled(True)

        self.show_launcher_specific_information()

        if install_loc.get('launcher') == 'steam' and 'vdf_dir' in install_loc:
            self.ui.btnShowGameList.setVisible(True)
        #elif install_loc.get('launcher') == 'lutris':
        #    self.ui.btnShowGameList.setVisible(True)
        else:
            self.ui.btnShowGameList.setVisible(False)

    def install_compat_tool(self, compat_tool):
        """ install compatibility tool (called by install dialog signal) """
        if compat_tool in self.pending_downloads:
            return

        self.pending_downloads.append(compat_tool)
        self.update_ui()
        if len(self.pending_downloads) == 1:
            install_thread = InstallWineThread(self)
            install_thread.start()

    def set_fetching_releases(self, value):
        if value:
            self.ui.statusBar().showMessage(self.tr('Fetching releases...'))
        else:
            self.ui.statusBar().showMessage(APP_NAME + ' ' + APP_VERSION)

    def set_download_progress_percent(self, value):
        """ set download progress bar value and update status bar text """
        self.progressBarDownload.setValue(value)
        if len(self.pending_downloads):
            compat_tool = self.pending_downloads[0]
            self.current_compat_tool_name = compat_tool['name'] + ' ' + compat_tool['version']
        if value == -2:
            self.ui.statusBar().showMessage(self.tr('Download canceled.'))
            return
        if value == -1:
            self.ui.statusBar().showMessage(self.tr('Could not install {current_compat_tool_name}...').format(current_compat_tool_name=self.current_compat_tool_name))
            return
        if value == 1:
            self.progressBarDownload.setVisible(True)
            self.ui.comboInstallLocation.setEnabled(False)
            self.ui.txtActiveDownloads.setText(str(len(self.pending_downloads)))
            self.ui.statusBar().showMessage(self.tr('Downloading {current_compat_tool_name}...').format(current_compat_tool_name=self.current_compat_tool_name))
        elif value == 99:
            self.ui.statusBar().showMessage(self.tr('Extracting {current_compat_tool_name}...').format(current_compat_tool_name=self.current_compat_tool_name))
        elif value == 100:
            self.ui.statusBar().showMessage(self.tr('Installed {current_compat_tool_name}.').format(current_compat_tool_name=self.current_compat_tool_name))
            self.update_ui()

    def btn_add_version_clicked(self):
        dialog = PupguiInstallDialog(get_install_location_from_directory_name(install_directory()), self.ct_loader, parent=self.ui)
        dialog.compat_tool_selected.connect(self.install_compat_tool)
        dialog.is_fetching_releases.connect(self.set_fetching_releases)
        dialog.setup_ui()
        dialog.show()
        dialog.setFixedSize(dialog.size())

    def btn_remove_selcted_clicked(self):
        ctools_to_remove = []
        games_using_tools = 0
        for item in self.ui.listInstalledVersions.selectedItems():
            ct = self.compat_tool_index_map[self.ui.listInstalledVersions.row(item)]
            if ct.no_games > 0:
                games_using_tools += 1
            ctools_to_remove.append(ct)

        if games_using_tools > 0:
            ret = QMessageBox.question(self.ui, self.tr('Remove compatibility tools?'), self.tr('You are trying to remove compatibility tools\nwhich are in use by {n} games. Continue?').format(n=games_using_tools))
            if ret == QMessageBox.StandardButton.No:
                return

        for ct in ctools_to_remove:
            remove_ctool(ct.get_install_folder(), ct.get_install_dir())

        self.ui.statusBar().showMessage(self.tr('Removed selected versions.'))
        self.update_ui()

    def btn_show_game_list_clicked(self):
        gl_dialog = PupguiGameListDialog(install_directory(), self.ui)
        gl_dialog.game_property_changed.connect(self.update_ui)

    def btn_about_clicked(self):
        PupguiAboutDialog(self.ui)

    def btn_close_clicked(self):
        if len(self.pending_downloads) == 0:
            self.ui.close()
        else:
            r = QMessageBox.question(self.ui, self.tr('Exit?'), self.tr('There are pending downloads.\nCancel and exit anyway?'))
            if r == QMessageBox.StandardButton.Yes:
                self.cancel_download(cancel_all=True)
                self.ui.close()

    def combo_install_location_current_index_changed(self):
        if not self.updating_combo_install_location:
            install_dir = install_directory(self.combo_install_location_index_map[self.ui.comboInstallLocation.currentIndex()])
            self.ui.statusBar().showMessage(self.tr('Changed install directory to {install_dir}.').format(install_dir=install_dir), timeout=3000)
            self.update_ui()

    def btn_manage_install_locations_clicked(self):
        customid_dialog = PupguiCustomInstallDirectoryDialog(parent=self.ui)
        customid_dialog.custom_id_set.connect(self.update_combo_install_location)

    def show_launcher_specific_information(self):
        install_loc = get_install_location_from_directory_name(install_directory())
        # For Steam Flatpak only: Show that Proton-GE and Boxtron are available directly from Flathub.
        if 'steam' in install_loc.get('launcher') and 'Flatpak' in install_loc.get('display_name'):
            self.ui.statusBar().showMessage(self.tr('Info: You can get Proton-GE / Boxtron directly from Flathub!'))
    
    def list_installed_versions_item_double_clicked(self, item):
        # Show info about compatibility tool when double clicked in list
        ct = self.compat_tool_index_map[self.ui.listInstalledVersions.row(item)]
        install_loc = get_install_location_from_directory_name(install_directory())
        cti_dialog = PupguiCtInfoDialog(self.ui, ctool=ct.displayname, install_loc=install_loc, install_dir=ct.get_install_dir())
        cti_dialog.batch_update_complete.connect(self.update_ui)

    def list_installed_versions_item_selection_changed(self):
        n_sel_items = len(self.ui.listInstalledVersions.selectedItems())
        if n_sel_items == 0:
            self.ui.btnRemoveSelected.setEnabled(False)
            self.ui.btnShowCtInfo.setEnabled(False)
        else:
            self.ui.btnRemoveSelected.setEnabled(True)
            self.ui.btnShowCtInfo.setEnabled(True)

    def btn_show_ct_info_clicked(self):
        install_loc = get_install_location_from_directory_name(install_directory())
        for item in self.ui.listInstalledVersions.selectedItems():
            ct = self.compat_tool_index_map[self.ui.listInstalledVersions.row(item)]
            cti_dialog = PupguiCtInfoDialog(self.ui, ctool=ct.displayname, install_loc=install_loc, install_dir=ct.get_install_dir())
            cti_dialog.batch_update_complete.connect(self.update_ui)

    def press_virtual_key(self, key, mod):
        """ Presses virtual key, used by GamepadInputWorker """
        e = QKeyEvent(QEvent.KeyPress, key, mod)
        QCoreApplication.postEvent(QApplication.focusWidget(), e)
        e = QKeyEvent(QEvent.KeyRelease, key, mod)
        QCoreApplication.postEvent(QApplication.focusWidget(), e)

    def cancel_download(self, cancel_all=False):
        """ Cancel a compatibility tool download """
        if len(self.pending_downloads) == 0:
            return
        if cancel_all:
            self.pending_downloads = []
        else:
            self.pending_downloads = self.pending_downloads[1:]
        for ctobj in self.ct_loader.get_ctobjs():
            ctobj['installer'].download_canceled = True
        self.update_ui()


def main():
    """ ProtonUp-Qt main function. Called from __main__.py """
    print(f'{APP_NAME} {APP_VERSION} by DavidoTek. Build Info: {BUILD_INFO}.')
    print_system_information()
    if not single_instance():
        print("Second instance of ProtonUp-Qt found!")
        return

    create_compatibilitytools_folder()
    download_awacy_gamelist()

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setWindowIcon(QIcon.fromTheme('net.davidotek.pupgui2'))

    lang = QLocale.languageToCode(QLocale().language())

    ldata = None
    try:
        ldata = pkgutil.get_data(__name__, 'resources/i18n/pupgui2_' + lang + '.qm')
    except:
        pass
    finally:
        translator = QTranslator()
        if translator.load(ldata):
            app.installTranslator(translator)

    qtTranslator = QTranslator()
    if qtTranslator.load(QLocale(), 'qt', '_', QLibraryInfo.location(QLibraryInfo.TranslationsPath)):
        app.installTranslator(qtTranslator)

    apply_dark_theme(app)

    window = MainWindow()

    ret = app.exec()

    shutil.rmtree(TEMP_DIR, ignore_errors=True)

    sys.exit(ret)
