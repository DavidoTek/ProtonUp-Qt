# pupgui2 compatibility tools module
# Roberta
# Copyright (C) 2021 DavidoTek, partially based on AUNaseef's protonup

import os
import requests

from PySide6.QtCore import QObject, QCoreApplication, Signal, Property
from PySide6.QtWidgets import QMessageBox

from pupgui2.util import ghapi_rlcheck, host_which, extract_tar, write_tool_version
from pupgui2.util import build_headers_with_authorization, fetch_project_release_data, fetch_project_releases


CT_NAME = 'Roberta'
CT_LAUNCHERS = ['steam']
CT_DESCRIPTION = {'en': QCoreApplication.instance().translate('ctmod_roberta', '''Steam Play compatibility tool to run adventure games using native Linux ScummVM.''')}


class CtInstaller(QObject):

    BUFFER_SIZE = 4096
    CT_URL = 'https://api.github.com/repos/dreamer/roberta/releases'
    CT_INFO_URL = 'https://github.com/dreamer/roberta/releases/tag/'

    p_download_progress_percent = 0
    download_progress_percent = Signal(int)
    message_box_message = Signal((str, str, QMessageBox.Icon))

    def __init__(self, main_window = None):
        super(CtInstaller, self).__init__()
        self.p_download_canceled = False
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
            'version', 'date', 'download', 'size'
        """

        return fetch_project_release_data(self.CT_URL, self.release_format, self.rs, tag=tag)

    def is_system_compatible(self):
        """
        Are the system requirements met?
        Return Type: bool
        """
        tr_missing = QCoreApplication.instance().translate('ctmod_roberta', 'missing')
        tr_found = QCoreApplication.instance().translate('ctmod_roberta', 'found')
        msg_tr_title = QCoreApplication.instance().translate('ctmod_roberta', 'Missing dependencies!')

        if host_which('scummvm') and host_which('inotifywait'):
            return True
        msg = QCoreApplication.instance().translate('ctmod_roberta', 'You need scummvm and inotify-tools for Roberta.') + '\n\n'
        msg += 'scummvm: ' + str(tr_missing if host_which('scummvm') is None else tr_found) + '\n'
        msg += 'inotify-tools: ' + str(tr_missing if host_which('inotifywait') is None else tr_found)
        msg += '\n\n' + QCoreApplication.instance().translate('ctmod_roberta', 'Will continue installing Roberta anyway.')

        self.message_box_message.emit(msg_tr_title, msg, QMessageBox.Warning)
        return True  # install Roberta anyway

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


        roberta_tar = os.path.join(temp_dir, data['download'].split('/')[-1])
        if not self.__download(url=data['download'], destination=roberta_tar):
            return False

        if not extract_tar(roberta_tar, install_dir, mode='xz'):
            return False

        roberta_dir = os.path.join(install_dir, 'roberta')
        write_tool_version(roberta_dir, version)

        self.__set_download_progress_percent(100)

        return True

    def get_info_url(self, version):
        """
        Get link with info about version (eg. GitHub release page)
        Return Type: str
        """
        return self.CT_INFO_URL + version
