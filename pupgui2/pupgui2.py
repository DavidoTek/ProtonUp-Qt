import os
import sys
import shutil
import pkgutil
import requests
import subprocess
import threading

from PySide6.QtCore import Qt, QCoreApplication, QObject, QThread, QWaitCondition, QMutex, QDataStream
from PySide6.QtCore import QByteArray, QEvent, Signal, Slot, QTranslator, QLocale, QLibraryInfo
from PySide6.QtGui import QIcon, QKeyEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox, QLabel, QPushButton, QCheckBox, QProgressBar, QVBoxLayout
from PySide6.QtUiTools import QUiLoader

from pupgui2.resources import ui
from pupgui2.constants import APP_NAME, APP_VERSION, BUILD_INFO, TEMP_DIR, STEAM_STL_INSTALL_PATH
from pupgui2.constants import STEAM_PROTONGE_FLATPAK_APPSTREAM, STEAM_BOXTRON_FLATPAK_APPSTREAM, STEAM_STL_FLATPAK_APPSTREAM
from pupgui2 import ctloader
from pupgui2.datastructures import CTType, MsgBoxType, MsgBoxResult
from pupgui2.gamepadinputworker import GamepadInputWorker
from pupgui2.pupgui2aboutdialog import PupguiAboutDialog
from pupgui2.pupgui2ctinfodialog import PupguiCtInfoDialog
from pupgui2.pupgui2customiddialog import PupguiCustomInstallDirectoryDialog
from pupgui2.pupgui2gamelistdialog import PupguiGameListDialog
from pupgui2.pupgui2installdialog import PupguiInstallDialog
from pupgui2.steamutil import get_steam_acruntime_list, get_steam_app_list, get_steam_ct_game_map
from pupgui2.heroicutil import is_heroic_launcher, get_heroic_game_list
from pupgui2.util import apply_dark_theme, create_compatibilitytools_folder, get_installed_ctools, remove_ctool
from pupgui2.util import install_directory, available_install_directories, get_install_location_from_directory_name
from pupgui2.util import print_system_information, single_instance, download_awacy_gamelist, is_online, config_advanced_mode, compat_tool_available


class InstallWineThread(QThread):

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.buffer_not_empty = QWaitCondition()
        self.buffer_mutex = QMutex()

    def run(self):
        while True:
            self.buffer_mutex.lock()
            self.buffer_not_empty.wait(self.buffer_mutex)
            self.buffer_mutex.unlock()

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
                ctobj['installer'].get_tool(tool_ver, os.path.expanduser(install_dir), TEMP_DIR)
                break

    def stop(self):
        self.terminate()
        self.wait()


