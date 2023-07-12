import os
import sys
import subprocess
import shutil
import platform
import threading
import webbrowser
import requests
import zipfile
import tarfile

import zstandard

from configparser import ConfigParser
from typing import Dict, List, Union, Tuple

import PySide6
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication, QStyleFactory, QMessageBox, QCheckBox

from pupgui2.constants import POSSIBLE_INSTALL_LOCATIONS, CONFIG_FILE, PALETTE_DARK, TEMP_DIR
from pupgui2.constants import AWACY_GAME_LIST_URL, LOCAL_AWACY_GAME_LIST
from pupgui2.datastructures import BasicCompatTool, CTType
from pupgui2.steamutil import remove_steamtinkerlaunch


def create_msgbox(
    title: str,
    text: str,
    info_text: str = None,
    buttons: Union[QMessageBox.StandardButton, Tuple[QMessageBox.StandardButton]] = QMessageBox.Ok,
    default_button: QMessageBox.StandardButton = QMessageBox.Ok,
    detailed_text: str = None,
    icon: QMessageBox.Icon = QMessageBox.Information,
    execute: bool = True,
) -> Union[int, QMessageBox]:
    """
    Create a new message box and show it (if execute=True) or return it (if execute=False)
    Args:
        text: The text to show.
        info_text: The informative text to show.
        buttons: The buttons to show, can be either a button or a tuple of buttons.
        default_button: The default button to use when shown.
        detailed_text: The detailed text to show.
        icon: The icon to show, default is the 'information' icon.
        execute: Whether to execute the message box after creating, default to True.
    Returns:
        A QMessageBox if execute is set to False, else returns the exit code from the message box.
        If custom buttons (parameter buttons) are specified, a tuple (QMessageBox, List[QMessageBox.StandardButton])
            or (int, List[QMessageBox.StandardButton]) is returned.
    """
    msg_box = QMessageBox()
    msg_box.setWindowTitle(title)
    msg_box.setText(text)
    if info_text:
        msg_box.setInformativeText(info_text)
    custom_buttons = []
    if isinstance(buttons, (list, tuple, set)):
        for btn in buttons:
            if isinstance(btn[0], str):
                custom_buttons.append(msg_box.addButton(btn[0], btn[1]))
            else:
                custom_buttons.append(msg_box.addButton(btn[0]))
    else:
        msg_box.setStandardButtons(buttons)
    msg_box.setDefaultButton(default_button)
    if detailed_text:
        msg_box.setDetailedText(detailed_text)
    msg_box.setIcon(icon)
    if execute:
        if custom_buttons:
            return msg_box.exec(), custom_buttons
        return msg_box.exec()

    if custom_buttons:
        return msg_box, custom_buttons
    return msg_box


def apply_dark_theme(app: QApplication) -> None:
    """
    Apply custom dark mode to Qt application when not using KDE Plasma
    and a dark GTK theme is selected (name ends with '-dark')
    Tries to detect the preference from org.gnome.desktop.interface color-scheme
    """
    theme = config_theme()

    if theme == 'light':
        app.setStyle('Fusion')
        app.setPalette(QStyleFactory.create('fusion').standardPalette())
    elif theme == 'dark':
        app.setStyle('Fusion')
        app.setPalette(PALETTE_DARK())
    else:
        is_plasma = 'plasma' in os.environ.get('DESKTOP_SESSION', '')
        darkmode_enabled = False
        try:
            ret = subprocess.run(['gsettings', 'get', 'org.gnome.desktop.interface', 'color-scheme'], capture_output=True).stdout.decode('utf-8').strip().strip("'")
            if ret == 'prefer-dark':
                darkmode_enabled = True
            else:
                ret = subprocess.run(['gsettings', 'get', 'org.gnome.desktop.interface', 'gtk-theme'], capture_output=True).stdout.decode('utf-8').strip().strip("'").lower()
                if ret.endswith('-dark') or ret == 'HighContrastInverse':
                    darkmode_enabled = True
        except:
            pass
        if not is_plasma:
            app.setStyle('Fusion')
            if darkmode_enabled:
                app.setPalette(PALETTE_DARK())
            else:
                app.setPalette(QStyleFactory.create('fusion').standardPalette())


