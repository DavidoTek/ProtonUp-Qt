# pupgui2 compatibility tools module
# cyrv6737's NorthstarProton for TitanFall 2
# Copyright (C) 2022 DavidoTek, partially based on AUNaseef's protonup

from PySide6.QtCore import QCoreApplication

from pupgui2.util import fetch_project_release_data

from pupgui2.resources.ctmods.ctmod_00protonge import CtInstaller as GEProtonInstaller


CT_NAME = 'Northstar Proton (Titanfall 2)'
CT_LAUNCHERS = ['steam', 'heroicproton', 'bottles', 'advmode']
CT_DESCRIPTION = {'en': QCoreApplication.instance().translate('ctmod_northstarproton', '''Proton build based on TKG's proton-tkg to run the Northstar client + TitanFall 2. By cyrv6737.<br/><br/><b style="color:orange;">Read the following before proceeding</b>:<br/><a href="https://github.com/R2NorthstarTools/NorthstarProton">https://github.com/R2NorthstarTools/NorthstarProton</a>''')}


class CtInstaller(GEProtonInstaller):

    BUFFER_SIZE = 65536
    CT_URL = 'https://api.github.com/repos/R2NorthstarTools/NorthstarProton/releases'
    CT_INFO_URL = 'https://github.com/R2NorthstarTools/NorthstarProton/releases/tag/'

    def __init__(self, main_window = None) -> None:

        super().__init__(main_window)

        self.release_format: str = 'tar.gz'

    def __fetch_github_data(self, tag: str) -> dict:
        """
        Fetch GitHub release information
        Return Type: dict
        Content(s):
            'version', 'date', 'download', 'size'
        """

        return fetch_project_release_data(self.CT_URL, self.release_format, self.rs, tag=tag)
