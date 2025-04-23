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
import pkgutil
import random

import zstandard

from configparser import ConfigParser
from typing import Any, Callable

import PySide6
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication, QComboBox, QStyleFactory, QMessageBox, QCheckBox

from pupgui2.constants import POSSIBLE_INSTALL_LOCATIONS, CONFIG_FILE, PALETTE_DARK, PALETTE_STEAMUI, TEMP_DIR, IS_FLATPAK
from pupgui2.constants import AWACY_GAME_LIST_URL, LOCAL_AWACY_GAME_LIST
from pupgui2.constants import GITHUB_API, GITLAB_API, GITLAB_API_RATELIMIT_TEXT
from pupgui2.datastructures import BasicCompatTool, CTType, Launcher, SteamApp, LutrisGame, HeroicGame
from pupgui2.datastructures import HardwarePlatform
from pupgui2.steamutil import remove_steamtinkerlaunch, is_valid_steam_install


def create_msgbox(
    title: str,
    text: str,
    info_text: str = None,
    buttons: QMessageBox.StandardButton | tuple[QMessageBox.StandardButton] = QMessageBox.Ok,
    default_button: QMessageBox.StandardButton = QMessageBox.Ok,
    detailed_text: str = None,
    icon: QMessageBox.Icon = QMessageBox.Information,
    execute: bool = True,
) -> int | QMessageBox:
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
        If custom buttons (parameter buttons) are specified, a tuple (QMessageBox, list[QMessageBox.StandardButton])
            or (int, list[QMessageBox.StandardButton]) is returned.
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

    # Configure theme if not set. Default to Steam Deck theme if running on Steam Deck
    if theme == None and detect_platform() == HardwarePlatform.STEAM_DECK:
        theme = 'steam'
        config_theme(theme)
    elif theme == None:
        theme = 'system'
        config_theme(theme)

    if theme == 'light':
        app.setStyle('Fusion')
        app.setPalette(QStyleFactory.create('fusion').standardPalette())
    elif theme == 'dark':
        app.setStyle('Fusion')
        app.setPalette(PALETTE_DARK())
    elif theme == 'steam':
        app.setPalette(PALETTE_STEAMUI())
        stylesheet = pkgutil.get_data(__name__, 'resources/themes/steamdeck.qss')
        app.setStyleSheet(stylesheet.decode('utf-8'))
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


def read_update_config_value(option: str, value, section: str = 'pupgui2', config_file: str = CONFIG_FILE) -> str:

    """
    Uses ConfigParser to read a value with a given option from a given section from a given config file.
    By default, will read a option and a value from the 'pupgui2' section in CONFIG_FILE path in constants.py.
    """

    config = ConfigParser()

    # Write value if given
    if value:
        config.read(config_file)
        if not config.has_section(section):
            config.add_section(section)
        config[section][option] = value
        os.makedirs(os.path.dirname(config_file), exist_ok=True)

        with open(config_file, 'w') as cfg:
            config.write(cfg)
    # If no value, attempt to read from config
    elif os.path.exists(config_file):
        config.read(config_file)
        if config.has_option(section, option):
            value = config[section][option]

    return value


def config_theme(theme=None) -> str:
    """
    Read/update config for the theme
    Write theme to config or read if theme=None
    Return Type: str
    """

    return read_update_config_value('theme', theme, section='pupgui2')


def config_advanced_mode(advmode=None) -> str:
    """
    Read/update config for the advanced mode
    Write advmode to config or read if advmode=None
    Return Type: str
    """

    return read_update_config_value('advancedmode', advmode, section='pupgui2')


def config_github_access_token(github_token=None):

    """
    Read/update config for GitHub Access Token
    """

    return read_update_config_value('github_api_token', github_token, section='pupgui2')


def config_gitlab_access_token(gitlab_token=None):

    """
    Read/update config for GitLab Access Token
    """

    return read_update_config_value('gitlab_api_token', gitlab_token, section='pupgui2')


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


def is_valid_launcher_installation(loc) -> bool:

    """
    Check whether a launcher installation is actually valid based on per-launcher criteria
    Return Type: bool
    """

    install_dir = os.path.expanduser(loc['install_dir'])

    # Right now we only check to make sure regular Steam (not Flatpak or Snap) has config.vdf and libraryfolders.vdf
    # because Steam can leave behind its directory structure when uninstalled, but not these files.
    #
    # In future we could expand this to other Steam flavours and other launchers.
    if loc['display_name'] == 'Steam':  # This seems to get called many times, why?
        # get the parent of the compatibility tools install directory
        # use abspath here as install_dir could be a symlink, https://github.com/DavidoTek/ProtonUp-Qt/pull/381
        launcher_root_dir = os.path.abspath(os.path.join(install_dir, '..'))
        return is_valid_steam_install(launcher_root_dir)
    
    return os.path.exists(install_dir)  # Default to path check for all other launchers


