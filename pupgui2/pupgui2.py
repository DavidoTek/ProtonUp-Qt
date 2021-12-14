import sys, os, shutil
import threading
from PySide6 import QtWidgets
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtUiTools import QUiLoader

from util import apply_dark_theme, create_compatibilitytools_folder
from util import install_directory, available_install_directories, get_install_location_from_directory_name
from util import list_installed_ctools, remove_ctool
from util import get_steam_games_using_compat_tool, sort_compatibility_tool_names
from util import download_steam_app_list_thread
from constants import APP_NAME, APP_VERSION, TEMP_DIR
import ctloader
from pupgui2installdialog import PupguiInstallDialog
from pupgui2aboutdialog import PupguiAboutDialog
from pupgui2ctinfodialog import PupguiCtInfoDialog
from gamepadinputworker import GamepadInputWorker


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

    def __init__(self, pupgui2_base_dir):
        super(MainWindow, self).__init__()

        self.ct_loader = ctloader.CtLoader()
        self.ct_loader.load_ctmods(ctmod_dir=os.path.join(pupgui2_base_dir, 'ctmods'))

        self.pupgui2_base_dir = pupgui2_base_dir

        self.combo_install_location_index_map = []
        self.pending_downloads = []
        
        self.load_ui()
        self.setup_ui()
        self.update_ui()

        self.ui.show()

    def load_ui(self):
        """ load the main window ui file """
        ui_file_name = os.path.join(self.pupgui2_base_dir, 'ui/pupgui2_mainwindow.ui')
        ui_file = QFile(ui_file_name)
        if not ui_file.open(QIODevice.ReadOnly):
            print(f'Cannot open {ui_file_name}: {ui_file.errorString()}')
            sys.exit(-1)
        loader = QUiLoader()
        self.ui = loader.load(ui_file)
        ui_file.close()

    def setup_ui(self):
        """ setup ui - connect signals etc """
        self.progressBarDownload = QProgressBar()
        self.progressBarDownload.setVisible(False)
        self.ui.statusBar().addPermanentWidget(self.progressBarDownload)
        self.ui.setWindowIcon(QIcon.fromTheme('net.davidotek.pupgui2'))

        i = 0
        current_install_dir = install_directory()
        for install_dir in available_install_directories():
            icon_name = get_install_location_from_directory_name(install_dir)['icon']
            display_name = get_install_location_from_directory_name(install_dir)['display_name']
            self.ui.comboInstallLocation.addItem(QIcon.fromTheme(icon_name), display_name + ' (' + install_dir + ')')
            self.combo_install_location_index_map.append(install_dir)
            if current_install_dir == install_dir:
                self.ui.comboInstallLocation.setCurrentIndex(i)
            i += 1

        self.ui.comboInstallLocation.currentIndexChanged.connect(self.combo_install_location_current_index_changed)
        self.ui.btnAddVersion.clicked.connect(self.btn_add_version_clicked)
        self.ui.btnRemoveSelected.clicked.connect(self.btn_remove_selcted_clicked)
        self.ui.btnAbout.clicked.connect(self.btn_about_clicked)
        self.ui.btnClose.clicked.connect(self.btn_close_clicked)
        self.ui.listInstalledVersions.itemDoubleClicked.connect(self.list_installed_versions_item_double_clicked)

        self.ui.statusBar().showMessage(APP_NAME + ' ' + APP_VERSION)

        self.giw = GamepadInputWorker()
        if os.getenv('PUPGUI2_DISABLE_GAMEPAD', '0') == '0':
            self.giw.start()
            self.giw.press_virtual_key.connect(self.press_virtual_key)

    def update_ui(self):
        """ update ui contents """
        self.ui.listInstalledVersions.clear()

        ctools = sort_compatibility_tool_names(list_installed_ctools(install_directory()))

        for ver in ctools:
            # Launcher specific
            install_loc = get_install_location_from_directory_name(install_directory())
            if install_loc.get('launcher') == 'steam' and 'vdf_dir' in install_loc:
                games = get_steam_games_using_compat_tool(ver.split(' - ')[0], install_loc.get('vdf_dir'))
                if len(games) == 0:
                    ver += ' - ' + self.tr('unused')
            
            self.ui.listInstalledVersions.addItem(ver)
        
        self.ui.txtActiveDownloads.setText(str(len(self.pending_downloads)))
        if len(self.pending_downloads) == 0:
            self.ui.statusBar().showMessage(APP_NAME + ' ' + APP_VERSION)
            self.progressBarDownload.setVisible(False)
            self.ui.comboInstallLocation.setEnabled(True)

        self.show_launcher_specific_information()

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
        install_loc = get_install_location_from_directory_name(install_directory())

        vers_to_remove = []
        games_using_tools = 0
        for item in self.ui.listInstalledVersions.selectedItems():
            ver = item.text()
            if install_loc.get('launcher') == 'steam' and 'vdf_dir' in install_loc:
                games_using_tools += len(get_steam_games_using_compat_tool(ver.split(' - ')[0], install_loc.get('vdf_dir')))
            vers_to_remove.append(ver)

        if games_using_tools > 0:
            ret = QMessageBox.question(self.ui, self.tr('Remove compatibility tools?'), self.tr('You are trying to remove compatibility tools\nwhich are in use by {n} games. Continue?').format(n=games_using_tools))
            if ret == QMessageBox.StandardButton.No:
                return

        for ver in vers_to_remove:
            remove_ctool(ver, install_directory())
        
        self.ui.statusBar().showMessage(self.tr('Removed selected versions.'))
        self.update_ui()

    def btn_about_clicked(self):
        PupguiAboutDialog(self.pupgui2_base_dir, self.ui)

    def btn_close_clicked(self):
        self.ui.close()

    def combo_install_location_current_index_changed(self):
        install_dir = install_directory(self.combo_install_location_index_map[self.ui.comboInstallLocation.currentIndex()])
        self.ui.statusBar().showMessage(self.tr('Changed install directory to {install_dir}.').format(install_dir=install_dir), timeout=3000)
        self.update_ui()

    def show_launcher_specific_information(self):
        install_loc = get_install_location_from_directory_name(install_directory())
        # For Steam Flatpak only: Show that Proton-GE and Boxtron are available directly from Flathub.
        if 'steam' in install_loc.get('launcher') and 'Flatpak' in install_loc.get('display_name'):
            self.ui.statusBar().showMessage(self.tr('Info: You can get Proton-GE / Boxtron directly from Flathub!'))
    
    def list_installed_versions_item_double_clicked(self, item):
        # Show info about compatibility tool when double clicked in list
        games = []
        ver = item.text().split(' - ')[0]
        install_loc = get_install_location_from_directory_name(install_directory())
        if install_loc.get('launcher') == 'steam' and 'vdf_dir' in install_loc:
            games = get_steam_games_using_compat_tool(ver, install_loc.get('vdf_dir'))
        PupguiCtInfoDialog(self.pupgui2_base_dir, self.ui, games=games, ctool=ver, install_loc=install_loc, install_dir=install_directory())

    def press_virtual_key(self, key, mod):
        e = QKeyEvent(QEvent.KeyPress, key, mod)
        QCoreApplication.postEvent(QApplication.focusWidget(), e)
        e = QKeyEvent(QEvent.KeyRelease, key, mod)
        QCoreApplication.postEvent(QApplication.focusWidget(), e)


if __name__ == '__main__':
    create_compatibilitytools_folder()

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setWindowIcon(QIcon.fromTheme('net.davidotek.pupgui2'))

    parser = QCommandLineParser()
    pupgui2_base_dir_option = QCommandLineOption(['pupgui2-base-dir'], 'directory containing pupgui2 files', 'pupgui2-base-dir', './share/pupgui2')
    parser.addOption(pupgui2_base_dir_option)
    parser.process(app)
    pupgui2_base_dir = os.path.abspath(parser.value(pupgui2_base_dir_option))

    translator = QTranslator()
    if translator.load(QLocale(), 'pupgui2', '_', os.path.join(pupgui2_base_dir, 'i18n')):
        app.installTranslator(translator)

    print(f'{APP_NAME} {APP_VERSION} by DavidoTek. Base directory: {pupgui2_base_dir}')

    download_steam_app_list_thread()

    apply_dark_theme(app)

    window = MainWindow(pupgui2_base_dir)

    ret = app.exec()

    shutil.rmtree(TEMP_DIR, ignore_errors=True)

    sys.exit(ret)