def config_theme(theme=None) -> str:
    """
    Read/update config for the theme
    Write theme to config or read if theme=None
    Return Type: str
    """
    config = ConfigParser()

    if theme:
        config.read(CONFIG_FILE)
        if not config.has_section('pupgui2'):
            config.add_section('pupgui2')
        config['pupgui2']['theme'] = theme
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w') as file:
            config.write(file)
    elif os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
        if config.has_option('pupgui2', 'theme'):
            return config['pupgui2']['theme']
    return theme


def config_advanced_mode(advmode=None) -> str:
    """
    Read/update config for the advanced mode
    Write advmode to config or read if advmode=None
    Return Type: str
    """
    config = ConfigParser()

    if advmode:
        config.read(CONFIG_FILE)
        if not config.has_section('pupgui2'):
            config.add_section('pupgui2')
        config['pupgui2']['advancedmode'] = advmode
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w') as file:
            config.write(file)
    elif os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
        if config.has_option('pupgui2', 'advancedmode'):
            return config['pupgui2']['advancedmode']
    return advmode


def create_compatibilitytools_folder() -> None:
    """
    Create compatibilitytools folder if launcher is installed but compatibilitytools folder doesn't exist
    Will check all launchers specified in constants.POSSIBLE_INSTALL_LOCATIONS
    """
    for loc in POSSIBLE_INSTALL_LOCATIONS:
        install_dir = os.path.normpath(os.path.expanduser(loc['install_dir']))
        parent_dir = os.path.abspath(os.path.join(install_dir, os.pardir))

        if os.path.exists(parent_dir) and not os.path.exists(install_dir):
            try:
                os.mkdir(install_dir)
            except Exception as e:
                print(f'Error trying to create compatibility tools folder {str(install_dir)}: {str(e)}')


def available_install_directories() -> List[str]:
    """
    List available install directories
    Return Type: List[str]
    """
    available_dirs = []
    for loc in POSSIBLE_INSTALL_LOCATIONS:
        install_dir = os.path.expanduser(loc['install_dir'])
        if os.path.exists(install_dir):
            available_dirs.append(install_dir)
    install_dir = config_custom_install_location().get('install_dir')
    if install_dir and os.path.exists(install_dir):
        available_dirs.append(install_dir)
    return available_dirs


def get_install_location_from_directory_name(install_dir: str) -> Dict[str, str]:
    """
    Get install location dict from install directory name
    Return Type: dict
        Contents: 'install_dir', 'display_name', 'launcher'
    """
    for loc in POSSIBLE_INSTALL_LOCATIONS:
        if os.path.expanduser(install_dir) == os.path.expanduser(loc['install_dir']):
            return loc
    custom_install_location = config_custom_install_location()
    if custom_install_location.get('install_dir') and os.path.expanduser(install_dir) == os.path.expanduser(custom_install_location.get('install_dir')) and custom_install_location.get('launcher'):
        return custom_install_location
    return {'install_dir': install_dir, 'display_name': 'unknown', 'launcher': ''}


# modified install_directory function from protonup 0.1.4
def install_directory(target=None) -> str:
    """
    Read/update config for the selected install directory
    Write target to config or read from config if target=None
    Return Type: str
    """
    config = ConfigParser()

    if target and target.lower() != 'get':
        if target.lower() == 'default':
            target = POSSIBLE_INSTALL_LOCATIONS[0]['install_dir']
        if not target.endswith('/'):
            target += '/'
        config.read(CONFIG_FILE)
        if not config.has_section('pupgui'):
            config.add_section('pupgui')
        config['pupgui']['installdir'] = target
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w') as file:
            config.write(file)
    elif os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
        if config.has_option('pupgui', 'installdir'):
            target = os.path.expanduser(config['pupgui']['installdir'])

    if target in available_install_directories():
        return target
    elif len(available_install_directories()) > 0:
        install_directory(available_install_directories()[0])
        return available_install_directories()[0]
    return ''


