# pupgui2 compatibility tools module
# Kron4ek Wine-Builds Vanilla
# Copyright (C) 2021 DavidoTek, partially based on AUNaseef's protonup

import subprocess

from PySide6.QtCore import QCoreApplication

from pupgui2.constants import IS_FLATPAK
from pupgui2.util import fetch_project_release_data, fetch_project_releases

from pupgui2.resources.ctmods.ctmod_00protonge import CtInstaller as GEProtonInstaller


CT_NAME = 'Kron4ek Wine-Builds Vanilla'
CT_LAUNCHERS = ['lutris', 'winezgui']
CT_DESCRIPTION = {'en': QCoreApplication.instance().translate('ctmod_kron4ekvanilla', '''Compatibility tool "Wine" to run Windows games on Linux. Official version from the WineHQ sources, compiled by Kron4ek.''')}


class CtInstaller(GEProtonInstaller):

    BUFFER_SIZE = 65536
    CT_URL = 'https://api.github.com/repos/Kron4ek/Wine-Builds/releases'
    CT_INFO_URL = 'https://github.com/Kron4ek/Wine-Builds/releases/tag/'

    def __init__(self, main_window = None) -> None:

        super().__init__(main_window)

        self.release_format = 'tar.xz'
    
    def __fetch_github_data(self, tag):

        """
        Fetch GitHub release information
        Return Type: dict
        Content(s):
            'version', 'date', 'download', 'size'
        """

        asset_condition = lambda asset: 'amd64' in asset.get('name', '') and 'staging' not in asset.get('name', '')
        return fetch_project_release_data(self.CT_URL, self.release_format, self.rs, tag=tag, asset_condition=asset_condition)

    def is_system_compatible(self) -> bool:

        """
        Are the system requirements met?
        Return Type: bool
        """

        proc_prefix = ['flatpak-spawn', '--host'] if IS_FLATPAK else []
        ldd = subprocess.run(proc_prefix + ['ldd', '--version'], capture_output=True)
        ldd_out = ldd.stdout.split(b'\n')[0].split(b' ')
        ldd_ver = ldd_out[len(ldd_out) - 1]
        ldd_maj = int(ldd_ver.split(b'.')[0])
        ldd_min = int(ldd_ver.split(b'.')[1])
        return False if ldd_maj < 2 else ldd_min >= 27 or ldd_maj != 2

    def fetch_releases(self, count: int = 100, page: int = 1) -> list[str]:
 
        """
        List available releases
        Return Type: str[]
        """

        return fetch_project_releases(self.CT_URL, self.rs, count=count, page=page)
