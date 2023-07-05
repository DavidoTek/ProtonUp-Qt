# pupgui2 compatibility tools module
# DXVK for Lutris (nightly version): https://github.com/doitsujin/dxvk/
# Copyright (C) 2022 DavidoTek, partially based on AUNaseef's protonup

import os
import requests

from PySide6.QtCore import QObject, QCoreApplication, Signal, Property

from pupgui2.util import ghapi_rlcheck, extract_zip


CT_NAME = 'DXVK (nightly)'
CT_LAUNCHERS = ['lutris', 'advmode']
CT_DESCRIPTION = {'en': QCoreApplication.instance().translate('ctmod_z2dxvknightly', '''Nightly version of DXVK (master branch), a Vulkan based implementation of Direct3D 9, 10 and 11 for Linux/Wine.<br/><br/><b>Warning: Nightly version is unstable, use with caution!</b>''')}


class CtInstaller(QObject):

    BUFFER_SIZE = 65536
    CT_URL = 'https://api.github.com/repos/doitsujin/dxvk/actions/artifacts'
    CT_INFO_URL = 'https://github.com/doitsujin/dxvk/commit/'

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

    def __download(self, url, destination, f_size):
        # f_size in argumentbecause artifacts don't have Content-Length.
        """
        Download files from url to destination
        Return Type: bool
        """
        try:
            file = requests.get(url, stream=True)
        except OSError:
            return False

        self.__set_download_progress_percent(1) # 1 download started
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

    def __get_artifact_from_commit(self, commit):
        """
        Get artifact from commit
        Return Type: str
        """
        for artifact in self.rs.get(f'{self.CT_URL}?per_page=100').json()["artifacts"]:
            if artifact['workflow_run']['head_sha'][:len(commit)] == commit:
                artifact['workflow_run']['head_sha'] = commit
                return artifact
        return None

    def __fetch_github_data(self, tag):
        """
        Fetch GitHub release information
        Return Type: dict
        Content(s):
            'version', 'date', 'download', 'size', 'checksum'
        """
        # Tag in this case is the commit hash.
        data = self.__get_artifact_from_commit(tag)
        if not data:
            return
        values = {'version': data['workflow_run']['head_sha'][:7], 'date': data['updated_at'].split('T')[0]}
        values['download'] = f'https://nightly.link/doitsujin/dxvk/actions/runs/{data["workflow_run"]["id"]}/{data["name"]}.zip'

        values['size'] = data['size_in_bytes']
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
        for artifact in ghapi_rlcheck(self.rs.get(f'{self.CT_URL}?per_page={str(count)}').json()).get("artifacts", {}):
            workflow = artifact['workflow_run']
            if workflow["head_branch"] != "master" or artifact["expired"]:
                continue
            tags.append(workflow['head_sha'][:7])
        return tags

    def get_tool(self, version, install_dir, temp_dir):
        """
    Download and install the compatibility tool
        Return Type: bool
        """
        data = self.__fetch_github_data(version)
        if not data or 'download' not in data:
            return False

        dxvk_zip = os.path.join(temp_dir, data['download'].split('/')[-1])
        if not self.__download(url=data['download'], destination=dxvk_zip, f_size=data['size']):
            return False

        dxvk_dir = os.path.join(install_dir, '../../runtime/dxvk', 'dxvk-git-' + data['version'])
        if not extract_zip(dxvk_zip, dxvk_dir):
            return False

        self.__set_download_progress_percent(100)

        return True

    def get_info_url(self, version):
        """
        Get link with info about version (eg. GitHub release page)
        Return Type: str
        """
        return self.CT_INFO_URL + version
