import os

APP_NAME = 'ProtonUp-Qt'
APP_VERSION = '1.4.4'
PROTONUP_VERSION = '0.1.4'  # same as in requirements.txt

CONFIG_FILE = os.path.expanduser('~/.config/pupgui/config.ini')

POSSIBLE_INSTALL_LOCATIONS = [
    {'install_dir': '~/.steam/root/compatibilitytools.d/', 'display_name': 'Steam', 'launcher': 'steam'},
    {'install_dir': '~/.var/app/com.valvesoftware.Steam/data/Steam/compatibilitytools.d/', 'display_name': 'Steam (Flatpak)', 'launcher': 'steam'},
    {'install_dir': '~/.local/share/lutris/runners/wine/', 'display_name': 'Lutris', 'launcher': 'lutris'}
]
