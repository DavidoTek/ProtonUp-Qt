import os

APP_NAME = 'ProtonUp-Qt'
APP_VERSION = '1.5.0'
PROTONUP_VERSION = '0.1.4'  # same as in requirements.txt
ABOUT_TEXT = '''\
GUI for installing/updating Proton-GE for Steam and Wine-GE for Lutris.

{APP_NAME} v{APP_VERSION} by DavidoTek: https://github.com/DavidoTek/ProtonUp-Qt
Based on/using ProtonUp v{PROTONUP_VERSION}: https://github.com/AUNaseef/protonup

Copyright (C) 2021 DavidoTek, licensed under GPLv3
'''.format(APP_NAME=APP_NAME, APP_VERSION=APP_VERSION, PROTONUP_VERSION=PROTONUP_VERSION)

CONFIG_FILE = os.path.expanduser('~/.config/pupgui/config.ini')

POSSIBLE_INSTALL_LOCATIONS = [
    {'install_dir': '~/.steam/root/compatibilitytools.d/', 'display_name': 'Steam', 'launcher': 'steam'},
    {'install_dir': '~/.var/app/com.valvesoftware.Steam/data/Steam/compatibilitytools.d/', 'display_name': 'Steam (Flatpak)', 'launcher': 'steam'},
    {'install_dir': '~/.local/share/lutris/runners/wine/', 'display_name': 'Lutris', 'launcher': 'lutris'}
]
