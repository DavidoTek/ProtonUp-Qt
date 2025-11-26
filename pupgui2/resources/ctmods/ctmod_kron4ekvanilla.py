# pupgui2 compatibility tools module
# Kron4ek Wine-Builds Vanilla
# Copyright (C) 2021 DavidoTek, partially based on AUNaseef's protonup

import subprocess

from PySide6.QtCore import QCoreApplication

from pupgui2.constants import IS_FLATPAK
from pupgui2.util import fetch_project_release_data, ghapi_rlcheck

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
    
    def __fetch_github_data(self, tag: str) -> dict:

        """
        Fetch GitHub release information
        Return Type: dict
        Content(s):
            'version', 'date', 'download', 'size'
        """

        is_wow64 = tag.endswith(' (wow64)')
        is_amd64 = tag.endswith(' (amd64)')
        if is_wow64:
            tag = tag.replace(" (wow64)", "")
            asset_condition = lambda asset: 'amd64-wow64' in asset.get('name', '') and 'staging' not in asset.get('name', '')
        elif is_amd64:
            tag = tag.replace(" (amd64)", "")
            asset_condition = lambda asset: 'amd64' in asset.get('name', '') and not any(ignore in asset.get('name', '') for ignore in ['staging', 'wow64'])
        else:
            print(f"ctmod_kron4ekvanilla: Invalid tag '{tag}'. Must contain amd64 or wow64")
            return None

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

    def get_extract_dir(self, install_dir: str) -> str:

        """
        Return the directory to extract Lutris-Wine archive based on the current launcher
        Return Type: str
        """

        # GE-Proton ctmod figures out if it needs to into a different folder
        #
        # kron4ek can use default 'install_dir' always because it is Wine and not Proton,
        # so override to return unmodified 'install_dir'
        return install_dir

    def fetch_releases(self, count: int = 100, page: int = 1) -> list[str]:

        """
        List available releases for both amd64 and amd64-wow64 builds
        Return Type: str[]
        """
        
        url = f'{self.CT_URL}?per_page={count}&page={page}'
        response = self.rs.get(url)
        releases_list = ghapi_rlcheck(response.json())

        versions_to_display = []
        
        for release in releases_list:
            if not 'tag_name' in release:
                continue
                
            tag_name = release.get('tag_name')         

            # Check if there is wow64 build to add
            for asset in release.get('assets', []):
                asset_name = asset.get('name', '')
                if 'amd64-wow64' in asset_name and self.release_format in asset_name and 'staging' not in asset_name:
                    versions_to_display.append(f"{tag_name} (wow64)")
                elif 'amd64' in asset_name and self.release_format in asset_name and 'staging' not in asset_name:
                    versions_to_display.append(f"{tag_name} (amd64)")

        return versions_to_display
