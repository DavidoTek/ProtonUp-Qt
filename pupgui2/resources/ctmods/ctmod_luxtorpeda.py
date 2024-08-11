# pupgui2 compatibility tools module
# Luxtorpeda
# Copyright (C) 2021 DavidoTek, partially based on AUNaseef's protonup

import os
import requests

from PySide6.QtCore import QObject, QCoreApplication, Signal, Property
from PySide6.QtWidgets import QMessageBox

from pupgui2.networkutil import download_file
from pupgui2.util import create_msgbox, extract_tar, write_tool_version
from pupgui2.util import build_headers_with_authorization, create_missing_dependencies_message, fetch_project_release_data, fetch_project_releases


CT_NAME = 'Luxtorpeda'
CT_LAUNCHERS = ['steam']
CT_DESCRIPTION = {'en': QCoreApplication.instance().translate('ctmod_luxtorpeda', '''Luxtorpeda provides Linux-native game engines for specific Windows-only games.''')}


class CtInstaller(QObject):

    BUFFER_SIZE = 65536
    CT_URL = 'https://api.github.com/repos/luxtorpeda-dev/luxtorpeda/releases'
    CT_INFO_URL = 'https://github.com/luxtorpeda-dev/luxtorpeda/releases/tag/'

    p_download_progress_percent = 0
    download_progress_percent = Signal(int)
    message_box_message = Signal((str, str, QMessageBox.Icon))

    def __init__(self, main_window = None):
        super(CtInstaller, self).__init__()
        self.p_download_canceled = False

        # Allows override for Boxtron/Roberta
        self.extract_dir_name = 'luxtorpeda'
        self.deps = []
        self.release_format = 'tar.xz'

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

            msgbox_title: str = self.tr("Download Error!")
            msgbox_text: str = self.tr("Failed to download tool '{CT_NAME}'!\n\nReason: {EXCEPTION}".format(CT_NAME=CT_NAME, EXCEPTION=e))
            self.message_box_message.emit(msgbox_title, msgbox_text, QMessageBox.Icon.Warning)

    def __fetch_github_data(self, tag):
        """
        Fetch GitHub release information
        Return Type: dict
        Content(s):
            'version', 'date', 'download', 'size'
        """

        return fetch_project_release_data(self.CT_URL, self.release_format, self.rs, tag=tag)

    def is_system_compatible(self, ct_name: str = CT_NAME) -> bool:
        """
        Are the system requirements met?
        Return Type: bool
        """

        if not self.deps:
            return True  # Skip check if we have no dependencies

        # Emit warning if we generated a missing dependencies message
        msg_tr_title = self.tr('Missing dependencies!')
        msg, success = create_missing_dependencies_message(ct_name, self.deps)
        if not success:
            self.message_box_message.emit(msg_tr_title, msg, QMessageBox.Warning)

        return True  # install Boxtron anyway


    def fetch_releases(self, count=100, page=1):
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
        data = self.__fetch_github_data(version)

        if not data or 'download' not in data:
            return False

        luxtorpeda_tar = os.path.join(temp_dir, data['download'].split('/')[-1])
        if not self.__download(url=data['download'], destination=luxtorpeda_tar, known_size=data.get('size', 0)):
            return False

        luxtorpeda_dir = os.path.join(install_dir, self.extract_dir_name)
        if not extract_tar(luxtorpeda_tar, install_dir, mode='xz'):
            return False
        write_tool_version(luxtorpeda_dir, version)

        self.__set_download_progress_percent(100)

        return True

    def get_info_url(self, version):
        """
        Get link with info about version (eg. GitHub release page)
        Return Type: str
        """
        return self.CT_INFO_URL + version
