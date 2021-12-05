import os
from xdg.BaseDirectory import xdg_config_home
from PySide6.QtCore import QObject, Qt
from PySide6.QtGui import QColor, QPalette

APP_NAME = 'ProtonUp-Qt'
APP_VERSION = '2.3.2'
APP_GHAPI_URL = 'https://api.github.com/repos/Davidotek/ProtonUp-qt/releases'
ABOUT_TEXT = '''\
GUI for installing/updating Wine/Proton based compatibility tools.

{APP_NAME} v{APP_VERSION} by DavidoTek: https://github.com/DavidoTek/ProtonUp-Qt
Inspired by/partly based on AUNaseef's protonup.

Copyright (C) 2021 DavidoTek, licensed under GPLv3\
'''.format(APP_NAME=APP_NAME, APP_VERSION=APP_VERSION)

CONFIG_FILE = os.path.join(xdg_config_home, 'pupgui/config.ini')
TEMP_DIR = '/tmp/pupgui2.a70200/'

_STEAM_ROOT = '~/.steam/root' if os.path.exists(os.path.expanduser('~/.steam/root')) else '~/.local/share/Steam'
POSSIBLE_INSTALL_LOCATIONS = [
    {'install_dir': _STEAM_ROOT + '/compatibilitytools.d/', 'display_name': 'Steam', 'launcher': 'steam', 'icon': 'steam', 'vdf_dir': _STEAM_ROOT + '/config/config.vdf'},
    {'install_dir': '~/.var/app/com.valvesoftware.Steam/data/Steam/compatibilitytools.d/', 'display_name': 'Steam Flatpak', 'launcher': 'steam', 'icon': 'steam'},
    {'install_dir': '~/.local/share/lutris/runners/wine/', 'display_name': 'Lutris', 'launcher': 'lutris', 'icon': 'lutris'},
    {'install_dir': '~/.config/heroic/tools/wine/', 'display_name': 'Heroic Wine', 'launcher': 'heroicwine', 'icon': 'heroic'},
    {'install_dir': '~/.config/heroic/tools/proton/', 'display_name': 'Heroic Proton', 'launcher': 'heroicproton', 'icon': 'heroic'}
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
LOCAL_STEAM_APPLIST_FILE = os.path.join(xdg_config_home,'pupgui/steam_applist.json')
