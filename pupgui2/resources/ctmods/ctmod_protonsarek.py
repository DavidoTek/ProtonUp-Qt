# pupgui2 compatibility tools module
# pythonlover02's Proton-Sarek
# Copyright (C) 2025 DavidoTek, partially based on AUNaseef's protonup

from typing import Callable


from PySide6.QtCore import QCoreApplication

from pupgui2.util import fetch_project_release_data, fetch_project_releases

from pupgui2.resources.ctmods.ctmod_00protonge import CtInstaller as GEProtonInstaller


CT_NAME = 'Proton-Sarek'
CT_LAUNCHERS = ['steam', 'lutris', 'heroicproton', 'bottles', 'advmode']
CT_DESCRIPTION = {'en': QCoreApplication.instance().translate('ctmod_protonsarek', '''A custom Proton build with <a href="https://github.com/pythonlover02/DXVK-Sarek">DXVK-Sarek</a> for users with GPUs that support Vulkan 1.1+ but not Vulkan 1.3, or for those with non-Vulkan support who want a plug-and-play option featuring personal patches.''')}


class CtInstaller(GEProtonInstaller):

    BUFFER_SIZE = 65536
    CT_URL = 'https://api.github.com/repos/pythonlover02/Proton-Sarek/releases'
    CT_INFO_URL = 'https://github.com/pythonlover02/Proton-Sarek/releases/tag/'

    def __init__(self, main_window = None) -> None:

        super().__init__(main_window)

        self.release_format: str = 'tar.gz'
        self.async_suffix = '-async'

    def fetch_releases(self, count: int = 100, page: int = 1) -> list[str]:

        """
        List available releases
        Return Type: str[]
        """

        include_extra_asset: Callable[..., list[str]] = lambda release: [str(release.get('tag_name', '')) + self.async_suffix for asset in release.get('assets', {}) if self.async_suffix in asset.get('name', '')]
        return fetch_project_releases(self.CT_URL, self.rs, count=count, page=page, include_extra_asset=include_extra_asset)

    def __fetch_github_data(self, tag: str) -> dict:

        """
        Fetch GitHub release information
        Return Type: dict
        Content(s):
            'version', 'date', 'download', 'size'
        """

        # Exclude async builds by default -- Maybe 'get_download_url_from_asset' needs to be stricter?
        asset_condition = lambda asset: self.async_suffix in asset['name'] if self.async_suffix in tag else self.async_suffix not in asset['name']
        return fetch_project_release_data(self.CT_URL, self.release_format, self.rs, tag=tag.replace(self.async_suffix, ''), asset_condition=asset_condition)

    def get_info_url(self, version: str) -> str:

        """
        Get link with info about version (eg. GitHub release page)
        Return Type: str
        """

        return super().get_info_url(version.replace(self.async_suffix, ''))
