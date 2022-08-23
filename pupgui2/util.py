import os, subprocess, shutil
import sys
import platform
import threading
from typing import Dict, List
import webbrowser
import requests
from configparser import ConfigParser

import PySide6
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from .constants import POSSIBLE_INSTALL_LOCATIONS, CONFIG_FILE, PALETTE_DARK, TEMP_DIR
from .constants import AWACY_GAME_LIST_URL, LOCAL_AWACY_GAME_LIST
from .datastructures import BasicCompatTool, CTType


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
        if not is_plasma and darkmode_enabled:
            app.setStyle('Fusion')
            app.setPalette(PALETTE_DARK())
        elif is_plasma:
            pass
        else:
            app.setStyle('Fusion')
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
                print('Error trying to create compatibility tools folder ' + str(install_dir) + ': ' + str(e))


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


def config_custom_install_location(install_dir=None, launcher='') -> Dict[str, str]:
    """
    Read/update config for the custom install location
    Write install_dir, launcher to config or read if install_dir=None or launcher=None
    Return Type: dict
        Contents: 'install_dir', 'display_name' (always ''), 'launcher'
    """
    config = ConfigParser()

    if install_dir and launcher:
        config.read(CONFIG_FILE)
        if not config.has_section('pupgui2'):
            config.add_section('pupgui2')
        config['pupgui2']['custom_install_dir'] = install_dir
        config['pupgui2']['custom_install_launcher'] = launcher
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w') as file:
            config.write(file)
    elif install_dir == 'remove' and os.path.exists(CONFIG_FILE):
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
                    versions_found.append(folder + ' - ' + ver.strip())
                else:
                    versions_found.append(folder)

        return versions_found


def remove_ctool(ver: str, install_dir: str) -> bool:
    """
    Remove compatibility tool folder
    Return Type: bool
    """
    target = os.path.join(install_dir, ver.split(' - ')[0])
    if os.path.exists(target):
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
    i = 0
    for ver in unsorted:
        i += 1
        if ver.startswith('GE-Proton'):
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

    sorted_vers = []
    for v in sorted(ver_dict):
        sorted_vers.append(ver_dict[v])

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
        print('Could not open webbrowser url ' + str(url))


def print_system_information() -> None:
    """
    Print system information like Python/Qt/OS version to the console
    """
    ver_info = 'Python ' + sys.version.replace('\n', '')
    ver_info += ', PySide ' + PySide6.__version__ + '\n'
    ver_info += 'Platform: '
    try:
        f = open('/etc/lsb-release')
        l = f.readlines()
        ver_info += l[0].strip().split('=')[1] + ' ' + l[1].strip().split('=')[1] + ' '
        f.close()
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
        f = open(lockfile, 'r')
        pid = f.read()
        f.close()
        cmdline_file = os.path.join('/proc/', pid, 'cmdline')
        if os.path.exists(cmdline_file):
            f = open(cmdline_file, 'r')
            cmdline = f.read()
            f.close()
            if 'pupgui2' in cmdline:
                return False
    try:
        os.mkdir(TEMP_DIR)
        f = open(lockfile, 'w')
        f.write(str(os.getpid()))
        f.close()
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
