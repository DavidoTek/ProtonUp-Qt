# pupgui_winege.py
# partly based on protonup - https://github.com/AUNaseef/protonup
# install/update tool for Wine-GE for Lutris, api not compatible with protonup!

import os
import shutil
from configparser import ConfigParser
import tarfile
import requests

WINEGE_URL = "https://api.github.com/repos/GloriousEggroll/wine-ge-custom/releases"

def fetch_releases(count=100):
    """
    List WineGE releases on Github
    Return Type: str[]
    """
    tags = []
    for release in requests.get(WINEGE_URL + "?per_page=" + str(count)).json():
        tags.append(release['tag_name'])
    return tags

def installed_versions(install_dir):
    """
    List of lutris wine installations
    Return Type: str[]
    """
    versions_found = []

    if os.path.exists(install_dir):
        folders = os.listdir(install_dir)
        # Find names of directories with proton
        for folder in folders:
            if os.path.exists(f'{install_dir}/{folder}/bin'):
                versions_found.append(folder)

    return versions_found

def remove_winege(install_dir, version):
    """Uninstall existing lutris wine installation"""
    target = install_dir + version
    if os.path.exists(target):
        shutil.rmtree(target)
        return True
    return False

def get_winege(install_dir, version):
    """Download and install WineGE"""
    pass