def config_custom_install_location(install_dir=None, launcher='', remove=False) -> Dict[str, str]:
    """
    Read/update config for the custom install location
    Write install_dir, launcher to config or read if install_dir=None or launcher=None
    Return Type: dict
        Contents: 'install_dir', 'display_name' (always ''), 'launcher'
    """
    config = ConfigParser()

    if install_dir and launcher and not remove:
        config.read(CONFIG_FILE)
        if not config.has_section('pupgui2'):
            config.add_section('pupgui2')
        config['pupgui2']['custom_install_dir'] = install_dir
        config['pupgui2']['custom_install_launcher'] = launcher
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w') as file:
            config.write(file)
    elif remove and os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
        if config.has_option('pupgui2', 'custom_install_dir'):
            config.remove_option('pupgui2', 'custom_install_dir')
        if config.has_option('pupgui2', 'custom_install_launcher'):
            config.remove_option('pupgui2', 'custom_install_launcher')
        with open(CONFIG_FILE, 'w') as file:
            config.write(file)
    elif os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
        if config.has_option('pupgui2', 'custom_install_dir') and config.has_option('pupgui2', 'custom_install_launcher'):
            install_dir = config['pupgui2']['custom_install_dir']
            launcher = config['pupgui2']['custom_install_launcher']

    if install_dir and not install_dir.endswith('/'):
        install_dir += '/'
    return {'install_dir': install_dir, 'display_name': '', 'launcher': launcher}


def list_installed_ctools(install_dir: str, without_version=False) -> List[str]:
    """
    List installed compatibility tool versions
    Returns the name of the tool and the version from VERSION.txt if without_version=False
    Return Type: List[str]
    """
    versions_found = []

    if os.path.exists(install_dir):
        folders = os.listdir(install_dir)
        for folder in folders:
            ver_file = os.path.join(install_dir, folder, 'VERSION.txt')
            if os.path.exists(ver_file) and not without_version:
                with open(ver_file, 'r') as f:
                    ver = f.read()
                versions_found.append(f'{folder} - {ver.strip()}')
            else:
                versions_found.append(folder)

    return versions_found


def remove_ctool(ver: str, install_dir: str) -> bool:
    """
    Remove compatibility tool folder
    Return Type: bool
    """
    target = os.path.join(install_dir, ver.split(' - ')[0])
    # Special case hack to remove SteamTinkerLaunch
    if 'steamtinkerlaunch' in target.lower():
        mb = QMessageBox()
        cb = QCheckBox(QCoreApplication.instance().translate('util.py', 'Delete SteamTinkerLaunch configuration'))
        mb.setWindowTitle(QCoreApplication.instance().translate('util.py', 'Uninstalling SteamTinkerLaunch'))
        mb.setText(QCoreApplication.instance().translate('util.py', 'SteamTinkerLaunch will be removed from your system. If this tool was installed with ProtonUp-Qt, this will also update your PATH to remove SteamTinkerLaunch.\nDo you want the configuration to be removed?'))
        mb.setCheckBox(cb)
        mb.exec()
        return remove_steamtinkerlaunch(compat_folder=target, remove_config=cb.isChecked())
    elif os.path.exists(target):
        shutil.rmtree(target)
        return True
    return False


def sort_compatibility_tool_names(unsorted: List[str], reverse=False) -> List[str]:
    """
    Sort the list of compatibility tools: First sort alphabetically using sorted() then sort by Proton version
    Return Type: List[str]
    """
    unsorted = sorted(unsorted)
    ver_dict = {}
    for i, ver in enumerate(unsorted, start=1):
        if ver.startswith('GE-Proton'):
            ver_dict[100+i] = ver
        elif 'SteamTinkerLaunch' in ver:
            ver_dict[100+i] = ver
        elif 'Proton-' in ver:
            try:
                ver_string = ver.split('-')[1]
                ver_major = int(ver_string.split('.')[0])
                ver_minor = int(ver_string.split('.')[1])
                ver_dict[ver_major * 10 + ver_minor] = ver
            except:
                ver_dict[i] = ver
        else:
            ver_dict[i] = ver

    sorted_vers = [ver_dict[v] for v in sorted(ver_dict)]

    if reverse:
        sorted_vers.reverse()

    return sorted_vers


def open_webbrowser_thread(url: str) -> None:
    """
    Open the specified URL in the default webbrowser. Non-blocking (using Threads)
    """
    try:
        t = threading.Thread(target=webbrowser.open, args=[url])
        t.start()
    except:
        print(f'Could not open webbrowser url {url}')


