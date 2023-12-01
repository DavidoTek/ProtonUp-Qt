# pupgui2 compatibility tools module
# vkd3d-proton and vkd3d for Lutris: https://github.com/HansKristian-Work/vkd3d-proton/
# Copyright (C) 2022 DavidoTek, partially based on AUNaseef's protonup

import os
import requests

from PySide6.QtCore import QObject, QCoreApplication, Signal, Property

from pupgui2.datastructures import Launcher
from pupgui2.util import extract_tar, extract_tar_zst, get_launcher_from_installdir
from pupgui2.util import build_headers_with_authorization, fetch_project_release_data, fetch_project_releases


CT_NAME = 'vkd3d-proton'
CT_LAUNCHERS = ['lutris', 'heroicwine', 'heroicproton']
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
        self.release_format = 'tar.zst'

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

    def __fetch_github_data(self, tag):
        """
        Fetch GitHub release information
        Return Type: dict
        Content(s):
            'version', 'date', 'download', 'size', 'checksum'
        """

        return fetch_project_release_data(self.CT_URL, self.release_format, self.rs, tag=tag)

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

        return fetch_project_releases(self.CT_URL, self.rs, count=count)

    def get_tool(self, version, install_dir, temp_dir):
        """
        Download and install the compatibility tool
        Return Type: bool
        """
        data = self.__fetch_github_data(version)

        if not data or 'download' not in data:
            return False

        vkd3d_archive = os.path.join(temp_dir, data['download'].split('/')[-1])  # e.g. /tmp/[...]/vkd3d-proton-2.7.tar.zst
        if not self.__download(url=data['download'], destination=vkd3d_archive):
            return False

        vkd3d_dir = self.get_extract_dir(install_dir)

        has_extract_tar_zst = vkd3d_archive.endswith('.tar.zst') and extract_tar_zst(vkd3d_archive, vkd3d_dir)
        has_extract_tar_xz = vkd3d_archive.endswith('.tar.xz') and extract_tar(vkd3d_archive, vkd3d_dir, mode='xz')

        if not has_extract_tar_zst and not has_extract_tar_xz:
            return False

        self.__set_download_progress_percent(100)

        return True

    def get_info_url(self, version):
        """
        Get link with info about version (eg. GitHub release page)
        Return Type: str
        """
        return self.CT_INFO_URL + version

    def get_extract_dir(self, install_dir: str) -> str:
        """
        Return the directory to extract vkd3d archive based on the current launcher
        Return Type: str
        """

        launcher = get_launcher_from_installdir(install_dir)
        if launcher == Launcher.LUTRIS:
            return os.path.abspath(os.path.join(install_dir, '../../runtime/vkd3d'))
        if launcher == Launcher.HEROIC:
            return os.path.abspath(os.path.join(install_dir, '../vkd3d'))
        else:
            return install_dir  # Default to install_dir
