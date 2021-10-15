# pupgui_winege.py
# partly based on protonup - https://github.com/AUNaseef/protonup
# install/update tool for Wine-GE for Lutris, api not compatible with protonup!

import os
import shutil
from configparser import ConfigParser
import tarfile
import requests
import hashlib

WINEGE_URL = "https://api.github.com/repos/GloriousEggroll/wine-ge-custom/releases"
TEMP_DIR = '/tmp/protonupqt/'
BUFFER_SIZE = 65536  # Work with 64 kb chunks


def download(url, destination):
    """Download files"""
    try:
        file = requests.get(url, stream=True)
    except OSError:
        return False  # Network error
    
    destination = os.path.expanduser(destination)
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    with open(destination, 'wb') as dest:
        for chunk in file.iter_content(chunk_size=BUFFER_SIZE):
            if chunk:
                dest.write(chunk)
                dest.flush()
    return True


def sha512sum(filename):
    """
    Get SHA512 checksum of a file
    Return Type: str
    """
    sha512sum = hashlib.sha512()
    with open(filename, 'rb') as file:
        while True:
            data = file.read(BUFFER_SIZE)
            if not data:
                break
            sha512sum.update(data)
    return sha512sum.hexdigest()


def fetch_data(tag):
    """
    Fetch WineGE release information from github
    Return Type: dict
    Content(s):
        'version', date', 'download', 'size', 'checksum'
    """
    url = WINEGE_URL + (f'/tags/{tag}' if tag else '/latest')
    data = requests.get(url).json()
    if 'tag_name' not in data:
        return None  # invalid tag

    values = {'version': data['tag_name'], 'date': data['published_at'].split('T')[0]}
    for asset in data['assets']:
        if asset['name'].endswith('sha512sum'):
            values['checksum'] = asset['browser_download_url']
        elif asset['name'].endswith('tar.xz'):
            values['download'] = asset['browser_download_url']
            values['size'] = asset['size']
    return values


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
    data = fetch_data(tag=version)

    if not data or 'download' not in data:
        return False

    protondir = install_dir + 'wine-lutris-ge-' + data['version'] + '-x86_64'
    checksum_dir = protondir + '/sha512sum'
    source_checksum = requests.get(data['checksum']).text if 'checksum' in data else None
    local_checksum = open(checksum_dir).read() if os.path.exists(checksum_dir) else None

    # Check if it already exist
    if os.path.exists(protondir):
        if local_checksum and source_checksum:
            if local_checksum in source_checksum:
                return
        else:
            return

    # Prepare Destination
    destination = TEMP_DIR
    if not destination.endswith('/'):
        destination += '/'
    destination += data['download'].split('/')[-1]
    destination = os.path.expanduser(destination)

    # Download
    if not download(url=data['download'], destination=destination):
        return

    download_checksum = sha512sum(destination)
    if source_checksum and (download_checksum not in source_checksum):
        shutil.rmtree(TEMP_DIR, ignore_errors=True)
        return

    # Installation
    if os.path.exists(protondir):
        shutil.rmtree(protondir)
    tarfile.open(destination, "r:xz").extractall(install_dir)
    open(checksum_dir, 'w').write(download_checksum)

    # Clean up
    shutil.rmtree(TEMP_DIR, ignore_errors=True)
