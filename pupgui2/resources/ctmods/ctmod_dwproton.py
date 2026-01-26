# pupgui2 compatibility tools module
# Dawn Winery's dwproton
# Copyright (C) 2025 DavidoTek, partially based on AUNaseef's protonup

import os
import requests

from PySide6.QtCore import QCoreApplication

from pupgui2.resources.ctmods.ctmod_00protonge import CtInstaller as GEProtonInstaller
from pupgui2.util import extract_tar

CT_NAME = 'dwproton'
CT_LAUNCHERS: list[str] = ['steam', 'lutris', 'heroicproton', 'bottles', 'advmode']
CT_DESCRIPTION: dict[str, str] = {
    'en': QCoreApplication.instance().translate('ctmod_dwproton', '''Dawn Winery's custom Proton fork with fixes for various games :xdd:''',)
}

class CtInstaller(GEProtonInstaller):

    CT_URL = 'https://dawn.wine/api/v1/repos/dawn-winery/dwproton/releases'
    CT_INFO_URL = 'https://dawn.wine/dawn-winery/dwproton/releases/tag/'

    def __init__(self, main_window=None):
        super().__init__(main_window)

        # Reset the session to clear GitHub Auth headers from the base class
        self.rs = requests.Session()
        self.release_format = 'tar.xz'

    def fetch_releases(self, count: int = 100, page: int = 1) -> list[str]:
        """
        Manually fetch releases to bypass pupgui2's strict GitHub/GitLab check.
        """
        try:
            params = {'limit': count, 'page': page}
            response = self.rs.get(self.CT_URL, params=params)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list):
                return [r['tag_name'] for r in data if 'tag_name' in r]
            return []
        except Exception as e:
            print(f"[{CT_NAME}] Error fetching releases: {e}")
            return []

    def _get_dw_data(self, version: str, install_dir: str) -> tuple[dict | None, str | None]:
        """
        Replacement for 'fetch_project_release_data'.
        Parses Gitea JSON to find the download link and checksum.
        """
        try:
            # Construct Gitea API URL for specific tag
            url = f"{self.CT_URL}/tags/{version}"
            resp = self.rs.get(url)
            resp.raise_for_status()
            data = resp.json()

            result = {
                'version': data.get('tag_name'),
                'download': None,
                'checksum': None,
                'size': 0
            }

            # Loop through assets to find the .tar.xz and .sha512sum
            for asset in data.get('assets', []):
                name = asset.get('name', '')

                # Found the main archive
                if name.endswith(self.release_format):
                    result['download'] = asset.get('browser_download_url')
                    result['size'] = asset.get('size')

                # Found the checksum file
                elif name.endswith('.sha512sum'):
                    result['checksum'] = asset.get('browser_download_url')

            protondir = os.path.join(install_dir, result['version'])

            return (result, protondir)
        except Exception as e:
            print(f"[{CT_NAME}] Failed to get data for {version}: {e}")
            return None

    def get_tool(self, version, install_dir, temp_dir):
        """
        Download and install the compatibility tool
        Return Type: bool
        """

        install_dir = self.get_extract_dir(install_dir)

        # Get Data using our custom method
        data, protondir = self._get_dw_data(version, install_dir)
        if not data or not data['download']:
            return False

        # Note: protondir is only used for checksums
        if not protondir or  not os.path.exists(protondir):
            protondir = os.path.join(install_dir, 'Proton-' + data['version'])  # Check if we have an older Proton-GE folder name

        checksum_dir = f'{protondir}/sha512sum'
        source_checksum = self.rs.get(data['checksum']).text if 'checksum' in data else None
        local_checksum = open(checksum_dir).read() if os.path.exists(checksum_dir) else None

        if os.path.exists(protondir):
            if local_checksum and source_checksum:
                if local_checksum in source_checksum:
                    return False
            else:
                return False

        proton_tar = os.path.join(temp_dir, data['download'].split('/')[-1])
        if not self.__download(url=data['download'], destination=proton_tar):
            return False

        download_checksum = self.__sha512sum(proton_tar)
        if source_checksum and (download_checksum not in source_checksum):
            return False

        if not extract_tar(proton_tar, install_dir, mode=self.release_format.split('.')[-1]):
            return False

        if os.path.exists(checksum_dir):
            open(checksum_dir, 'w').write(download_checksum)

        self.__set_download_progress_percent(100)

        return True
