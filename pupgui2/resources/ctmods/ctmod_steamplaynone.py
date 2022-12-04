# pupgui2 compatibility tools module
# Steam-Play-None https://github.com/Scrumplex/Steam-Play-None
# Copyright (C) 2022 DavidoTek, partially based on AUNaseef's protonup

import os
import shutil
import tarfile
import requests

from PySide6.QtCore import QObject, QCoreApplication, Signal, Property


CT_NAME = 'Steam-Play-None'
CT_LAUNCHERS = ['steam', 'advmode']
CT_DESCRIPTION = {'en': QCoreApplication.instance().translate('ctmod_steamplaynone', '''Run Linux games as is, even if Valve recommends Proton for a game.<br/>Created by Scrumplex.<br/><br/>Useful for Steam Deck.''')}


class CtInstaller(QObject):

    BUFFER_SIZE = 2048
    CT_URL = 'https://github.com/Scrumplex/Steam-Play-None/archive/refs/heads/main.tar.gz'  # no releases
    CT_INFO_URL = 'https://github.com/Scrumplex/Steam-Play-None'

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
        return ['main']

    def get_tool(self, version, install_dir, temp_dir):
        """
        Download and install the compatibility tool
        Return Type: bool
        """
        destination = os.path.join(temp_dir, 'main.tar.gz')
        dl_url = self.CT_URL
        protondir = os.path.join(install_dir, 'Steam-Play-None-main')

        if not self.__download(url=dl_url, destination=destination):
            return False

        if os.path.exists(protondir):
            shutil.rmtree(protondir)
        tarfile.open(destination, "r:gz").extractall(install_dir)

        self.__set_download_progress_percent(100)

        return True

    def get_info_url(self, version):
        """
        Get link with info about version (eg. GitHub release page)
        Return Type: str
        """
        return self.CT_INFO_URL