def print_system_information() -> None:
    """
    Print system information like Python/Qt/OS version to the console
    """
    ver_info = 'Python ' + sys.version.replace('\n', '')
    ver_info += f', PySide {PySide6.__version__}' + '\n'
    ver_info += 'Platform: '
    try:
        with open('/etc/lsb-release') if os.path.exists('/etc/lsb-release') else open('/etc/os-release') as f:
            l = f.readlines()
            ver_info += l[0].strip().split('=')[1] + ' ' + l[1].strip().split('=')[1] + ' '
            ver_info = ver_info.replace('"', '')
    except:
        pass
    ver_info += str(platform.platform())
    print(ver_info)


def single_instance() -> bool:
    """
    Creates a lockfile to detect other instances of the app. Returns False if another instance is found
    Return Type: bool
    """
    lockfile = os.path.join(TEMP_DIR, 'lockfile')
    if os.path.exists(lockfile):
        with open(lockfile, 'r') as f:
            pid = f.readline().strip()
        cmdline_file = os.path.join('/proc/', pid, 'cmdline')
        if os.path.exists(cmdline_file):
            with open(cmdline_file, 'r') as f:
                cmdline = f.read()
            if 'pupgui2' in cmdline and int(pid) != os.getpid():
                return False
    try:
        os.mkdir(TEMP_DIR)
        with open(lockfile, 'w') as f:
            f.write(str(os.getpid()))
    except:
        pass
    return True


def download_awacy_gamelist() -> None:
    """
    Download the areweanticheatyet.com gamelist
    """
    def _download_awacy_gamelist_thread():
        r = requests.get(AWACY_GAME_LIST_URL)
        with open(LOCAL_AWACY_GAME_LIST, 'wb') as f:
            f.write(r.content)
    t = threading.Thread(target=_download_awacy_gamelist_thread)
    t.start()


def get_installed_ctools(install_dir: str) -> List[BasicCompatTool]:
    """
    Returns installed compatibility tools sorted after name/version
    Return Type: List[BasicCompatTool]
    """
    ctools = []

    if os.path.exists(install_dir):
        folders = os.listdir(install_dir)
        folders = sort_compatibility_tool_names(folders)
        for folder in folders:
            if not os.path.isdir(os.path.join(install_dir, folder)):
                continue
            
            ct = BasicCompatTool(folder, install_dir, folder, ct_type=CTType.CUSTOM)

            ver_file = os.path.join(install_dir, folder, 'VERSION.txt')
            if os.path.exists(ver_file):
                with open(ver_file, 'r') as f:
                    ver = f.read().strip()
                    ct.set_version(ver)

            ctools.append(ct)

    return ctools


def host_which(name: str) -> str:
    """
    Runs 'which <name>' on the host system (either normal or using 'flatpak-spawn --host' when inside Flatpak)
    Return Type: str
    """
    proc_prefix = ['flatpak-spawn', '--host'] if os.path.exists('/.flatpak-info') else []
    which = subprocess.run(proc_prefix + ['which', name], universal_newlines=True, stdout=subprocess.PIPE).stdout.strip()
    return None if which == '' else which


def ghapi_rlcheck(json: dict):
    """ Checks if the given GitHub request response (JSON) contains a rate limit warning and warns the user """
    if type(json) == dict:
        if 'API rate limit exceeded' in json.get('message', ''):
            print('Warning: GitHub API rate limit exceeded. See https://github.com/DavidoTek/ProtonUp-Qt/issues/161#issuecomment-1358200080 for details.')
            QApplication.instance().message_box_message.emit(
                QCoreApplication.instance().translate('util.py', 'Warning: GitHub API rate limit exceeded!'),
                QCoreApplication.instance().translate('util.py', 'GitHub API rate limit exceeded. You may need to wait a while or specify a GitHub API key if you have one.\n\nSee https://github.com/DavidoTek/ProtonUp-Qt/issues/161#issuecomment-1358200080 for details.'),
                QMessageBox.Warning
                )
    return json


def is_online(host='https://api.github.com/repos/', timeout=3) -> bool:
    """
    Attempts to ping a given host using `requests`.
    Returns False if `requests` raises a `ConnectionError` or `Timeout` exception, otherwise returns True 
    
    Return Type: bool
    """
    try:
        requests.get(host, timeout=timeout)
        return True
    except (requests.ConnectionError, requests.Timeout):
        return False


