# pupgui2 compatibility tools module
# Wine-GE
# Copyright (C) 2021 DavidoTek, partially based on AUNaseef's protonup

import os
import requests
import hashlib

from PySide6.QtCore import QObject, QCoreApplication, Signal, Property

from pupgui2.datastructures import Launcher
from pupgui2.util import ghapi_rlcheck, extract_tar, get_launcher_from_installdir
from pupgui2.util import build_headers_with_authorization


CT_NAME = 'Wine-GE'
CT_LAUNCHERS = ['lutris', 'heroicwine', 'bottles', 'winezgui']
CT_DESCRIPTION = {'en': QCoreApplication.instance().translate('ctmod_00winege', '''Compatibility tool "Wine" to run Windows games on Linux. Based on Valve Proton Experimental's bleeding-edge Wine, built for Lutris.<br/><br/><b>Use this when you don't know what to choose.</b>''')}


class CtInstaller(QObject):

    BUFFER_SIZE = 65536
    CT_URL = 'https://api.github.com/repos/GloriousEggroll/wine-ge-custom/releases'
    CT_INFO_URL = 'https://github.com/GloriousEggroll/wine-ge-custom/releases/tag/'

    p_download_progress_percent = 0
    download_progress_percent = Signal(int)

    def __init__(self, main_window = None):
        super(CtInstaller, self).__init__()
        self.p_download_canceled = False

        self.rs = requests.Session()
        rs_headers = build_headers_with_authorization({}, main_window.web_access_tokens, 'github')
        self.rs.headers.update(rs_headers)

    def get_download_canceled(self):
        return self.p_download_canceled

    def set_download_canceled(self, val):
        self.p_download_canceled = val

    download_canceled = Property(bool, get_download_canceled, set_download_canceled)

    def __set_download_progress_percent(self, value : int):
        if self.p_download_progress_percent == value:
            return
        self.p_download_progress_percent = value
        self.download_progress_percent.emit(value)

    def __download(self, url, destination):
        """
        Download files from url to destination
        Return Type: bool
        """
        try:
            file = self.rs.get(url, stream=True)
        except OSError:
            return False

        self.__set_download_progress_percent(1) # 1 download started
        f_size = int(file.headers.get('content-length'))
        c_count = int(f_size / self.BUFFER_SIZE)
        c_current = 1
        destination = os.path.expanduser(destination)
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        with open(destination, 'wb') as dest:
            for chunk in file.iter_content(chunk_size=self.BUFFER_SIZE):
                if self.download_canceled:
                    self.download_canceled = False
                    self.__set_download_progress_percent(-2) # -2 download canceled
                    return False
                if chunk:
                    dest.write(chunk)
                    dest.flush()
                self.__set_download_progress_percent(int(min(c_current / c_count * 98.0, 98.0))) # 1-98, 100 after extract
                c_current += 1
        self.__set_download_progress_percent(99) # 99 download complete
        return True

    def __sha512sum(self, filename):
        """
        Get SHA512 checksum of a file
        Return Type: str
        """
        sha512sum = hashlib.sha512()
        with open(filename, 'rb') as file:
            while True:
                data = file.read(self.BUFFER_SIZE)
                if not data:
                    break
                sha512sum.update(data)
        return sha512sum.hexdigest()

    def __fetch_github_data(self, tag):
        """
        Fetch GitHub release information
        Return Type: dict
        Content(s):
            'version', 'date', 'download', 'size', 'checksum'
        """
        url = self.CT_URL + (f'/tags/{tag}' if tag else '/latest')
        data = self.rs.get(url).json()
        if 'tag_name' not in data:
            return None

        values = {'version': data['tag_name'], 'date': data['published_at'].split('T')[0]}
        for asset in data['assets']:
            if asset['name'].endswith('sha512sum'):
                values['checksum'] = asset['browser_download_url']
            elif asset['name'].endswith('tar.xz'):
                values['download'] = asset['browser_download_url']
                values['size'] = asset['size']
        return values

    def is_system_compatible(self):
        """
        Are the system requirements met?
        Return Type: bool
        """
        return True

    def fetch_releases(self, count=100, page=1):
        """
        List available releases
        Return Type: str[]
        """
        return [release['tag_name'] for release in ghapi_rlcheck(self.rs.get(f'{self.CT_URL}?per_page={count}&page={page}').json()) if 'tag_name' in release]

    def get_tool(self, version, install_dir, temp_dir):
        """
        Download and install the compatibility tool
        Return Type: bool
        """
        data = self.__fetch_github_data(version)

        if not data or 'download' not in data:
            return False

        ge_extract_basename = f"lutris-{data['version']}-x86_64"
        ge_extract_fullpath = os.path.join(install_dir, ge_extract_basename)

        checksum_dir = os.path.join(ge_extract_fullpath, 'sha512sum')
        source_checksum = self.rs.get(data['checksum']).text if 'checksum' in data else None
        local_checksum = open(checksum_dir).read() if os.path.exists(checksum_dir) else None

        if os.path.exists(ge_extract_fullpath):
            if local_checksum and source_checksum:
                if local_checksum in source_checksum:
                    return False
            else:
                return False

        proton_tar = os.path.join(temp_dir, data['download'].split('/')[-1])
        if not self.__download(url=data['download'], destination=proton_tar):
            return False

        download_checksum = self.__sha512sum(proton_tar)
        if source_checksum and (download_checksum not in source_checksum):
            return False

        if not extract_tar(proton_tar, install_dir, mode='xz'):
            return False

        if os.path.exists(checksum_dir):
            open(checksum_dir, 'w').write(download_checksum)

        # Make sure extracted directory name matches name launcher expects (i.e. Lutris uses a custom name format)
        ge_updated_dirname = os.path.join(install_dir, self.get_launcher_extract_dirname(ge_extract_basename, install_dir))
        os.rename(ge_extract_fullpath, ge_updated_dirname)

        self.__set_download_progress_percent(100)

        return True

    def get_launcher_extract_dirname(self, original_name: str, install_dir: str) -> str:

        """
        Return base extract directory name updated to match naming scheme expected for given launcher.
        Example: 'lutris-GE-Proton8-17-x86_64' -> 'wine-ge-8-17-x86_64'

        Return Type: str
        """

        launcher_name = ''
        launcher = get_launcher_from_installdir(install_dir)
        if launcher == Launcher.LUTRIS:
            # Lutris expects this name format for self-updating, see #294 -- ex: wine-ge-8-17-x86_64
            launcher_name = original_name.lower().replace('lutris', 'wine').replace('proton', '')
        elif launcher == Launcher.HEROIC:
            # This matches Heroic Wine-GE naming convention -- ex: Wine-GE-Proton8-17
            launcher_name = original_name.replace('lutris', 'Wine').rsplit('-', 1)[0]

        return launcher_name or original_name

    def get_info_url(self, version):
        """
        Get link with info about version (eg. GitHub release page)
        Return Type: str
        """
        return self.CT_INFO_URL + version
