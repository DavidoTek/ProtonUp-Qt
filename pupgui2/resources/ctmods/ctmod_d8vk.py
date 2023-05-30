# pupgui2 compatibility tools module
# D8VK for Lutris (nightly version): https://github.com/AlpyneDreams/d8vk/
# Copyright (C) 2022 DavidoTek, partially based on AUNaseef's protonup

import os
import shutil
import requests
import zipfile

from PySide6.QtCore import QObject, QCoreApplication, Signal, Property

from pupgui2.util import ghapi_rlcheck


CT_NAME = 'D8VK (nightly)'
CT_LAUNCHERS = ['lutris', 'heroicwine', 'heroicproton', 'advmode']
CT_DESCRIPTION = {}
CT_DESCRIPTION['en'] = QCoreApplication.instance().translate('ctmod_d8vk', '''Vulkan-based implementation of Direct3D 8/9/10/11 (Nightly).<br/><br/><b>Warning: Nightly version is unstable, use with caution!</b>''')


class CtInstaller(QObject):

    BUFFER_SIZE = 65536
    CT_URL = 'https://api.github.com/repos/AlpyneDreams/d8vk/actions/artifacts'
    CT_INFO_URL = 'https://github.com/AlpyneDreams/d8vk/commit/'

    p_download_progress_percent = 0
    download_progress_percent = Signal(int)

    def __init__(self, main_window = None):
        super(CtInstaller, self).__init__()
        self.p_download_canceled = False
        self.rs = main_window.rs if main_window.rs else requests.Session()

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
        for artifact in self.rs.get(self.CT_URL + '?per_page=100').json()["artifacts"]:
            if artifact['workflow_run']['head_sha'][:len(commit)] == commit and 'd8vk' in artifact['name']:  # Only get D8VK artifacts and not DXVK native artifacts
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
        values['download'] = "https://nightly.link/AlpyneDreams/d8vk/actions/runs/{}/{}.zip".format(
            data["workflow_run"]["id"],  data["name"]
        )
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
        for artifact in ghapi_rlcheck(self.rs.get(self.CT_URL + '?per_page=' + str(count)).json()).get("artifacts", {}):
            workflow = artifact['workflow_run']
            if not workflow["head_branch"] == "main" or artifact["expired"]:
                continue
            if workflow['head_sha'][:7] not in tags:  # Downloads wrong releases sometimes? Folder structure looks wrong -- Maybe wrong one downloaded from nightly link or wrong suite? (maybe only ever other entry is right and we're filtering the "proper" ones)
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

        dxvk_dir = self.get_extract_dir(install_dir)
        dxvk_install_dir = os.path.join(dxvk_dir, 'd8vk-git-' + data['version'])
        destination = temp_dir
        destination += data['download'].split('/')[-1]
        destination = destination

        if not self.__download(url=data['download'], destination=destination, f_size=data['size']):
            return False

        if os.path.exists(dxvk_dir + 'd8vk-git-' + data['version']):
            shutil.rmtree(dxvk_dir + 'd8vk-git-' + data['version'])
        with zipfile.ZipFile(destination) as zip:
            zip.extractall(dxvk_install_dir)

        self.__set_download_progress_percent(100)

        return True

    def get_info_url(self, version):
        """
        Get link with info about version (eg. GitHub release page)
        Return Type: str
        """
        return self.CT_INFO_URL + version

    def get_extract_dir(self, install_dir: str) -> str:
        """
        Return the directory to extract D8VK archive based on the current launcher
        Return Type: str
        """

        if 'lutris/runners' in install_dir:
            return os.path.abspath(os.path.join(install_dir, '../../runtime/dxvk'))
        if 'heroic/tools' in install_dir:
            return os.path.abspath(os.path.join(install_dir, '../dxvk'))
        else:
            return install_dir  # Default to install_dir