def compat_tool_available(compat_tool: str, ctobjs: List[dict]) -> bool:
    """ Return whether a compat tool is available for a given launcher """

    return compat_tool in [ctobj['name'] for ctobj in ctobjs]


def get_dict_key_from_value(d, searchval):
    """
    Fetch a given dictionary key from a given value.
    Returns the given value if found, otherwise None.
    """
    for key, value in d.items():
        if value == searchval:
            return key
    else:
        return None


def get_combobox_index_by_value(combobox, value: str) -> int:
    """
    Get the index in a combobox where a text value is located.
    Returns an integer >= 0 if found, otherwise -1.

    Return Type: int
    """

    if value:
        for i in range(combobox.count()):
            if value == combobox.itemText(i):
                return i

    return -1


def remove_if_exists(path: str):

    """
    Remove a file or folder at a path if it exists.
    """

    try:
        if os.path.exists(path):
            if os.path.isfile(path):
                os.remove(path)
            elif os.path.isdir(path):
                shutil.rmtree(path)
    except OSError as e:
        print(f'Could not remove item at {path}: {e}')


def write_tool_version(tool_dir: str, version: str):

    """
    Write the version of a tool to a VERSION.txt in tool_dir.
    """

    with open(os.path.join(tool_dir, 'VERSION.txt'), 'w') as f:
        f.write(f'{version}\n')


## Extraction utility methods ##


def extract_paths_exist(archive_path: str, extract_path: str) -> bool:

    """
    Checks if an archive exists at a path, and that an extraction path exists. Returns True if both exist, otherwise False.

    Return Type: bool
    """

    archive_path_exists: bool = os.path.isfile(archive_path)
    extract_path_exists: bool = os.path.isdir(os.path.dirname(extract_path))  # Full path may not exist as this may be created during extraction

    if not archive_path_exists:
        print(f'Archive file does not exist: {archive_path}')
    if not extract_path_exists:
        print(f'Extract path does not exist: {extract_path}')
    
    return archive_path_exists and extract_path_exists


def extract_zip(zip_path: str, extract_path: str) -> bool:

    """
    Extracts a Zip archive at zip_path to extract_path using ZipFile. Returns True if the zip extracts successfully, otherwise False.

    Return Type: bool
    """

    if not extract_paths_exist(zip_path, extract_path):
        return False

    try:
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(extract_path)
        return True
    except zipfile.BadZipFile:
        print(f'Zip file \'{zip_path}\' appears to be invalid!')
    except Exception as e:
        print(f'Failed to extract zip file \'{zip_path}\': {e}')

    return False


# Default mode 'r:' is for regular tars
def extract_tar(tar_path: str, extract_path: str, mode: str = 'r:') -> bool:

    """
    Extracts a Tar archive at tar_path to extract_path using tarfile. Returns True if tar extracts successfully, otherwise False.

    Return Type: bool
    """

    if not extract_paths_exist(tar_path, extract_path):
        return False

    try:
        if not mode.startswith('r:'):
            mode = f'r:{mode}'

        with tarfile.open(tar_path, mode) as tf:
            tf.extractall(extract_path)
        return True
    except tarfile.ReadError:
        print(f'Could not read tar file \'{tar_path}\'!')
    except Exception as e:
        print(f'Failed to extract tar file \'{tar_path}\': {e}')
    
    return False


def extract_tar_zst(zst_path: str, extract_path: str) -> bool:

    """
    Extract a .tar.zst file at zst_path to extract_path using ZstdDecompressor and tarfile. Returns True if full archive extracts succesfully, otherwise False.
    """

    if not extract_paths_exist(zst_path, extract_path):
        return False

    try:
        with open(zst_path, 'rb') as zf:
            zf_data = zstandard.ZstdDecompressor().stream_reader(zf)
            with tarfile.open(zst_path, 'r|', fileobj=zf_data) as tf:
                tf.extractall(extract_path)

        return True
    except zstandard.ZstdError as zste:  # Error reading Zst file
        print(f'Failed to extract zst file \'{zst_path}\': {zste}')
    except tarfile.ReadError as tfe:  # Error reading tar file
        print(f'Could not read tar file: {tfe}')
    except Exception as e:  # General error
        print(f'Could not extract archive \'{zst_path}\': {e}')

    return False