def available_install_directories() -> list[str]:
    """
    List available install directories
    Return Type: list[str]
    """
    available_dirs = []
    for loc in POSSIBLE_INSTALL_LOCATIONS:
        install_dir = os.path.expanduser(loc['install_dir'])
        # only add unique paths to available_dirs
        if is_valid_launcher_installation(loc) and not install_dir in available_dirs:
            available_dirs.append(install_dir)
    install_dir = config_custom_install_location().get('install_dir')
    if install_dir and os.path.exists(install_dir) and not install_dir in available_dirs:
        available_dirs.append(install_dir)
    return available_dirs


def get_install_location_from_directory_name(install_dir: str) -> dict[str, str]:
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


def config_custom_install_location(install_dir=None, launcher='', remove=False) -> dict[str, Any]:
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


def list_installed_ctools(install_dir: str, without_version=False) -> list[str]:
    """
    List installed compatibility tool versions
    Returns the name of the tool and the version from VERSION.txt if without_version=False
    Return Type: list[str]
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


def sort_compatibility_tool_names(unsorted: list[str], reverse=False) -> list[str]:
    """
    Sort the list of compatibility tools: First sort alphabetically using sorted() then sort by Proton version
    Return Type: list[str]
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
    # Python and PySide version
    ver_info = 'Python ' + sys.version.replace('\n', '')
    ver_info += f', PySide {PySide6.__version__}' + '\n'

    # OS release (or Flatpak runtime)
    ver_info += 'Platform: '
    try:
        with open('/etc/lsb-release') if os.path.exists('/etc/lsb-release') else open('/etc/os-release') as f:
            l = f.readlines()
            ver_info += l[0].strip().split('=')[1] + ' ' + l[1].strip().split('=')[1]
            ver_info = ver_info.replace('"', '')
    except:
        pass
    ver_info += ", " + str(platform.platform())

    # Host OS release if running in Flatpak
    if IS_FLATPAK:
        ver_info += " (Flatpak)"
        ver_info += '\nPlatform: '
        cmd = ["flatpak-spawn", "--host", "cat", "/etc/os-release"]
        try:
            l = subprocess.check_output(cmd).decode("utf-8").splitlines()
            ver_info += l[0].strip().split('=')[1] + ' ' + l[1].strip().split('=')[1] + ' '
            ver_info = ver_info.replace('"', '')
            ver_info += " (Host)"   
        except Exception as e:
            print(f"ERROR while calling detect_platform(): {e}")

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

    if not is_online():
        return

    t = threading.Thread(target=_download_awacy_gamelist_thread)
    t.start()


