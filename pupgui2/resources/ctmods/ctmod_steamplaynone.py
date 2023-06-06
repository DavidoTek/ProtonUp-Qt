# pupgui2 compatibility tools module
# Steam-Play-None https://github.com/Scrumplex/Steam-Play-None
# Copyright (C) 2022 DavidoTek, partially based on AUNaseef's protonup

import os
import requests

from PySide6.QtCore import QObject, QCoreApplication, Signal, Property

from pupgui2.util import extract_tar


CT_NAME = 'Steam-Play-None'
CT_LAUNCHERS = ['steam', 'advmode']
CT_DESCRIPTION = {'en': QCoreApplication.instance().translate('ctmod_steamplaynone', '''Run Linux games as is, even if Valve recommends Proton for a game.<br/>Created by Scrumplex.<br/><br/>Useful for Steam Deck.<br/><br/>Note: The internal name has been changed from <b>none</b> to <b>Steam-Play-None</b>!''')}


class CtInstaller(QObject):

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
        destination = os.path.expanduser(destination)

        try:
            file = self.rs.get(url)
        except OSError:
            return False

        self.__set_download_progress_percent(1) # 1 download started

        os.makedirs(os.path.dirname(destination), exist_ok=True)
        with open(destination, 'wb') as dest:
            self.__set_download_progress_percent(50)
            dest.write(file.content)
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
        steam_play_none_tar = os.path.join(temp_dir, 'main.tar.gz')
        dl_url = self.CT_URL

        if not self.__download(url=dl_url, destination=steam_play_none_tar):
            return False

        if not extract_tar(steam_play_none_tar, install_dir, mode='gz'):
            return False

        # Rename extracted Steam-Play-None-main to Steam-Play-None
        steam_play_none_main = os.path.join(install_dir, 'Steam-Play-None-main')
        steam_play_none_dir = os.path.join(install_dir, 'Steam-Play-None')
        os.rename(steam_play_none_main, steam_play_none_dir)

        self.__set_download_progress_percent(100)

        return True

    def get_info_url(self, version):
        """
        Get link with info about version (eg. GitHub release page)
        Return Type: str
        """
        return self.CT_INFO_URL
