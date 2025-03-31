# pupgui2 compatibility tools module
# DXVK for Lutris: https://github.com/doitsujin/dxvk/
# Copyright (C) 2022 DavidoTek, partially based on AUNaseef's protonup

import os
from PySide6.QtWidgets import QMessageBox
import requests

from PySide6.QtCore import QObject, QCoreApplication, Signal, Property

from pupgui2.networkutil import download_file
from pupgui2.util import extract_tar, extract_zip, get_launcher_from_installdir, fetch_project_releases
from pupgui2.util import fetch_project_release_data, build_headers_with_authorization
from pupgui2.datastructures import Launcher


CT_NAME = 'DXVK'
CT_LAUNCHERS = ['lutris', 'heroicwine', 'heroicproton']
CT_DESCRIPTION = {'en': QCoreApplication.instance().translate('ctmod_z0dxvk', '''Vulkan based implementation of Direct3D 8, 9, 10, and 11 for Linux/Wine.<br/><br/>https://github.com/lutris/docs/blob/master/HowToDXVK.md''')}


class CtInstaller(QObject):

    BUFFER_SIZE: int = 65536
    CT_URL: str = 'https://api.github.com/repos/doitsujin/dxvk/releases'
    CT_INFO_URL: str = 'https://github.com/doitsujin/dxvk/releases/tag/'

    p_download_progress_percent: int = 0
    download_progress_percent: Signal = Signal(int)
    message_box_message: Signal = Signal((str, str, QMessageBox.Icon))

    def __init__(self, main_window = None):
        super(CtInstaller, self).__init__()
        self.p_download_canceled: bool = False
        self.release_format: str = 'tar.gz'

        self.rs: requests.Session = requests.Session()
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

    def __download(self, url: str, destination: str, known_size: int = 0):
        """
        Download files from url to destination
        Return Type: bool
        """

        try:
            return download_file(
                url=url,
                destination=destination,
                progress_callback=self.__set_download_progress_percent,
                download_cancelled=self.download_canceled,
                buffer_size=self.BUFFER_SIZE,
                stream=True,
                known_size=known_size
            )
        except Exception as e:
            print(f"Failed to download tool {CT_NAME} - Reason: {e}")

            self.message_box_message.emit(
                self.tr("Download Error!"),
                self.tr("Failed to download tool '{CT_NAME}'!\n\nReason: {EXCEPTION}".format(CT_NAME=CT_NAME, EXCEPTION=e)),
                QMessageBox.Icon.Warning
            )

    def __fetch_data(self, tag: str = '') -> dict:
        """
        Fetch release information
        Return Type: dict
        Content(s):
            'version', 'date', 'download', 'size'
        """

        asset_condition = lambda asset: 'native' not in [asset.get('name', ''), asset.get('url', '')]  # 'name' for github asset, 'url' for gitlab asset
        return fetch_project_release_data(self.CT_URL, self.release_format, self.rs, tag=tag, asset_condition=asset_condition)

    def is_system_compatible(self):
        """
        Are the system requirements met?
        Return Type: bool
        """
        return True

    def fetch_releases(self, count: int = 100, page: int = 1):
        """
        List available releases
        Return Type: list[str]
        """
        return fetch_project_releases(self.CT_URL, self.rs, count=count, page=page)

    def __get_data(self, version: str, install_dir: str) -> tuple[dict | None, str | None]:

        """
        Get needed download data and path to extract directory.
        Return Type: diple[dict | None, str | None]
        """

        data = self.__fetch_data(version)
        if not data or 'download' not in data:
            return (None, None)

        dxvk_dir = self.get_extract_dir(install_dir)

        return (data, dxvk_dir)

    def __extract(self, archive_path: str, extract_dir: str) -> bool:

        """
        Extract the tool archive at the given path.
        Return Type: bool
        """

        if not archive_path or not extract_dir:
            return False
        
        # DXVK and DXVK Async are 'tar.gz'
        if self.release_format.startswith('tar'):
            tar_type = self.release_format.split('.')[-1]

            return extract_tar(archive_path, extract_dir, mode=tar_type)
        # DXVK Nightly is 'zip'
        elif self.release_format == 'zip':
            return extract_zip(archive_path, extract_dir)

        # If unknown archive format, cannot extract, so default to fail
        return False

    def get_tool(self, version: str, install_dir: str, temp_dir: str) -> bool:
        """
        Download and install the compatibility tool
        Return Type: bool
        """

        data, dxvk_dir = self.__get_data(version, install_dir)
        if not data:
            return False

        # Should be updated to support Heroic, like ctmod_d8vk
        dxvk_archive: str = os.path.join(temp_dir, data['download'].split('/')[-1])
        if not self.__download(url=data['download'], destination=dxvk_archive, known_size=data.get('size', 0)):
            return False

        if not dxvk_dir or not self.__extract(dxvk_archive, dxvk_dir):
            return False

        self.__set_download_progress_percent(100)

        return True

    def get_info_url(self, version: str) -> str:
        """
        Get link with info about version (eg. GitHub release page)
        Return Type: str
        """
        return self.CT_INFO_URL + version

    def get_extract_dir(self, install_dir: str) -> str:
        """
        Return the directory to extract DXVK archive based on the current launcher
        Return Type: str
        """

        launcher = get_launcher_from_installdir(install_dir)
        if launcher == Launcher.LUTRIS:
            return os.path.abspath(os.path.join(install_dir, '../../runtime/dxvk'))
        if launcher == Launcher.HEROIC:
            return os.path.abspath(os.path.join(install_dir, '../dxvk'))
        else:
            return install_dir  # Default to install_dir