class MainWindow(QObject):

    update_statusbar_message = Signal(str)

    def __init__(self):
        super(MainWindow, self).__init__()

        self.rs = requests.Session()
        if token := os.getenv('PUPGUI_GHA_TOKEN'):
            self.rs.headers.update({'Authorization': f'token {token}'})
        self.ct_loader = ctloader.CtLoader(main_window=self)

        for ctobj in self.ct_loader.get_ctobjs():
            cti = ctobj.get('installer')
            if hasattr(cti, 'message_box_message'):
                cti.message_box_message.connect(self.show_msgbox)
            if hasattr(cti, 'question_box_message'):
                cti.question_box_message.connect(self.show_msgbox_question, Qt.BlockingQueuedConnection)
            cti.download_progress_percent.connect(self.set_download_progress_percent)

        self.combo_install_location_index_map = []
        self.updating_combo_install_location = False
        self.pending_downloads = []
        self.current_compat_tool_name = ""
        self.compat_tool_index_map = []
        self.msgcb_answer : MsgBoxResult = None
        self.msgcb_answer_lock = QMutex()

        self.load_ui()
        self.setup_ui()
        self.update_statusbar_message.connect(self.ui.statusBar().showMessage)
        QApplication.instance().message_box_message.connect(self.show_msgbox)
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
        self.ui.txtInstalledVersions.setText('0')

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
        self.ui.btnSteamFlatpakCtools.clicked.connect(self.btn_steam_flatpak_ctools_clicked)

        self.ui.btnRemoveSelected.setEnabled(False)
        self.ui.btnShowCtInfo.setEnabled(False)

        # Keyboard Shortcuts
        QShortcut(QKeySequence.Quit, self.ui).activated.connect(self.btn_close_clicked)
        QShortcut(QKeySequence('Ctrl+,'), self.ui).activated.connect(self.btn_about_clicked)
        QShortcut(QKeySequence(QKeySequence.HelpContents), self.ui).activated.connect(self.btn_about_clicked)
        QShortcut(QKeySequence('Ctrl+Shift+N'), self.ui).activated.connect(self.btn_manage_install_locations_clicked)
        QShortcut(QKeySequence.New, self.ui).activated.connect(self.btn_add_version_clicked)
        QShortcut(QKeySequence.Delete, self.ui).activated.connect(self.btn_remove_selcted_clicked)
        QShortcut(QKeySequence('Ctrl+Backspace'), self.ui).activated.connect(self.btn_remove_selcted_clicked)
        QShortcut(QKeySequence('Alt+Return'), self.ui).activated.connect(self.btn_show_ct_info_clicked)  # Uses 'Return' even though docs mention 'Enter' - https://doc.qt.io/qt-6/qkeysequence.html
        QShortcut(QKeySequence('Ctrl+G'), self.ui).activated.connect(self.btn_show_game_list_clicked)
        ## Steam Compat Tool Shortcuts (Some overlap w/ Heroic)
        QShortcut(QKeySequence('Ctrl+Shift+B'), self.ui).activated.connect(lambda: self.btn_add_version_clicked(compat_tool='Boxtron'))
        QShortcut(QKeySequence('Ctrl+Shift+L'), self.ui).activated.connect(lambda: self.btn_add_version_clicked(compat_tool='Luxtorpeda'))
        QShortcut(QKeySequence('Ctrl+Shift+T'), self.ui).activated.connect(lambda: self.btn_add_version_clicked(compat_tool='Proton Tkg'))
        QShortcut(QKeySequence('Ctrl+Shift+S'), self.ui).activated.connect(lambda: self.btn_add_version_clicked(compat_tool='SteamTinkerLaunch'))
        ## Lutris Compat Tool Shortcuts (Some overlap w/ Heroic)
        QShortcut(QKeySequence('Ctrl+Shift+D'), self.ui).activated.connect(lambda: self.btn_add_version_clicked(compat_tool='DXVK'))
        QShortcut(QKeySequence('Ctrl+Shift+L'), self.ui).activated.connect(lambda: self.btn_add_version_clicked(compat_tool='Lutris-Wine'))
        QShortcut(QKeySequence('Ctrl+Shift+W'), self.ui).activated.connect(lambda: self.btn_add_version_clicked(compat_tool='Wine Tkg (Valve Wine)'))

        self.set_default_statusbar()

        self.giw = GamepadInputWorker()
        if os.getenv('PUPGUI2_DISABLE_GAMEPAD', '0') == '0':
            self.giw.start()
            self.giw.press_virtual_key.connect(self.press_virtual_key)
        QApplication.instance().aboutToQuit.connect(self.giw.stop)

        self.install_thread = InstallWineThread(self)
        self.install_thread.start()
        QApplication.instance().aboutToQuit.connect(self.install_thread.stop)

    def set_default_statusbar(self):
        """ Show the default text in the status bar - non-blocking using update_statusbar_message Signal """
        def _set_default_statusbar_thread(update_statusbar_message: Signal):
            if not is_online():
                update_statusbar_message.emit(f'{APP_NAME} {APP_VERSION} (Offline)')
            else:
                update_statusbar_message.emit(f'{APP_NAME} {APP_VERSION}')
        t = threading.Thread(target=_set_default_statusbar_thread, args=[self.update_statusbar_message])
        t.start()

    def update_combo_install_location(self, custom_install_dir = None):
        self.updating_combo_install_location = True

        self.ui.comboInstallLocation.clear()
        self.combo_install_location_index_map = []

        current_install_dir = custom_install_dir or install_directory()
        for i, install_dir in enumerate(available_install_directories()):
            icon_name = get_install_location_from_directory_name(install_dir).get('icon')
            display_name = get_install_location_from_directory_name(install_dir).get('display_name')
            if display_name and display_name != '':
                self.ui.comboInstallLocation.addItem(QIcon.fromTheme(icon_name), f'{display_name} ({install_dir})')
            else:
                self.ui.comboInstallLocation.addItem(install_dir)
            self.combo_install_location_index_map.append(install_dir)
            if current_install_dir == install_dir:
                if custom_install_dir is not None:
                    self.updating_combo_install_location = False
                self.ui.comboInstallLocation.setCurrentIndex(i)

        self.updating_combo_install_location = False
        # Update compat list when custom install directoy is removed -- Not called because of `self.updating_combo_install_location = False` -- Could be improved?
        if custom_install_dir is not None and len(custom_install_dir) <= 0:
            self.ui.comboInstallLocation.currentIndexChanged.emit(self.ui.comboInstallLocation.currentIndex())

    def update_ui(self):
        """ update ui contents """
        install_loc = get_install_location_from_directory_name(install_directory())
        unused_ctools = 0

        self.ui.listInstalledVersions.clear()
        self.compat_tool_index_map = get_installed_ctools(install_directory())

        # Launcher specific (Lutris): Show DXVK and vkd3d-proton
        if install_loc.get('launcher') == 'lutris':
            dxvk_dir = os.path.join(install_directory(), '../../runtime/dxvk')
            vkd3d_dir = os.path.join(install_directory(), '../../runtime/vkd3d')

            self.get_installed_versions('dxvk', dxvk_dir)
            self.get_installed_versions('vkd3d', vkd3d_dir)
        # Launcher specific (Steam): Number of games using the compatibility tool
        elif install_loc.get('launcher') == 'steam' and 'vdf_dir' in install_loc:
            get_steam_app_list(install_loc.get('vdf_dir'), cached=False)  # update app list cache
            self.compat_tool_index_map += get_steam_acruntime_list(install_loc.get('vdf_dir'), cached=True)
            map = get_steam_ct_game_map(install_loc.get('vdf_dir'), self.compat_tool_index_map, cached=True)
            for ct in self.compat_tool_index_map:
                ct.no_games = len(map.get(ct, []))
        # Launcher specific (Heroic): Set number of installed games using compat tool
        elif is_heroic_launcher(install_loc.get('launcher')):
            heroic_dir = os.path.join(os.path.expanduser(install_loc.get('install_dir')), '../..')
            heroic_game_list = get_heroic_game_list(heroic_dir)
            for ct in self.compat_tool_index_map:
                ct.no_games = len([game for game in heroic_game_list if game.is_installed and ct.displayname in game.wine_info.get('name', '')])
            
            # Get DXVK/VKD3D installs for Heroic
            dxvk_dir = os.path.join(install_directory(), '../dxvk')
            vkd3d_dir = os.path.join(install_directory(), '../vkd3d')
            self.get_installed_versions('dxvk', dxvk_dir)
            self.get_installed_versions('vkd3d', vkd3d_dir)

        for ct in self.compat_tool_index_map:
            self.ui.listInstalledVersions.addItem(ct.get_displayname(unused_tr=self.tr('unused')))
            if ct.no_games == 0:
                unused_ctools += 1

        self.ui.txtActiveDownloads.setText(str(len(self.pending_downloads)))
        if len(self.pending_downloads) == 0:
            self.set_default_statusbar()
            self.progressBarDownload.setVisible(False)
            self.ui.comboInstallLocation.setEnabled(True)

        self.show_launcher_specific_information()

        if install_loc.get('launcher') == 'steam' and 'vdf_dir' in install_loc:
            self.ui.btnShowGameList.setVisible(True)
        elif install_loc.get('launcher') == 'lutris':
           self.ui.btnShowGameList.setVisible(True)
        elif is_heroic_launcher(install_loc.get('launcher')):
            self.ui.btnShowGameList.setVisible(True)
        else:
            self.ui.btnShowGameList.setVisible(False)

        self.ui.txtUnusedVersions.setText(self.tr('Unused: {unused_ctools}').format(unused_ctools=unused_ctools) if unused_ctools > 0 else '')
        self.ui.txtInstalledVersions.setText(f'{len(self.compat_tool_index_map)}')

    def get_installed_versions(self, ctool_name, ctool_dir):
        for ct in get_installed_ctools(ctool_dir):
            if ctool_name not in ct.get_displayname().lower():
                ct.displayname = f'{ctool_name} {ct.displayname}'
            self.compat_tool_index_map.append(ct)

    def install_compat_tool(self, compat_tool):
        """ install compatibility tool (called by install dialog signal) """
        if compat_tool in self.pending_downloads:
            return

        self.pending_downloads.append(compat_tool)
        self.update_ui()

        self.install_thread.buffer_mutex.lock()
        self.install_thread.buffer_not_empty.wakeOne()
        self.install_thread.buffer_mutex.unlock()

    def set_fetching_releases(self, value):
        if value and is_online():
            self.ui.statusBar().showMessage(self.tr('Fetching releases...'))
        else:
            self.set_default_statusbar()

    def set_download_progress_percent(self, value):
        """ set download progress bar value and update status bar text """
        self.progressBarDownload.setValue(value)
        if len(self.pending_downloads):
            compat_tool = self.pending_downloads[0]
            self.current_compat_tool_name = compat_tool['name'] + ' ' + compat_tool['version']
        if value == -2:
            self.ui.statusBar().showMessage(self.tr('Download canceled.'))
            self.progressBarDownload.setVisible(False)
            return
        if value == -1:
            self.ui.statusBar().showMessage(self.tr('Could not install {current_compat_tool_name}...').format(current_compat_tool_name=self.current_compat_tool_name))
            self.progressBarDownload.setVisible(False)
            return
        if value == 1:
            self.progressBarDownload.setVisible(True)
            self.ui.comboInstallLocation.setEnabled(False)
            self.ui.txtActiveDownloads.setText(str(len(self.pending_downloads)))
            self.ui.statusBar().showMessage(self.tr('Downloading {current_compat_tool_name}...').format(current_compat_tool_name=self.current_compat_tool_name))
        elif value == 99:
            self.ui.statusBar().showMessage(self.tr('Extracting {current_compat_tool_name}...').format(current_compat_tool_name=self.current_compat_tool_name))
        elif value == 99.5:
            self.ui.statusBar().showMessage(self.tr('Installing {current_compat_tool_name}...').format(current_compat_tool_name=self.current_compat_tool_name))
        elif value == 100:
            self.ui.statusBar().showMessage(self.tr('Installed {current_compat_tool_name}.').format(current_compat_tool_name=self.current_compat_tool_name))
            self.update_ui()

    def btn_add_version_clicked(self, compat_tool: str = ''):
        advanced_mode = (config_advanced_mode() == 'enabled')
        install_loc = get_install_location_from_directory_name(install_directory())

        if not compat_tool or compat_tool_available(compat_tool, self.ct_loader.get_ctobjs(install_loc, advanced_mode=advanced_mode)):
            dialog = PupguiInstallDialog(install_loc, self.ct_loader, parent=self.ui)
            dialog.compat_tool_selected.connect(self.install_compat_tool)
            dialog.is_fetching_releases.connect(self.set_fetching_releases)
            dialog.set_selected_compat_tool(compat_tool)

    def btn_remove_selcted_clicked(self):
        ctools_to_remove = []
        games_using_tools = 0
        for item in self.ui.listInstalledVersions.selectedItems():
            ct = self.compat_tool_index_map[self.ui.listInstalledVersions.row(item)]
            if ct.no_games > 0:
                games_using_tools += ct.no_games
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
        customid_dialog = PupguiCustomInstallDirectoryDialog(install_directory(), parent=self.ui)
        customid_dialog.custom_id_set.connect(self.update_combo_install_location)

    def show_launcher_specific_information(self):
        install_loc = get_install_location_from_directory_name(install_directory())
        # For Steam Flatpak only: Show that GE-Proton and Boxtron are available directly from Flathub.
        if 'steam' in install_loc.get('launcher', '') and 'Flatpak' in install_loc.get('display_name', ''):
            self.ui.statusBar().showMessage(self.tr('Info: You can get GE-Proton / Boxtron directly from Flathub!'))
            self.ui.btnSteamFlatpakCtools.setVisible(True)
        else:
            self.ui.btnSteamFlatpakCtools.setVisible(False)
    
    def list_installed_versions_item_double_clicked(self, item):
        """ Show info about compatibility tool when double clicked in list """
        ct = self.compat_tool_index_map[self.ui.listInstalledVersions.row(item)]
        install_loc = get_install_location_from_directory_name(install_directory())
        cti_dialog = PupguiCtInfoDialog(self.ui, ctool=ct, install_loc=install_loc)
        cti_dialog.batch_update_complete.connect(self.update_ui)

    def list_installed_versions_item_selection_changed(self):
        n_sel_items = len(self.ui.listInstalledVersions.selectedItems())
        if n_sel_items == 0:
            self.ui.btnRemoveSelected.setEnabled(False)
            self.ui.btnShowCtInfo.setEnabled(False)
        else:
            self.ui.btnRemoveSelected.setEnabled(True)
            self.ui.btnShowCtInfo.setEnabled(True)
        # Compatibility tools and runtimes installed by Steam (steamapps) cannot be removed
        for item in self.ui.listInstalledVersions.selectedItems():
            ct = self.compat_tool_index_map[self.ui.listInstalledVersions.row(item)]
            if ct.ct_type in [CTType.STEAM_CT, CTType.STEAM_RT]:
                self.ui.btnRemoveSelected.setEnabled(False)
                break

    def btn_show_ct_info_clicked(self):
        install_loc = get_install_location_from_directory_name(install_directory())
        for item in self.ui.listInstalledVersions.selectedItems():
            ct = self.compat_tool_index_map[self.ui.listInstalledVersions.row(item)]
            cti_dialog = PupguiCtInfoDialog(self.ui, ctool=ct, install_loc=install_loc)
            cti_dialog.batch_update_complete.connect(self.update_ui)

    def btn_steam_flatpak_ctools_clicked(self):
        """ Open dialog to open the appstore(appstream) to install Proton-GE/Boxtron from Flathub"""
        iftdialog = QDialog(parent=self.ui)
        iftdialog.setWindowTitle(self.tr('Install tool from Flathub'))
        iftdialog.setFixedSize(250, 100)
        iftdialog.setModal(True)
        lbl_description = QLabel(self.tr('Click to open your app store'))
        btn_dl_protonge = QPushButton('Proton-GE')
        btn_dl_boxtron = QPushButton('Boxtron')
        btn_dl_stl = QPushButton('Steam Tinker Launch')
        layout1 = QVBoxLayout()
        layout1.addWidget(lbl_description)
        layout1.addWidget(btn_dl_protonge)
        layout1.addWidget(btn_dl_boxtron)
        layout1.addWidget(btn_dl_stl)
        iftdialog.setLayout(layout1)
        btn_dl_protonge.clicked.connect(lambda: os.system(f'xdg-open {STEAM_PROTONGE_FLATPAK_APPSTREAM}'))
        btn_dl_boxtron.clicked.connect(lambda: os.system(f'xdg-open {STEAM_BOXTRON_FLATPAK_APPSTREAM}'))
        btn_dl_stl.clicked.connect(lambda: os.system(f'xdg-open {STEAM_STL_FLATPAK_APPSTREAM}'))
        iftdialog.show()

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
        self.pending_downloads = [] if cancel_all else self.pending_downloads[1:]
        for ctobj in self.ct_loader.get_ctobjs():
            ctobj['installer'].download_canceled = True
        self.update_ui()

    @Slot(str, str, QMessageBox.Icon)
    def show_msgbox(self, title: str, text: str, icon = QMessageBox.NoIcon):
        """ Show a message box with main window as parent """
        mb = QMessageBox(parent=self.ui)
        mb.setWindowTitle(title)
        mb.setText(text)
        mb.setIcon(icon)
        mb.show()

    @Slot(str, str, str, MsgBoxType, QMessageBox.Icon)
    def show_msgbox_question(self, title: str, text: str, checkbox_text: str, type: MsgBoxType, icon = QMessageBox.NoIcon) -> bool:
        """ Show a message box with main window as parent (blocking connection, with optional checkbox) """
        mb = QMessageBox(parent=self.ui)
        mb.setWindowTitle(title)
        mb.setText(text)
        mb.setIcon(icon)
        cb = None

        if type in [MsgBoxType.OK_CANCEL, MsgBoxType.OK_CANCEL_CB, MsgBoxType.OK_CANCEL_CB_CHECKED]:
            mb.setStandardButtons(QMessageBox.StandardButton.Ok)
            mb.addButton(QMessageBox.StandardButton.Cancel)
            mb.setDefaultButton(QMessageBox.StandardButton.Cancel)

        if type in [MsgBoxType.OK_CB, MsgBoxType.OK_CANCEL_CB, MsgBoxType.OK_CB_CHECKED, MsgBoxType.OK_CANCEL_CB_CHECKED]:
            cb = QCheckBox(checkbox_text)
            mb.setCheckBox(cb)
            
        if type in [MsgBoxType.OK_CB_CHECKED, MsgBoxType.OK_CANCEL_CB_CHECKED]:
            cb.setChecked(True)

        res = mb.exec()

        result = MsgBoxResult()
        result.msgbox_type = type
        if res == 1024:
            result.button_clicked = MsgBoxResult.BUTTON_OK
        else:
            result.button_clicked = MsgBoxResult.BUTTON_CANCEL
        if cb:
            result.is_checked = cb.isChecked()

        self.set_msgcb_answer(result)

    def set_msgcb_answer(self, answer: MsgBoxResult):
        self.msgcb_answer_lock.lock()
        self.msgcb_answer = answer
        self.msgcb_answer_lock.unlock()

    def get_msgcb_answer(self) -> MsgBoxResult:
        self.msgcb_answer_lock.lock()
        answer = self.msgcb_answer
        self.msgcb_answer_lock.unlock()
        return answer


