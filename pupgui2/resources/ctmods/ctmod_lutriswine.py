# pupgui2 compatibility tools module
# Lutris-Wine
# Copyright (C) 2021 DavidoTek, partially based on AUNaseef's protonup

from typing import override
from PySide6.QtCore import QObject, QCoreApplication, Signal, Property

from pupgui2.util import ghapi_rlcheck

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

    @override
    def fetch_releases(self, count: int = 100, page:int = 1):
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

    # TODO can we simplify this with the get_release_data methods? Would also apply to GE-Proton and be a nice win
    @override
    def __fetch_github_data(self, tag, is_fshack):

        url = self.CT_URL + (f'/tags/{tag}' if tag else '/latest')
        data = self.rs.get(url).json()
        if 'tag_name' not in data:
            return None

        values = {'version': data['tag_name'], 'date': data['published_at'].split('T')[0]}
        for asset in data['assets']:
            if asset['name'].endswith('sha512sum'):
                values['checksum'] = asset['browser_download_url']
            # only change from GE-Proton is that we have this check for fshack to include Lutris fshack builds as valid releases
            elif asset['name'].endswith('tar.xz') and not ('fshack' in asset['name'] and not is_fshack):
                values['download'] = asset['browser_download_url']
                values['size'] = asset['size']
        return values

    @override
    def __get_data(self, version: str, install_dir: str) -> tuple[dict | None, str | None]:

        is_fshack = 'fshack-' in version
        if is_fshack:
            version = version.replace('fshack-', '')

        data = self.__fetch_github_data(version, is_fshack)
        if not data or 'download' not in data:
            return (None, None)

        # Overwrite the Proton installation directory as the format we need for Lutris Wine
        protondir = protondir = f'{install_dir}wine-{data["version"].lower()}-x86_64'

        return (data, protondir)
