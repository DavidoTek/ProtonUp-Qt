import os
from xdg.BaseDirectory import xdg_config_home

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette


APP_NAME = 'ProtonUp-Qt'
APP_VERSION = '2.8.2'
APP_ID = 'net.davidotek.pupgui2'
APP_ICON_FILE = os.path.join(xdg_config_home, 'pupgui/appicon256.png')
APP_GHAPI_URL = 'https://api.github.com/repos/Davidotek/ProtonUp-qt/releases'
DAVIDOTEK_KOFI_URL = 'https://ko-fi.com/davidotek'
PROTONUPQT_GITHUB_URL = 'https://github.com/DavidoTek/ProtonUp-Qt'
ABOUT_TEXT = '''\
{APP_NAME} v{APP_VERSION} by DavidoTek: <a href="{PROTONUPQT_GITHUB_URL}">https://github.com/DavidoTek/ProtonUp-Qt</a><br />
Copyright (C) 2021-2023 DavidoTek, licensed under GPLv3
'''.format(APP_NAME=APP_NAME, APP_VERSION=APP_VERSION, PROTONUPQT_GITHUB_URL=PROTONUPQT_GITHUB_URL)
BUILD_INFO = 'built from source'

CONFIG_FILE = os.path.join(xdg_config_home, 'pupgui/config.ini')
TEMP_DIR = os.path.join(os.getenv('XDG_CACHE_HOME'), 'tmp', 'pupgui2.a70200/') if os.path.exists(os.getenv('XDG_CACHE_HOME', '')) else '/tmp/pupgui2.a70200/'
HOME_DIR = os.path.expanduser('~')

# support different Steam root directories
# valid install dir should have config.vdf and libraryfolders.vdf, to ensure it is not an unused folder with correct directory structure
_POSSIBLE_STEAM_ROOTS = ['~/.local/share/Steam', '~/.steam/root', '~/.steam/steam', '~/.steam/debian-installation']
_STEAM_ROOT = _POSSIBLE_STEAM_ROOTS[0]
for steam_root in _POSSIBLE_STEAM_ROOTS:
    ct_dir = os.path.join(os.path.expanduser(steam_root), 'config')
    config_vdf = os.path.join(ct_dir, 'config.vdf')
    libraryfolders_vdf = os.path.join(ct_dir, 'libraryfolders.vdf')
    if os.path.exists(config_vdf) and os.path.exists(libraryfolders_vdf):
        _STEAM_ROOT = steam_root
        break

POSSIBLE_INSTALL_LOCATIONS = [
    {'install_dir': f'{_STEAM_ROOT}/compatibilitytools.d/', 'display_name': 'Steam', 'launcher': 'steam', 'type': 'native', 'icon': 'steam', 'vdf_dir': f'{_STEAM_ROOT}/config'},
    {'install_dir': '~/.var/app/com.valvesoftware.Steam/data/Steam/compatibilitytools.d/', 'display_name': 'Steam Flatpak', 'launcher': 'steam', 'type': 'flatpak', 'icon': 'steam', 'vdf_dir': '~/.var/app/com.valvesoftware.Steam/.local/share/Steam/config'},
    {'install_dir': '~/snap/steam/common/.steam/root/compatibilitytools.d/', 'display_name': 'Steam Snap', 'launcher': 'steam', 'type': 'snap', 'icon': 'steam', 'vdf_dir': '~/snap/steam/common/.steam/root/config'},
    {'install_dir': '~/.local/share/lutris/runners/wine/', 'display_name': 'Lutris', 'launcher': 'lutris', 'type': 'native', 'icon': 'lutris', 'config_dir': '~/.config/lutris'},
    {'install_dir': '~/.var/app/net.lutris.Lutris/data/lutris/runners/wine/', 'display_name': 'Lutris Flatpak', 'launcher': 'lutris', 'type': 'flatpak', 'icon': 'lutris', 'config_dir': '~/.var/app/net.lutris.Lutris/config/lutris'},
    {'install_dir': '~/.config/heroic/tools/wine/', 'display_name': 'Heroic Wine', 'launcher': 'heroicwine', 'type': 'native', 'icon': 'heroic'},
    {'install_dir': '~/.config/heroic/tools/proton/', 'display_name': 'Heroic Proton', 'launcher': 'heroicproton', 'type': 'native', 'icon': 'heroic'},
    {'install_dir': '~/.var/app/com.heroicgameslauncher.hgl/config/heroic/tools/wine/', 'display_name': 'Heroic Wine Flatpak', 'launcher': 'heroicwine', 'type': 'flatpak', 'icon': 'heroic'},
    {'install_dir': '~/.var/app/com.heroicgameslauncher.hgl/config/heroic/tools/proton/', 'display_name': 'Heroic Proton Flatpak', 'launcher': 'heroicproton', 'type': 'flatpak', 'icon': 'heroic'},
    {'install_dir': '~/.local/share/bottles/runners/', 'display_name': 'Bottles', 'launcher': 'bottles', 'type': 'native', 'icon': 'com.usebottles.bottles'},
    {'install_dir': '~/.var/app/com.usebottles.bottles/data/bottles/runners/', 'display_name': 'Bottles Flatpak', 'launcher': 'bottles', 'type': 'flatpak', 'icon': 'com.usebottles.bottles'}
]