class PupguiApp(QApplication):
    message_box_message = Signal((str, str, QMessageBox.Icon))


def main():
    """ ProtonUp-Qt main function. Called from __main__.py """
    print(f'{APP_NAME} {APP_VERSION} by DavidoTek. Build Info: {BUILD_INFO}.')
    print_system_information()
    if not single_instance():
        print("Second instance of ProtonUp-Qt found!")
        return

    create_compatibilitytools_folder()
    download_awacy_gamelist()

    app = PupguiApp(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setWindowIcon(QIcon.fromTheme('net.davidotek.pupgui2'))
    app.setDesktopFileName('net.davidotek.pupgui2.desktop')

    lang = QLocale.languageToCode(QLocale().language())
    lname = QLocale().name()

    print(f'Loading locale {lang} / {lname}')

    ldata = None
    try:
        ldata = pkgutil.get_data(__name__, f'resources/i18n/pupgui2_{lname}.qm')  # Example: pupgui2_zh_TW.qm
    except:
        pass
    else:
        translator = QTranslator()
        if translator.load(ldata):
            app.installTranslator(translator)

    if ldata is None:
        try:
            ldata = pkgutil.get_data(__name__, f'resources/i18n/pupgui2_{lang}.qm') # Example: pupgui2_de.qm
        except:
            pass
        else:
            translator = QTranslator()
            if translator.load(ldata):
                app.installTranslator(translator)

    qtTranslator = QTranslator()
    if qtTranslator.load(QLocale(), 'qt', '_', QLibraryInfo.location(QLibraryInfo.TranslationsPath)):
        app.installTranslator(qtTranslator)

    apply_dark_theme(app)

    MainWindow()

    ret = app.exec()
    shutil.rmtree(TEMP_DIR, ignore_errors=True)

    # Flatpak workaround: Delete STL dir if it isn't installed (folder is always created for sandbox access)
    if os.path.exists('/.flatpak-info') and len(os.listdir(STEAM_STL_INSTALL_PATH)) == 0:
        subprocess.run(['flatpak-spawn', '--host', 'rm', '-r', STEAM_STL_INSTALL_PATH])

    sys.exit(ret)
