# pupgui2 compatibility tools module
# vkd3d-proton for Lutris: https://github.com/HansKristian-Work/vkd3d-proton/
# Copyright (C) 2022 DavidoTek, partially based on AUNaseef's protonup

import os
import shutil
import tarfile
import requests
import zstandard

from PySide6.QtCore import QObject, QCoreApplication, Signal, Property

from pupgui2.util import ghapi_rlcheck


CT_NAME = 'vkd3d-proton'
CT_LAUNCHERS = ['lutris']
CT_DESCRIPTION = {'en': QCoreApplication.instance().translate('ctmod_vkd3d-proton', '''Fork of Wine's VKD3D which aims to implement the full Direct3D 12 API on top of Vulkan (Valve Release).<br/><br/>https://github.com/lutris/docs/blob/master/HowToDXVK.md''')}

class CtInstaller(QObject):

    BUFFER_SIZE = 65536
    CT_URL = 'https://api.github.com/repos/HansKristian-Work/vkd3d-proton/releases'
    CT_INFO_URL = 'https://github.com/HansKristian-Work/vkd3d-proton/releases/tag/'

    p_download_progress_percent = 0
    download_progress_percent = Signal(int)

    def __init__(self, main_window = None):
        super(CtInstaller, self).__init__()
        self.p_download_canceled = False
        self.rs = main_window.rs or requests.Session()

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
            if asset['name'].endswith('tar.zst'):
                values['download'] = asset['browser_download_url']
                values['size'] = asset['size']
        return values

    def is_system_compatible(self):
        """
        Are the system requirements met?
        Return Type: bool
        """
        return True

    def fetch_releases(self, count=100):
        """
        List available releases
        Return Type: str[]
        """
        return [release['tag_name'] for release in ghapi_rlcheck(self.rs.get(f'{self.CT_URL}?per_page={str(count)}').json()) if 'tag_name' in release]

    def get_tool(self, version, install_dir, temp_dir):
        """
        Download and install the compatibility tool
        Return Type: bool
        """
        data = self.__fetch_github_data(version)

        if not data or 'download' not in data:
            return False

        vkd3d_dir = os.path.abspath(os.path.join(install_dir, '../../runtime/vkd3d'))

        temp_download = os.path.join(temp_dir, data['download'].split('/')[-1])  # e.g. /tmp/[...]/vkd3d-proton-2.7.tar.zst
        temp_archive = temp_download.replace('.zst', '')  # e.g. /tmp/[...]/vkd3d-proton-2.7.tar

        if not self.__download(url=data['download'], destination=temp_download):
            return False

        if os.path.exists(f'{vkd3d_dir}vkd3d-proton-{data["version"].lower()}'):
            shutil.rmtree(f'{vkd3d_dir}vkd3d-proton-{data["version"].lower()}')

        # Extract .tar.zst file - Very convoluted, there is an open request to add support for this to Python tarfile: https://bugs.python.org/issue37095
        vkd3d_decomp = zstandard.ZstdDecompressor()

        with open(temp_download, 'rb') as vkd3d_infile, open(temp_archive, 'wb') as vkd3d_outfile:
            vkd3d_decomp.copy_stream(vkd3d_infile, vkd3d_outfile)

        with open(temp_archive, 'rb') as vkd3d_outfile:
            with tarfile.open(fileobj=vkd3d_outfile) as vkd3d_tarfile:
                vkd3d_tarfile.extractall(vkd3d_dir)

        self.__set_download_progress_percent(100)

        return True

    def get_info_url(self, version):
        """
        Get link with info about version (eg. GitHub release page)
        Return Type: str
        """
        return self.CT_INFO_URL + version