def get_installed_ctools(install_dir: str) -> list[BasicCompatTool]:
    """
    Returns installed compatibility tools sorted after name/version
    Return Type: list[BasicCompatTool]
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
    proc_prefix = ['flatpak-spawn', '--host'] if IS_FLATPAK else []
    which = subprocess.run(proc_prefix + ['which', name], universal_newlines=True, stdout=subprocess.PIPE).stdout.strip()
    return None if which == '' else which


def host_path_exists(path: str, is_file: bool) -> bool:
    """
    Returns whether the given path exists on the host system

    Parameters:
        path: str
            Path which exists or not
        is_file: bool
            Whether to check for a file (is_file=True) or a directory (is_file=False)

    Return Type: bool
    """
    path = os.path.expanduser(path)
    proc_prefix = 'flatpak-spawn --host' if IS_FLATPAK else ''
    parameter = 'f' if is_file else 'd'  # check file using -f and directory using -d
    ret = os.system(proc_prefix + ' bash -c \'if [ -' + parameter + ' "' + path + '" ]; then exit 1; else exit 0; fi\'')
    return bool(ret) 


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


def glapi_rlcheck(json: dict):
    if type(json) == dict:
        # Is 'message' the right key? GitLab should return it as plaintext
        # See: https://docs.gitlab.com/ee/administration/settings/user_and_ip_rate_limits.html#use-a-custom-rate-limit-response
        if any(rate_limit_msg in json.get('message', '') for rate_limit_msg in GITLAB_API_RATELIMIT_TEXT):
            print('Warning: GitLab API rate limit exceeded. You may need to wait a while or specify a GitLab API token generated for the given instance.')
            QApplication.instance().message_box_message.emit(
                QCoreApplication.instance().translate('util.py', 'Warning: GitLab API rate limit exceeded!'),
                QCoreApplication.instance().translate('util.py', 'GitLab API rate limite exceeded. You may want to wait a while or specify a GitLab API key generated for this GitLab instance if you have one.'),
                QMessageBox.Warning
            )
    return json


def is_gitlab_instance(url: str) -> bool:
    """
    Check if a full API endpoint URL is in the list of known GitLab instances.
    Return Type: bool
    """

    return any(instance in url for instance in GITLAB_API)


def is_online(host='https://api.github.com/rate_limit/', timeout=5) -> bool:
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


# Only used for dxvk and dxvk-async right now, but is potentially useful to more ctmods?
def fetch_project_releases(releases_url: str, rs: requests.Session, count=100, page=1) -> list[str]:

    """
    List available releases for a given project URL hosted using requests.
    Return Type: list[str]
    """
    releases_api_url: str = f'{releases_url}?per_page={count}&page={page}'

    releases: dict = {}
    tag_key: str = ''
    if GITHUB_API in releases_url:
        releases = ghapi_rlcheck(rs.get(releases_api_url).json())
        tag_key = 'tag_name'
    elif is_gitlab_instance(releases_url):
        releases = glapi_rlcheck(rs.get(releases_api_url).json())
        tag_key = 'name'
    else:
        return []  # Unknown API, cannot fetch releases!

    return [release[tag_key] for release in releases if tag_key in release]


def get_assets_from_release(release_url: str, release: dict) -> dict:

    """
    Parse the assets list out of a given release.
    Return Type: dict
    """

    if GITHUB_API in release_url:
        return release.get('assets', {})
    elif is_gitlab_instance(release_url):
        return release.get('assets', {}).get('links', {})
    else:
        return {}


def get_download_url_from_asset(release_url: str, asset: dict, release_format: str, asset_condition: Callable | None = None) -> str:

    """
    Fetch the download link from a release asset matching a given release format and optional condition lambda.
    Return Type: str
    """

    # Checks are identical for now but may be different for other APIs
    valid_asset: str = ''
    if GITHUB_API in release_url and asset.get('name', '').endswith(release_format):
        valid_asset = asset['browser_download_url']
    elif is_gitlab_instance(release_url) and asset.get('name', '').endswith(release_format):
        valid_asset = asset['url']
    else:
        return ''

    if asset_condition is None or asset_condition(asset):
        return valid_asset

    return ''


# TODO in future if this is re-used for other ctmods other than DXVK and dxvk-async, try to parse more data i.e. checksum
def fetch_project_release_data(release_url: str, release_format: str, rs: requests.Session, tag: str = '', asset_condition: Callable | None = None) -> dict:

    """
    Fetch information about a given release based on its tag, with an optional condition lambda.
    Return Type: dict
    Content(s):
        'version', 'date', 'download', 'size' (if available)
    """

    date_key: str = ''
    api_tag = tag if tag else 'latest'

    url: str = f'{release_url}/'
    if GITHUB_API in release_url:
        url += f'tags/{api_tag}'
        date_key = 'published_at'
    elif is_gitlab_instance(release_url):
        url += api_tag
        date_key = 'released_at'
    else:
        return {}  # Unknown API, cannot fetch data!

    release: dict = rs.get(url).json()
    values: dict = { 'version': release['tag_name'], 'date': release[date_key].split('T')[0] }

    for asset in get_assets_from_release(release_url, release):
        if asset_url := get_download_url_from_asset(release_url, asset, release_format, asset_condition=asset_condition):
            values['download'] = asset_url
            values['size'] = asset.get('size', None)

            break

    return values


def build_headers_with_authorization(request_headers: dict[str, Any], authorization_tokens: dict[str, str], token_type: str) -> dict[str, Any]:

    """
    Generate an updated `request_headers` dict with the `Authorization` header containing the key for GitHub or GitLab, based on `token_type`
    and removing any existing Authorization.

    Return Type: dict[str, Any]
    """

    updated_headers: dict[str, Any] = request_headers.copy()

    updated_headers['Authorization'] = ''  # Reset old authentication
    token: str = authorization_tokens.get(token_type, '')
    if not token:        
        return updated_headers

    if token_type == 'github':
        updated_headers['Authorization'] = f'token {token}'
    elif token_type == 'gitlab':
        updated_headers['Authorization'] = f'Bearer {token}'

    return updated_headers

def compat_tool_available(compat_tool: str, ctobjs: list[dict]) -> bool:
    """ Return whether a compat tool is available for a given launcher """

    return compat_tool in [ctobj['name'] for ctobj in ctobjs]


def get_dict_key_from_value(d: dict[Any, Any], searchval: Any) -> Any:

    """
    Fetch a given dictionary key from a given value.
    Returns the given value if found, otherwise None.

    Return Type: Any
    """

    for key, value in d.items():
        if value == searchval:
            return key
    else:
        return None


def get_combobox_index_by_value(combobox: QComboBox, value: str) -> int:
    """
    Get the index in a combobox where a text value is located.
    Returns an integer >= 0 if found, otherwise -1.

    Return Type: int
    """

    if not value:
        return -1

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


def get_launcher_from_installdir(install_dir: str) -> Launcher:

    """
    Return the launcher type based on the install path given.
    Return Type: Launcher (Enum)
    """

    if any(steam_path in install_dir.lower() for steam_path in ['steam/compatibilitytools.d', 'steam/root/compatibilitytools.d']):
        return Launcher.STEAM
    elif 'lutris/runners' in install_dir.lower():
        return Launcher.LUTRIS
    elif 'heroic/tools' in install_dir.lower():
        return Launcher.HEROIC
    elif 'bottles/runners' in install_dir.lower():
        return Launcher.BOTTLES
    elif 'winezgui/runners' in install_dir.lower():
        return Launcher.WINEZGUI
    else:
        return Launcher.UNKNOWN


def create_missing_dependencies_message(ct_name: str, dependencies: list[str]) -> tuple[str, bool]:

    """
    Generate a string message noting which dependencies are missing for a ctmod_name, with tr_context to translate relevant strings.
    Return the string message and a boolean to note whether the dependencies were met or not.

    Return Type: tuple[str, bool]
    """

    deps_found = [ host_which(dep) for dep in dependencies ]

    if all(deps_found):
        return '', True

    tr_missing = QCoreApplication.instance().translate('util.py', 'missing')
    tr_found = QCoreApplication.instance().translate('util.py', 'found')
    tr_raw_msg = QCoreApplication.instance().translate('util.py', 'You need following dependencies for {CT_NAME}:\n\n{DEP_ENUM}\n\nWill continue the installation anyway.')

    tr_msg = tr_raw_msg.format(
        CT_NAME=ct_name,
        DEP_ENUM='\n'.join(f'{dep_name}: {tr_missing if not deps_found[i] else tr_found}' for i, dep_name in enumerate(dependencies))
    )

    return tr_msg, False


def get_random_game_name(games: list[SteamApp] | list[LutrisGame] | list[HeroicGame]) -> str:
    """ Return a random game name from list of SteamApp, LutrisGame, or HeroicGame """

    if len(games) <= 0:
        return ''
    
    tooltip_game_name: str = ''
    random_game: SteamApp | LutrisGame | HeroicGame = random.choice(games)
    if type(random_game) is SteamApp:
        tooltip_game_name = random_game.game_name
    elif type(random_game) is LutrisGame:
        tooltip_game_name = random_game.name
    elif type(random_game) is HeroicGame:
        tooltip_game_name = random_game.title
    
    return str(tooltip_game_name)


def detect_platform() -> HardwarePlatform:
    """
    Detects the (hardware) platform the application is running on.
    Possible types are DESKTOP and STEAM_DECK.

    Returns:
        HardwarePlatform: The platform (Enum)
    """

    os_release_content = ""

    # Detect SteamOS: https://github.com/sonic2kk/steamtinkerlaunch/wiki/Steam-Deck#setup
    if IS_FLATPAK:
        cmd = ["flatpak-spawn", "--host", "cat", "/etc/os-release"]
        try:
            os_release_content = subprocess.check_output(cmd).decode("utf-8")
        except Exception as e:
            print(f"ERROR while calling detect_platform(): {e}")
    else:
        if os.path.isfile("/etc/os-release"):
            with open("/etc/os-release") as f:
                os_release_content = f.read()

    if "steamdeck" in os_release_content:
        return HardwarePlatform.STEAM_DECK

    return HardwarePlatform.DESKTOP
