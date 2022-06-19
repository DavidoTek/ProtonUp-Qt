import os
from xdg.BaseDirectory import xdg_config_home
from PySide6.QtCore import QObject, Qt
from PySide6.QtGui import QColor, QPalette

APP_NAME = 'ProtonUp-Qt'
APP_VERSION = '2.6.4'
APP_GHAPI_URL = 'https://api.github.com/repos/Davidotek/ProtonUp-qt/releases'
DAVIDOTEK_KOFI_URL = 'https://ko-fi.com/davidotek'
PROTONUPQT_GITHUB_URL = 'https://github.com/DavidoTek/ProtonUp-Qt'
ABOUT_TEXT = '''\
{APP_NAME} v{APP_VERSION} by DavidoTek: <a href="{PROTONUPQT_GITHUB_URL}">https://github.com/DavidoTek/ProtonUp-Qt</a><br />
Copyright (C) 2021-2022 DavidoTek, licensed under GPLv3
'''.format(APP_NAME=APP_NAME, APP_VERSION=APP_VERSION, PROTONUPQT_GITHUB_URL=PROTONUPQT_GITHUB_URL)
BUILD_INFO = 'built from source'

CONFIG_FILE = os.path.join(xdg_config_home, 'pupgui/config.ini')
TEMP_DIR = '/tmp/pupgui2.a70200/'

# support different Steam root directories
_POSSIBLE_STEAM_ROOTS = ['~/.local/share/Steam', '~/.steam/root', '~/.steam/steam', '~/.steam/debian-installation']
_STEAM_ROOT = _POSSIBLE_STEAM_ROOTS[0]
for steam_root in _POSSIBLE_STEAM_ROOTS:
    ct_dir = os.path.join(os.path.expanduser(steam_root), 'config')
    if os.path.exists(ct_dir):
        _STEAM_ROOT = steam_root
        break

POSSIBLE_INSTALL_LOCATIONS = [
    {'install_dir': _STEAM_ROOT + '/compatibilitytools.d/', 'display_name': 'Steam', 'launcher': 'steam', 'icon': 'steam', 'vdf_dir': _STEAM_ROOT + '/config'},
    {'install_dir': '~/.var/app/com.valvesoftware.Steam/data/Steam/compatibilitytools.d/', 'display_name': 'Steam Flatpak', 'launcher': 'steam', 'icon': 'steam'},
    {'install_dir': '~/.local/share/lutris/runners/wine/', 'display_name': 'Lutris', 'launcher': 'lutris', 'icon': 'lutris', 'config_dir': '~/.config/lutris'},
    {'install_dir': '~/.var/app/net.lutris.Lutris/data/lutris/runners/wine/', 'display_name': 'Lutris Flatpak', 'launcher': 'lutris', 'icon': 'lutris', 'config_dir': '~/.var/app/net.lutris.Lutris/config/lutris'},
    {'install_dir': '~/.config/heroic/tools/wine/', 'display_name': 'Heroic Wine', 'launcher': 'heroicwine', 'icon': 'heroic'},
    {'install_dir': '~/.config/heroic/tools/proton/', 'display_name': 'Heroic Proton', 'launcher': 'heroicproton', 'icon': 'heroic'},
    {'install_dir': '~/.var/app/com.heroicgameslauncher.hgl/config/heroic/tools/wine/', 'display_name': 'Heroic Wine Flatpak', 'launcher': 'heroicwine', 'icon': 'heroic'},
    {'install_dir': '~/.var/app/com.heroicgameslauncher.hgl/config/heroic/tools/proton/', 'display_name': 'Heroic Proton Flatpak', 'launcher': 'heroicproton', 'icon': 'heroic'},
    {'install_dir': '~/.local/share/bottles/runners/', 'display_name': 'Bottles', 'launcher': 'bottles', 'icon': 'com.usebottles.bottles'},
    {'install_dir': '~/.var/app/com.usebottles.bottles/data/bottles/runners/', 'display_name': 'Bottles Flatpak', 'launcher': 'bottles', 'icon': 'com.usebottles.bottles'}
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

STEAM_API_GETAPPLIST_URL = 'https://api.steampowered.com/ISteamApps/GetAppList/v2/'
STEAM_APP_PAGE_URL = 'https://store.steampowered.com/app/'
AWACY_GAME_LIST_URL = 'https://raw.githubusercontent.com/Starz0r/AreWeAntiCheatYet/master/games.json'
LOCAL_AWACY_GAME_LIST = os.path.join(TEMP_DIR, 'awacy_games.json')
