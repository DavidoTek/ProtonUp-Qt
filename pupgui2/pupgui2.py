import sys, os, subprocess, shutil
import threading
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtUiTools import QUiLoader

from util import apply_dark_theme, create_steam_compatibilitytools_folder
from util import install_directory, available_install_directories, get_install_location_from_directory_name
from util import list_installed_ctools, remove_ctool
from constants import APP_NAME, APP_VERSION, ABOUT_TEXT, TEMP_DIR
import ctloader
from pupgui2installdialog import PupguiInstallDialog


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
            self.main_window.update_ui()

    def install_compat_tool(self, compat_tool):
        tool_name = compat_tool['name']
        tool_ver = compat_tool['version']
        install_dir = compat_tool['install_dir']

        for ctobj in self.main_window.ct_loader.get_ctobjs():
            if ctobj['name'] == tool_name:
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

        i = 0
        current_install_dir = install_directory()
        for install_dir in available_install_directories():
            launcher_name = get_install_location_from_directory_name(install_dir)['launcher']
            display_name = get_install_location_from_directory_name(install_dir)['display_name']
            self.ui.comboInstallLocation.addItem(QIcon.fromTheme(launcher_name), display_name + ' (' + install_dir + ')')
            self.combo_install_location_index_map.append(install_dir)
            if current_install_dir == install_dir:
                self.ui.comboInstallLocation.setCurrentIndex(i)
            i += 1

        self.ui.comboInstallLocation.currentIndexChanged.connect(self.combo_install_location_current_index_changed)
        self.ui.btnAddVersion.clicked.connect(self.btn_add_version_clicked)
        self.ui.btnRemoveSelected.clicked.connect(self.btn_remove_selcted_clicked)
        self.ui.btnAbout.clicked.connect(self.btn_about_clicked)
        self.ui.btnClose.clicked.connect(self.btn_close_clicked)

        self.ui.statusBar().showMessage(APP_NAME + ' ' + APP_VERSION)

    def update_ui(self):
        """ update ui contents """
        self.ui.listInstalledVersions.clear()

        for ver in list_installed_ctools(install_directory()):
            self.ui.listInstalledVersions.addItem(ver)
        
        self.ui.txtActiveDownloads.setText(str(len(self.pending_downloads)))
        if len(self.pending_downloads) == 0:
            self.ui.statusBar().showMessage(APP_NAME + ' ' + APP_VERSION)
            self.progressBarDownload.setVisible(False)
            self.ui.comboInstallLocation.setEnabled(True)

    def install_compat_tool(self, compat_tool):
        """ install compatibility tool (called by install dialog signal) """
        if compat_tool in self.pending_downloads:
            return

        self.pending_downloads.append(compat_tool)
        if len(self.pending_downloads) == 1:
            install_thread = InstallWineThread(self)
            install_thread.start()

    def set_fetching_releases(self, value):
        if value:
            self.ui.statusBar().showMessage('Fetching releases...')
        else:
            self.ui.statusBar().showMessage(APP_NAME + ' ' + APP_VERSION)

    def set_download_progress_percent(self, value):
        """ set download progress bar value and update status bar text """
        self.progressBarDownload.setValue(value)
        if len(self.pending_downloads):
            compat_tool = self.pending_downloads[0]
            self.current_compat_tool_name = compat_tool['name'] + ' ' + compat_tool['version']
        if value == 1:
            self.progressBarDownload.setVisible(True)
            self.ui.comboInstallLocation.setEnabled(False)
            self.ui.txtActiveDownloads.setText(str(len(self.pending_downloads)))
            self.ui.statusBar().showMessage('Downloading ' + self.current_compat_tool_name + '...')
        elif value == 99:
            self.ui.statusBar().showMessage('Extracting ' + self.current_compat_tool_name + '...')
        elif value == 100:
            self.ui.statusBar().showMessage('Installed ' + self.current_compat_tool_name)

    def btn_add_version_clicked(self):
        dialog = PupguiInstallDialog(get_install_location_from_directory_name(install_directory()), self.ct_loader, parent=self.ui)
        dialog.compat_tool_selected.connect(self.install_compat_tool)
        dialog.is_fetching_releases.connect(self.set_fetching_releases)
        dialog.setup_ui()
        dialog.show()

    def btn_remove_selcted_clicked(self):
        launcher_name = get_install_location_from_directory_name(install_directory())['launcher']
        for item in self.ui.listInstalledVersions.selectedItems():
            ver = item.text()
            remove_ctool(ver, install_directory())
        self.ui.statusBar().showMessage('Removed selected versions')
        self.update_ui()

    def btn_about_clicked(self):
        QMessageBox.about(self.ui, 'About ' + APP_NAME + ' ' + APP_VERSION, ABOUT_TEXT)
        QMessageBox.aboutQt(self.ui)

    def btn_close_clicked(self):
        self.ui.close()

    def combo_install_location_current_index_changed(self):
        install_dir = install_directory(self.combo_install_location_index_map[self.ui.comboInstallLocation.currentIndex()])
        self.ui.statusBar().showMessage('Changed install directory to ' + install_dir, timeout=3000)
        self.update_ui()


if __name__ == '__main__':
    create_steam_compatibilitytools_folder()

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setWindowIcon(QIcon.fromTheme('pupgui2'))

    parser = QCommandLineParser()
    pupgui2_base_dir_option = QCommandLineOption(['pupgui2-base-dir'], 'directory containing pupgui2 files', 'pupgui2-base-dir', './share/pupgui2')
    parser.addOption(pupgui2_base_dir_option)
    parser.process(app)
    pupgui2_base_dir = os.path.abspath(parser.value(pupgui2_base_dir_option))

    print(f'{APP_NAME} {APP_VERSION} by DavidoTek. Base directory: {pupgui2_base_dir}')

    apply_dark_theme(app)

    window = MainWindow(pupgui2_base_dir)

    ret = app.exec()

    shutil.rmtree(TEMP_DIR, ignore_errors=True)

    sys.exit(ret)
