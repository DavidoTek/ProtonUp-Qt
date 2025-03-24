# pupgui2 compatibility tools module
# Proton-CachyOS
# Copyright (C) 2021 DavidoTek, partially based on AUNaseef's protonup

import os

from PySide6.QtCore import QCoreApplication

from pupgui2.util import ghapi_rlcheck, extract_tar
from .ctmod_00protonge import CtInstaller as ProtonGECtInstaller

CT_NAME = 'Proton-CachyOS'
CT_LAUNCHERS = ['steam', 'heroicproton', 'bottles']
CT_DESCRIPTION = {
    'en': QCoreApplication.instance().translate(
        'ctmod_protoncachyos',
        '''
        Steam compatibility tool from the CachyOS Linux distribution for running Windows games
        with improvements over Valve's default Proton. Choose the one corresponding to your CPU.
        <br/><br/>
        * <b>x86_64</b>: Works on any x64_64 CPU
        <br/>
        * <b>x86_64_v3</b>: For CPUs that support AVX2 and up
        '''
    )
}


class CtInstaller(ProtonGECtInstaller):

    BUFFER_SIZE = 65536
    CT_URL = 'https://api.github.com/repos/CachyOS/proton-cachyos/releases'
    CT_INFO_URL = 'https://github.com/CachyOS/proton-cachyos/releases/tag/'

    def __fetch_github_data(self, tag: str, arch: str) -> dict | None:
        """
        Fetch GitHub release information
        Return Type: dict
        Content(s):
            'version', 'date', 'download', 'size', 'checksum'
        """
        url = self.CT_URL + (f'/tags/{tag}' if tag else '/latest')
        data = self.rs.get(url).json()
        if 'tag_name' not in data:
            return None

        values = {'version': data['tag_name'], 'date': data['published_at'].split('T')[0]}
        for asset in data['assets']:
            if asset['name'].endswith(f'{arch}.sha512sum'):
                values['checksum'] = asset['browser_download_url']
            elif asset['name'].endswith(f'{arch}.tar.xz'):
                values['download'] = asset['browser_download_url']
                values['size'] = asset['size']
        return values

    def get_hwcaps(self) -> set[str]:
        hwcaps = {'x86_64'}
        # flags according to https://gitlab.com/x86-psABIs/x86-64-ABI/-/blob/master/x86-64-ABI/low-level-sys-info.tex
        flags_v2 = {'sse4_1', 'sse4_2', 'ssse3'}
        flags_v3 = {*flags_v2, 'avx', 'avx2'}
        flags_v4 = {*flags_v3, 'avx512f', 'avx512bw', 'avx512cd', 'avx512dq', 'avx512vl'}
        with open('/proc/cpuinfo', 'r') as cpuinfo:
            for line in cpuinfo:
                if line.startswith('flags'):
                    flags = line.split(":")[1].strip().split()
        flags = set(flags)
        if flags_v4.issubset(flags):
            hwcaps.add('x86_64_v4')
        if flags_v3.issubset(flags):
            hwcaps.add('x86_64_v3')
        if flags_v2.issubset(flags):
            hwcaps.add('x86_64_v2')
        return hwcaps

    def fetch_releases(self, count: int = 100, page: int = 1) -> list:
        """
        List available releases
        Return Type: str[]
        """
        hwcaps = self.get_hwcaps()
        assets = []
        releases = ghapi_rlcheck(self.rs.get(f'{self.CT_URL}?per_page={count}&page={page}').json())
        for release in releases:
            for asset in release['assets']:
                name = asset["name"]
                if name.endswith(".tar.xz"):
                    name = name.strip(".tar.xz")
                    _, _, major, minor, _, arch = name.split("-")
                    name = "-".join((major, minor, arch))
                    if arch in hwcaps and name not in assets:
                        assets.append(name)
        return assets

    def get_tool(self, version: str, install_dir: str, temp_dir: str):
        """
        Download and install the compatibility tool
        Return Type: bool
        """
        major, minor, arch = version.split("-")
        tag = "-".join(('cachyos', major, minor, 'slr'))
        data = self.__fetch_github_data(tag, arch)

        if not data or 'download' not in data:
            return False

        protondir = os.path.join(install_dir, data['version'])
        if not os.path.exists(protondir):
            protondir = os.path.join(install_dir, 'proton-' + data['version'])
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
        if not self.__download(url=data['download'], destination=proton_tar, known_size=data.get('size', 0)):
            return False

        download_checksum = self.__sha512sum(proton_tar)
        if source_checksum and (download_checksum not in source_checksum):
            return False

        if not extract_tar(proton_tar, install_dir, mode='xz'):
            return False

        if os.path.exists(checksum_dir):
            open(checksum_dir, 'w').write(download_checksum)

        self.__set_download_progress_percent(100)

        return True

    def get_info_url(self, version: str) -> str:
        """
        Get link with info about version (eg. GitHub release page)
        Return Type: str
        """
        major, minor, arch = version.split("-")
        tag = "-".join(('cachyos', major, minor, 'slr'))
        return self.CT_INFO_URL + tag
