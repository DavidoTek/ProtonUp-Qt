import os, subprocess, shutil
import sys
import platform
import threading, requests, json
import webbrowser
import vdf
from configparser import ConfigParser
import PySide6
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from constants import POSSIBLE_INSTALL_LOCATIONS, CONFIG_FILE, PALETTE_DARK
from constants import STEAM_API_GETAPPLIST_URL, LOCAL_STEAM_APPLIST_FILE


def apply_dark_theme(app):
    """
    Apply custom dark mode to Qt application when not using KDE Plasma
    and a dark GTK theme is selected (name ends with '-dark')
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


def config_theme(theme=None):
    """
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


def create_compatibilitytools_folder():
    """
    Create compatibilitytools folder if launcher is installed but compatibilitytools folder doesn't exist.
    """
    for loc in POSSIBLE_INSTALL_LOCATIONS:
        install_dir = os.path.normpath(os.path.expanduser(loc['install_dir']))
        parent_dir = os.path.abspath(os.path.join(install_dir, os.pardir))

        if os.path.exists(parent_dir) and not os.path.exists(install_dir):
            try:
                os.mkdir(install_dir)
            except Exception as e:
                print('Error trying to create compatibility tools folder ' + str(install_dir) + ': ' + str(e))


def available_install_directories():
    """
    List available install directories
    Return Type: str[]
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


def get_install_location_from_directory_name(install_dir):
    """
    Get install location dict from install directory name
    Return Type: dict
    """
    for loc in POSSIBLE_INSTALL_LOCATIONS:
        if os.path.expanduser(install_dir) == os.path.expanduser(loc['install_dir']):
            return loc
    custom_install_location = config_custom_install_location()
    if custom_install_location.get('install_dir') and os.path.expanduser(install_dir) == os.path.expanduser(custom_install_location.get('install_dir')) and custom_install_location.get('launcher'):
        return custom_install_location
    return {'install_dir': install_dir, 'display_name': 'unknown', 'launcher': ''}


# modified install_directory function from protonup 0.1.4
def install_directory(target=None):
    """
    Custom install directory
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


