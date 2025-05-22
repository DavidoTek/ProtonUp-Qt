# pupgui2 compatibility tools module
# Lutris-Wine
# Copyright (C) 2021 DavidoTek, partially based on AUNaseef's protonup

from PySide6.QtCore import QCoreApplication

from pupgui2.util import fetch_project_release_data, ghapi_rlcheck

from pupgui2.resources.ctmods.ctmod_00protonge import CtInstaller as GEProtonInstaller


CT_NAME = 'Lutris-Wine'
CT_LAUNCHERS = ['lutris', 'bottles', 'winezgui']
CT_DESCRIPTION = {'en': QCoreApplication.instance().translate('ctmod_lutriswine', '''Compatibility tool "Wine" to run Windows games on Linux. Improved by Lutris to offer better compatibility or performance in certain games.''')}


class CtInstaller(GEProtonInstaller):

    BUFFER_SIZE = 65536
    CT_URL = 'https://api.github.com/repos/lutris/wine/releases'
    CT_INFO_URL = 'https://github.com/lutris/wine/releases/tag/'

    def __init__(self, main_window = None):

        super().__init__(main_window)

        self.release_format = 'tar.xz'

    def fetch_releases(self, count: int = 100, page: int = 1):
        """
        List available releases
        Return Type: str[]
        """
        tags = []
        for release in ghapi_rlcheck(self.rs.get(f'{self.CT_URL}?per_page={count}&page={page}').json()):
            if not 'tag_name' in release:
                continue

            tags.append(release['tag_name'])
            if 'assets' not in release or len(release['assets']) <= 0:
                continue

            if any('lutris-fshack' in asset['name'] for asset in release['assets']):
                tags.append(release['tag_name'].replace('lutris-', 'lutris-fshack-'))

        return tags

    def __fetch_github_data(self, tag: str, is_fshack: bool):

        """
        Fetch GitHub release information
        Return Type: dict
        Content(s):
            'version', 'date', 'download', 'size', 'checksum'
        """

        asset_condition = None
        if is_fshack:
            asset_condition = lambda asset: 'fshack' in asset['name']

        return fetch_project_release_data(self.CT_URL, self.release_format, self.rs, tag=tag, asset_condition=asset_condition)

    def __get_data(self, version: str, install_dir: str) -> tuple[dict | None, str | None]:

        """
        Get needed download data and path to extract directory.
        Return Type: tuple[dict | None, str | None]
        """

        is_fshack = 'fshack-' in version
        if is_fshack:
            version = version.replace('fshack-', '')

        data = self.__fetch_github_data(version, is_fshack)
        if not data or 'download' not in data:
            return (None, None)

        # Overwrite the Proton installation directory as the format we need for Lutris Wine
        protondir = f'{install_dir}wine-{data["version"].lower()}-x86_64'

        return (data, protondir)

    def get_info_url(self, version: str) -> str:

        """
        Get link with info about version (eg. GitHub release page)
        Return Type: str
        """

        return super().get_info_url(version.replace('fshack-', ''))

    def get_extract_dir(self, install_dir: str) -> str:

        """
        Return the directory to extract Lutris-Wine archive based on the current launcher
        Return Type: str
        """

        # GE-Proton ctmod figures out if it needs to into a different folder
        #
        # Lutris-Wine can use default 'install_dir' always because it is Wine and not Proton,
        # so override to return unmodified 'install_dir'
        return install_dir