def PALETTE_DARK():
    """ returns dark color palette """
    palette_dark = QPalette()
    palette_dark.setColor(QPalette.Window, QColor(30, 30, 30))
    palette_dark.setColor(QPalette.WindowText, Qt.white)
    palette_dark.setColor(QPalette.Base, QColor(12, 12, 12))
    palette_dark.setColor(QPalette.AlternateBase, QColor(30, 30, 30))
    palette_dark.setColor(QPalette.ToolTipBase, Qt.white)
    palette_dark.setColor(QPalette.ToolTipText, Qt.white)
    palette_dark.setColor(QPalette.Text, Qt.white)
    palette_dark.setColor(QPalette.Button, QColor(30, 30, 30))
    palette_dark.setColor(QPalette.ButtonText, Qt.white)
    palette_dark.setColor(QPalette.BrightText, Qt.red)
    palette_dark.setColor(QPalette.Link, QColor(40, 120, 200))
    palette_dark.setColor(QPalette.Highlight, QColor(40, 120, 200))
    palette_dark.setColor(QPalette.HighlightedText, Qt.black)
    return palette_dark

PROTONDB_COLORS = {'platinum': '#b4c7dc', 'gold': '#cfb53b', 'silver': '#a6a6a6', 'bronze': '#cd7f32', 'borked': '#ff0000', 'pending': '#748472' }

STEAM_API_GETAPPLIST_URL = 'https://api.steampowered.com/ISteamApps/GetAppList/v2/'
STEAM_APP_PAGE_URL = 'https://store.steampowered.com/app/'
AWACY_GAME_LIST_URL = 'https://raw.githubusercontent.com/Starz0r/AreWeAntiCheatYet/master/games.json'
AWACY_WEB_URL = 'https://areweanticheatyet.com/?search={GAMENAME}&sortOrder=&sortBy='
LOCAL_AWACY_GAME_LIST = os.path.join(TEMP_DIR, 'awacy_games.json')
PROTONDB_API_URL = 'https://www.protondb.com/api/v1/reports/summaries/{game_id}.json'
PROTONDB_APP_PAGE_URL = 'https://protondb.com/app/'

STEAM_BOXTRON_FLATPAK_APPSTREAM = 'appstream://com.valvesoftware.Steam.CompatibilityTool.Boxtron'
STEAM_PROTONGE_FLATPAK_APPSTREAM = 'appstream://com.valvesoftware.Steam.CompatibilityTool.Proton-GE'
STEAM_STL_FLATPAK_APPSTREAM = 'appstream://com.valvesoftware.Steam.Utility.steamtinkerlaunch'

STEAM_STL_INSTALL_PATH = os.path.join(HOME_DIR, 'stl')
STEAM_STL_CONFIG_PATH = os.path.join(HOME_DIR, '.config', 'steamtinkerlaunch')
STEAM_STL_CACHE_PATH = os.path.join(HOME_DIR, '.cache', 'steamtinkerlaunch')
STEAM_STL_DATA_PATH = os.path.join(HOME_DIR, '.local', 'share', 'steamtinkerlaunch')
STEAM_STL_SHELL_FILES = [ '.bashrc', '.zshrc', '.kshrc' ]
STEAM_STL_FISH_VARIABLES = os.path.join(HOME_DIR, '.config/fish/fish_variables')

LUTRIS_WEB_URL = 'https://lutris.net/games/'
EPIC_STORE_URL = 'https://store.epicgames.com/p/'