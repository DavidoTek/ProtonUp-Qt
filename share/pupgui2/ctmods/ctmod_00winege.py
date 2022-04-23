# pupgui2 compatibility tools module
# Wine-GE
# Copyright (C) 2021 DavidoTek, partially based on AUNaseef's protonup

import os, shutil, tarfile, requests, hashlib
from PySide6.QtCore import *

CT_NAME = 'Wine-GE'
CT_LAUNCHERS = ['lutris', 'heroicwine']
CT_DESCRIPTION = {}
CT_DESCRIPTION['en'] = '''Compatibility tool "Wine" to run Windows games on Linux. Based on Valve Proton Experimental's bleeding-edge Wine, built for Lutris.<br/><br/><b>Use this when you don't know what to choose.</b>'''
CT_DESCRIPTION['de'] = '''Kompatibilitätstool "Wine" für Windows-Spiele unter Linux. Basiert auf der neusten Wine Version von Value Proton Experimental, für Lutris.<br/><br/><b>Verwende dies, wenn du dir nicht sicher bist.</b>'''
CT_DESCRIPTION['en'] = '''Compatibiliteitshulpmiddel 'Wine' voor het spelen van Windows-games op Linux. Dit hulpmiddel is gebaseerd op Valve Proton Experimental's Wine en is gemaakt voor Lutris.<br/><br/><b>Bij twijfel, kies dit hulpmiddel.</b>'''
CT_DESCRIPTION['pl'] = '''Narzędzie kompatybilności "Wine" do uruchamiania Windowsowych gier na Linuksie. Bazuje na Valve'owym Protonie Experimental bleeding-edge Wine, zbudowane dla Lutrisa.<br/><br/><b>Użyj tego, jeśli nie wiesz co wybrać.</b>'''


class CtInstaller(QObject):
    
    BUFFER_SIZE = 65536
    CT_URL = 'https://api.github.com/repos/GloriousEggroll/wine-ge-custom/releases'
    CT_INFO_URL = 'https://github.com/GloriousEggroll/wine-ge-custom/releases/tag/'

    p_download_progress_percent = 0
    download_progress_percent = Signal(int)

    def __init__(self):
        super(CtInstaller, self).__init__()
        self.p_download_canceled = False
    
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
            file = requests.get(url, stream=True)
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
    
    def __sha512sum(self, filename):
        """
        Get SHA512 checksum of a file
        Return Type: str
        """
        sha512sum = hashlib.sha512()
        with open(filename, 'rb') as file:
            while True:
                data = file.read(self.BUFFER_SIZE)
                if not data:
                    break
                sha512sum.update(data)
        return sha512sum.hexdigest()
    
    def __fetch_github_data(self, tag):
        """
        Fetch GitHub release information
        Return Type: dict
        Content(s):
            'version', 'date', 'download', 'size', 'checksum'
        """
        url = self.CT_URL + (f'/tags/{tag}' if tag else '/latest')
        data = requests.get(url).json()
        if 'tag_name' not in data:
            return None

        values = {'version': data['tag_name'], 'date': data['published_at'].split('T')[0]}
        for asset in data['assets']:
            if asset['name'].endswith('sha512sum'):
                values['checksum'] = asset['browser_download_url']
            elif asset['name'].endswith('tar.xz'):
                values['download'] = asset['browser_download_url']
                values['size'] = asset['size']
        return values
    
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
        tags = []
        for release in requests.get(self.CT_URL + '?per_page=' + str(count)).json():
            if 'tag_name' in release:
                tags.append(release['tag_name'])
        return tags

    def get_tool(self, version, install_dir, temp_dir):
        """
        Download and install the compatibility tool
        Return Type: bool
        """
        data = self.__fetch_github_data(version)

        if not data or 'download' not in data:
            return False
        
        protondir = install_dir + 'lutris-ge-' + data['version'].replace('GE-', '').lower() + '-x86_64'
        checksum_dir = protondir + '/sha512sum'
        source_checksum = requests.get(data['checksum']).text if 'checksum' in data else None
        local_checksum = open(checksum_dir).read() if os.path.exists(checksum_dir) else None

        if os.path.exists(protondir):
            if local_checksum and source_checksum:
                if local_checksum in source_checksum:
                    return False
            else:
                return False

        destination = temp_dir
        destination += data['download'].split('/')[-1]
        destination = destination

        if not self.__download(url=data['download'], destination=destination):
            return False

        download_checksum = self.__sha512sum(destination)
        if source_checksum and (download_checksum not in source_checksum):
            return False
        
        if os.path.exists(protondir):
            shutil.rmtree(protondir)
        tarfile.open(destination, "r:xz").extractall(install_dir)
        if os.path.exists(checksum_dir):
            open(checksum_dir, 'w').write(download_checksum)

        self.__set_download_progress_percent(100)

        return True

    def get_info_url(self, version):
        """
        Get link with info about version (eg. GitHub release page)
        Return Type: str
        """
        return self.CT_INFO_URL + version