def config_custom_install_location(install_dir=None, launcher=''):
    """
    Return Type: dict
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


def list_installed_ctools(install_dir):
        """
        List installed compatibility tool versions
        Return Type: str[]
        """
        versions_found = []

        if os.path.exists(install_dir):
            folders = os.listdir(install_dir)
            for folder in folders:
                ver_file = os.path.join(install_dir, folder, 'VERSION.txt')
                if os.path.exists(ver_file):
                    with open(ver_file, 'r') as f:
                        ver = f.read()
                    versions_found.append(folder + ' - ' + ver.strip())
                else:
                    versions_found.append(folder)

        return versions_found


def remove_ctool(ver, install_dir):
    """
    Remove compatibility tool folder
    Return Type: bool
    """
    target = os.path.join(install_dir, ver.split(' - ')[0])
    if os.path.exists(target):
        shutil.rmtree(target)
        return True
    return False


def get_steam_games_using_compat_tool(ver, vdf_dir):
    """
    Get all games using a specified compatibility tool from Steam config.vdf
    'ver' should be the same as the internal name specified in compatibilitytool.vdf (Matches folder name in most cases)
    Return Type: str[]
    """
    tools = []
    
    try:
        vdf_file = os.path.expanduser(vdf_dir)
        d = vdf.load(open(vdf_file))
        c = d.get('InstallConfigStore').get('Software').get('Valve').get('Steam').get('CompatToolMapping')

        for t in c:
            x = c.get(str(t))
            if x is None:
                continue
            if x.get('name') == ver:
                tools.append(t)
    except Exception as e:
        print('Error: Could not get list of Steam games using compat tool "' + str(ver) + '":', e)
        tools = ['-1']  # don't return empty list else compat tool would be listed as unused

    return tools


def get_steam_game_list(vdf_dir):
    """
    Returns a list of Steam games and which compatibility tools they are using.
    (Only includes games which override the default compatibility tool. ToDo: Include all + natives)
    Return Type: dict[]
        Content: 'id', 'compat_tool', 'game_name'
    """
    games = []
    game_ids_str = []
    try:
        vdf_file = os.path.expanduser(vdf_dir)
        d = vdf.load(open(vdf_file))
        c = d.get('InstallConfigStore').get('Software').get('Valve').get('Steam').get('CompatToolMapping')

        for t in c:
            x = c.get(str(t))
            if x is None:
                continue
            games.append({'id': str(t), 'compat_tool': x.get('name')})
            game_ids_str.append(str(t))

        game_names = get_steam_game_names_by_ids(game_ids_str)
        for g in games:
            if g.get('id') == '0':
                g['game_name'] = 'Steam'
            else:
                g['game_name'] = game_names.get(int(g.get('id', -1)), '')
    except Exception as e:
        print('Error: Could not get a list of all Steam games:', e)

    return games


def sort_compatibility_tool_names(unsorted):
    """
    Sort the list of compatibility tools: First sort alphabetically using sorted() then sort by Proton version
    Return Type: str[]
    """
    unsorted = sorted(unsorted)
    ver_dict = {}
    i = 0
    for ver in unsorted:
        i += 1
        if 'Proton-' in ver:
            try:
                ver_string = ver.split('-')[1]
                ver_major = int(ver_string.split('.')[0])
                ver_minor = int(ver_string.split('.')[1])
                ver_dict[ver_major * 100 + ver_minor] = ver
            except:
                ver_dict[i] = ver
        else:
            ver_dict[i] = ver
    
    sorted_vers = []
    for v in sorted(ver_dict):
        sorted_vers.append(ver_dict[v])

    return sorted_vers


def download_steam_app_list_thread(force_download=False):
    """
    Download Steam app list in a separe thread
    """
    if os.path.exists(LOCAL_STEAM_APPLIST_FILE) and not force_download:
        return
    
    if os.path.exists(LOCAL_STEAM_APPLIST_FILE):
        os.remove(LOCAL_STEAM_APPLIST_FILE)

    def _download_steam_app_list():
        for i in range(0, 3): # try to download file, if download failed repeat (up to 3 times)
            if os.path.exists(LOCAL_STEAM_APPLIST_FILE):
                os.remove(LOCAL_STEAM_APPLIST_FILE)
            r = requests.get(STEAM_API_GETAPPLIST_URL)
            with open(LOCAL_STEAM_APPLIST_FILE, 'wb') as f:
                f.write(r.content)
            if os.path.exists(LOCAL_STEAM_APPLIST_FILE) and os.path.getsize(LOCAL_STEAM_APPLIST_FILE) > 5000000:
                break

    t = threading.Thread(target=_download_steam_app_list)
    t.start()


def get_steam_game_names_by_ids(ids_str=[]):
    """
    Get steam game names by ids
    Return Type: dict[]
    """
    ids = []
    for id in ids_str:
        ids.append(int(id))
    names = {}
    try:
        with open(LOCAL_STEAM_APPLIST_FILE) as f:
            data = json.load(f)
            steam_apps = data.get('applist').get('apps')
            for steam_app in steam_apps:
                if steam_app.get('appid') in ids:
                    names[steam_app.get('appid')] = steam_app.get('name')
                    ids.remove(steam_app.get('appid'))
                if len(ids) == 0:
                    break
    except:
        pass
    return names


def steam_update_ctool(game_id=0, new_ctool=None, vdf_dir=''):
    """
    Change compatibility tool for 'game_id' to 'new_ctool' in Steam config vdf
    Return Type: bool
    """
    if new_ctool == None or not os.path.exists(vdf_dir):
        return False
    
    try:
        vdf_file = os.path.expanduser(vdf_dir)
        d = vdf.load(open(vdf_file))
        c = d.get('InstallConfigStore').get('Software').get('Valve').get('Steam').get('CompatToolMapping')

        if str(game_id) in c:
            c.get(str(game_id))['name'] = str(new_ctool)
        else:
            return False
        
        vdf.dump(d, open(vdf_file, 'w'), pretty=True)
    except Exception as e:
        print('Error, could not update Steam compatibility tool to', new_ctool, 'for game', game_id, ':', e, ', vdf_dir=', vdf_dir)
        return False
    return True


def open_webbrowser_thread(url):
    try:
        t = threading.Thread(target=webbrowser.open, args=[url])
        t.start()
    except:
        print('Could not open webbrowser url ' + str(url))


def print_system_information():
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
