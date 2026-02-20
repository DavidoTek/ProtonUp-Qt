# pupgui2 compatibility tools module
# Proton-GE
# Copyright (C) 2021 DavidoTek, partially based on AUNaseef's protonup

import os
import requests
import hashlib

from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import QObject, QCoreApplication, Signal, Property

from pupgui2.datastructures import Launcher
from pupgui2.util import fetch_project_release_data, fetch_project_releases
from pupgui2.util import get_launcher_from_installdir, extract_tar
from pupgui2.util import build_headers_with_authorization
from pupgui2.networkutil import download_file


CT_NAME = 'GE-Proton'
CT_LAUNCHERS = ['steam', 'lutris', 'heroicproton', 'bottles']
CT_DESCRIPTION = {'en': QCoreApplication.instance().translate('ctmod_00protonge', '''Steam compatibility tool for running Windows games with improvements over Valve's default Proton.<br/><br/><b>Use this when you don't know what to choose.</b>''')}


class CtInstaller(QObject):

    BUFFER_SIZE = 65536
    CT_URL = 'https://api.github.com/repos/GloriousEggroll/proton-ge-custom/releases'
    CT_INFO_URL = 'https://github.com/GloriousEggroll/proton-ge-custom/releases/tag/'

    p_download_progress_percent = 0
    download_progress_percent = Signal(int)
    message_box_message = Signal(str, str, QMessageBox.Icon)

    def __init__(self, main_window = None):
        super(CtInstaller, self).__init__()
        self.p_download_canceled = False

        self.release_format = 'tar.gz'

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

    def __download(self, url: str, destination: str, known_size: int = 0) -> bool:
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
                self.tr(
                    "Failed to download tool '{CT_NAME}'!\n\nReason: {EXCEPTION}".format(CT_NAME=CT_NAME, EXCEPTION=e)),
                QMessageBox.Icon.Warning
            )

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

        return fetch_project_release_data(self.CT_URL, self.release_format, self.rs, tag=tag, checksum_suffix='.sha512sum')

    def __get_data(self, version: str, install_dir: str) -> tuple[dict | None, str | None]:

        """
        Get needed download data and path to extract directory.
        Return Type: tuple[dict | None, str | None]
        """

        data = self.__fetch_github_data(version)
        if not data or 'download' not in data:
            return (None, None)

        protondir = os.path.join(install_dir, data['version'])

        return (data, protondir)

    def is_system_compatible(self) -> bool:
        """
        Are the system requirements met?
        Return Type: bool
        """
        return True

    def fetch_releases(self, count: int = 100, page: int = 1) -> list[str]:
        """
        List available releases
        Return Type: str[]
        """

        return fetch_project_releases(self.CT_URL, self.rs, count=count, page=page)

    def get_tool(self, version, install_dir, temp_dir):
        """
        Download and install the compatibility tool
        Return Type: bool
        """

        install_dir = self.get_extract_dir(install_dir)

        data, protondir = self.__get_data(version, install_dir)
        if not data:
            return False

        # Note: protondir is only used for checksums
        if not protondir or  not os.path.exists(protondir):
            protondir = os.path.join(install_dir, 'Proton-' + data['version'])  # Check if we have an older Proton-GE folder name

        checksum_dir = f'{protondir}/sha512sum'
        source_checksum = self.rs.get(data['checksum']).text if 'checksum' in data else None
        local_checksum = open(checksum_dir).read() if os.path.exists(checksum_dir) else None

        if os.path.exists(protondir):
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

        if not extract_tar(proton_tar, install_dir, mode=self.release_format.split('.')[-1]):
            return False

        if os.path.exists(checksum_dir):
            open(checksum_dir, 'w').write(download_checksum)

        self.__set_download_progress_percent(100)

        return True

    def get_extract_dir(self, install_dir: str) -> str:

        """
        Return the directory to extract GE-Proton archive based on the current launcher
        Return Type: str
        """
        return install_dir  # Default to install_dir

    def get_info_url(self, version: str) -> str:
        """
        Get link with info about version (eg. GitHub release page)
        Return Type: str
        """
        return self.CT_INFO_URL + version
