# pupgui2 compatibility tools module
# Proton-Tkg https://github.com/Frogging-Family/wine-tkg-git
# Copyright (C) 2022 DavidoTek, partially based on AUNaseef's protonup

import os
import glob
import requests

from PySide6.QtCore import QObject, QCoreApplication, Signal, Property

from pupgui2.util import ghapi_rlcheck, extract_tar, extract_zip, extract_tar_zst, remove_if_exists


CT_NAME = 'Proton Tkg'
CT_LAUNCHERS = ['steam', 'heroicproton']
CT_DESCRIPTION = {'en': QCoreApplication.instance().translate('ctmod_protontkg', '''Custom Proton build for running Windows games, built with the Wine-tkg build system.''')}


class CtInstaller(QObject):

    BUFFER_SIZE = 65536
    CT_URL = 'https://api.github.com/repos/Frogging-Family/wine-tkg-git/releases'
    CT_INFO_URL = 'https://github.com/Frogging-Family/wine-tkg-git/releases/tag/'
    CT_WORKFLOW_URL = 'https://api.github.com/repos/Frogging-Family/wine-tkg-git/actions/workflows'
    CT_ARTIFACT_URL = 'https://api.github.com/repos/Frogging-Family/wine-tkg-git/actions/runs/{}/artifacts'
    CT_INFO_URL_CI = 'https://github.com/Frogging-Family/wine-tkg-git/actions/runs/'
    PROTON_PACKAGE_NAME = 'proton-valvexbe-arch-nopackage'

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

    def __download(self, url, destination, f_size=None):
        """
        Download files from url to destination
        Return Type: bool
        """
        try:
            if 'https://github.com' in url:
                file = self.rs.get(url, stream=True)
            else:
                file = requests.get(url, stream=True)
        except OSError:
            return False

        self.__set_download_progress_percent(1) # 1 download started
        if not f_size:
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

    def __get_artifact_from_id(self, commit):
        """
        Get artifact from workflow run id.
        Return Type: str
        """
        artifact_info = self.rs.get(f'{self.CT_ARTIFACT_URL.format(commit)}?per_page=100').json()
        if artifact_info.get("total_count") != 1:
            return None
        return artifact_info["artifacts"][0]

    def __fetch_github_data_ci(self, tag):
        """
        Fetch GitHub CI information
        Return Type: dict
        Content(s):
            'version', 'date', 'download', 'size', 'checksum'
        """
        # Tag in this case is the commit hash.
        data = self.__get_artifact_from_id(tag)
        if not data:
            return
        values = {'version': data['workflow_run']['head_sha'], 'date': data['updated_at'].split('T')[0]}
        values['download'] = f'https://nightly.link/Frogging-Family/wine-tkg-git/actions/runs/{data["workflow_run"]["id"]}/{data["name"]}.zip'

        values['size'] = data['size_in_bytes']
        return values

    def __fetch_github_data(self, tag):
        """
        Fetch GitHub release information
        Return Type: dict
        Content(s):
            'version', 'date', 'download', 'size', 'checksum'
        """
        values = self.__fetch_github_data_ci(tag)
        if values:
            return values

        url = self.CT_URL + (f'/tags/{tag}' if tag else '/latest')
        data = self.rs.get(url).json()
        if 'tag_name' not in data:
            return None

        values = {'version': data['tag_name'], 'date': data['published_at'].split('T')[0]}
        for asset in data['assets']:
            if 'proton' in asset['name']:
                values['download'] = asset['browser_download_url']
                values['size'] = asset['size']
        return values

    def is_system_compatible(self):
        """
        Are the system requirements met?
        Return Type: bool
        """
        return True

    def __fetch_workflows(self, count=30):
        tags = []
        for workflow in self.rs.get(f'{self.CT_WORKFLOW_URL}?per_page={str(count)}').json().get("workflows", {}):
            if workflow['state'] != "active" or self.PROTON_PACKAGE_NAME not in workflow['path']:
                continue
            page = 1
            while page != -1 and page < 5:  # fetch more (up to 5 pages) if first releases all failed
                at_least_one_failed = False  # ensure the reason that len(tags)=0 is that releases failed
                for run in self.rs.get(workflow["url"] + f"/runs?per_page={str(count)}&page={page}").json()["workflow_runs"]:
                    if run['conclusion'] == "success":
                        tags.append(str(run['id']))
                    elif run['conclusion'] == "failure":
                        at_least_one_failed = True
                if len(tags) == 0 and at_least_one_failed:
                    page += 1
                else:
                    page = -1

        return tags

    def fetch_releases(self, count=30):
        """
        List available releases
        Return Type: str[]
        """
        tags = self.__fetch_workflows(count=count)
        for release in ghapi_rlcheck(self.rs.get(f'{self.CT_URL}?per_page={str(count)}').json()):
            # Check assets length because latest release (7+) doesn't have assets.
            if 'tag_name' not in release or len(release["assets"]) == 0:
                continue
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

        tkg_archive = os.path.abspath(os.path.join(temp_dir, data['download'].split('/')[-1]))
        if not self.__download(url=data['download'], destination=tkg_archive, f_size=data.get("size")):
            return False

        # Tkg Archive Format Reference:
        # Legacy GitHub Releases use .tar.gz files
        # GitHub Actions releases use .zip files with various archive formats inside
        # -----
        # Proton-tkg: .tar
        # Proton-tkg (Wine Master): .tar
        # Wine-tkg (Valve Wine): .tar.zst
        # Wine-tkg (Vanilla Wine): .tar

        # Extract tool
        if tkg_archive.endswith('.tar.gz'):  # Legacy archives from GitHub releases
            if not extract_tar(tkg_archive, install_dir, mode='gz'):
                return False
            remove_if_exists(tkg_archive)
        elif tkg_archive.endswith('.zip'):  # GitHub Actions builds
            tkg_extract_tmp = os.path.join(temp_dir, f'tkg_extract_tmp')
            if not extract_zip(tkg_archive, tkg_extract_tmp):
                return False
            remove_if_exists(tkg_archive)

            if zst_glob := glob.glob(f'{tkg_extract_tmp}/*.tar.zst'):
                # Extract .tar.zst nested inside .zip
                tkg_zst = zst_glob[0]
                tkg_zst_basename = os.path.basename(tkg_zst.replace('.tar.zst', ''))
                tkg_zst_extract_path = os.path.abspath(os.path.join(install_dir, 'usr'))
                tkg_zst_dest_path = os.path.abspath(os.path.join(install_dir, tkg_zst_basename))

                # Extract and rename archive
                remove_if_exists(tkg_zst_dest_path)
                if not extract_tar_zst(tkg_zst, install_dir):
                    return False
                os.rename(tkg_zst_extract_path, tkg_zst_dest_path)

                # Remove lingering dotfiles
                remove_extractfiles = [ '.BUILDINFO', '.INSTALL', '.MTREE', '.PKGINFO' ]
                for rmfile in remove_extractfiles:
                    remove_if_exists(os.path.join(install_dir, rmfile))
                remove_if_exists(tkg_zst)
            elif tar_glob := glob.glob(f"{tkg_extract_tmp}/*.tar"): 
                # Regular .tar
                tkg_tar = tar_glob[0]
                tkg_tar_extract_path = os.path.join(install_dir, os.path.basename(tkg_tar).replace('.tar', ''))

                remove_if_exists(tkg_tar_extract_path)
                if not extract_tar(tkg_tar, install_dir):
                    return False
                remove_if_exists(tkg_tar)
        else:
            self.__set_download_progress_percent(-1)
            return False

        self.__set_download_progress_percent(100)
        return True

    def get_extract_dir(self, install_dir: str) -> str:
        """
        Return the directory to extract TkG archive based on the current launcher
        Return Type: str
        """

        if 'lutris/runners' in install_dir:
            return os.path.abspath(os.path.join(install_dir, '../../runners/wine'))
        else:
            return install_dir  # Default to install_dir

    def get_info_url(self, version):
        """
        Get link with info about version (eg. GitHub release page)
        Return Type: str
        """
        if self.__get_artifact_from_id(version):
            return self.CT_INFO_URL_CI + version

        return self.CT_INFO_URL + version
