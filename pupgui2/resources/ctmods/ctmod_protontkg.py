# pupgui2 compatibility tools module
# Proton-Tkg https://github.com/Frogging-Family/wine-tkg-git
# Copyright (C) 2022 DavidoTek, partially based on AUNaseef's protonup

import os
import glob
import shutil
import tarfile
import requests
import zstandard
from zipfile import ZipFile

from PySide6.QtCore import QObject, QCoreApplication, Signal, Property

from pupgui2.util import ghapi_rlcheck


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
    TKG_EXTRACT_NAME = 'proton_tkg'

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

        destination = temp_dir
        destination += data['download'].split('/')[-1]

        if not self.__download(url=data['download'], destination=destination, f_size=data.get("size")):
            return False

        install_folder = f'{install_dir}{self.TKG_EXTRACT_NAME}' + data['version'].lower()
        if os.path.exists(install_folder):
            shutil.rmtree(install_folder)

        if '.tar.gz' in destination:
            tarfile.open(destination, "r:gz").extractall(install_dir)
        elif '.zip' in destination:
            with ZipFile(destination) as z:
                os.mkdir(install_folder)
                z.extractall(install_folder)
            
            # Supports both Wine-tkg and Proton-tkg
            zst_glob = glob.glob(f'{install_folder}/*.tar.zst')
            if len(zst_glob) > 0:
                # Wine-tkg is .tar.zst
                tkg_dir = self.get_extract_dir(install_dir)

                tkg_archive_name = zst_glob[0]  # Should only ever be 1 really, so assume the first is the zst archive we're looking for

                temp_download = os.path.join(install_folder, tkg_archive_name)
                temp_archive = temp_download.replace('.zst', '')

                # Extract .tar.zst file - Closely mirrors vkd3d-proton ctmod except for extraction logic
                tkg_decomp = zstandard.ZstdDecompressor()

                with open(temp_download, 'rb') as tkg_infile, open(temp_archive, 'wb') as tkg_outfile:
                    tkg_decomp.copy_stream(tkg_infile, tkg_outfile)

                with open(temp_archive, 'rb') as tkg_outfile:
                    with tarfile.open(fileobj=tkg_outfile) as tkg_tarfile:
                        tkg_tarfile.extractall(tkg_dir)
                        final_extract_dir = os.path.dirname(tkg_archive_name)

                        shutil.rmtree(final_extract_dir)  # Remove extracted folder
                        os.rename(os.path.join(install_dir, 'usr'), final_extract_dir)  # Rename extracted 'usr' folder to match the .zip file extracted name for consistency / easier removal if redownloading

                        # Remove lingering dotfiles
                        remove_extractfiles = [ '.BUILDINFO', '.INSTALL', '.MTREE', '.PKGINFO' ]
                        for rmfile in remove_extractfiles:
                            rmfile_fullpath = os.path.join(install_dir, rmfile)
                            if os.path.exists(rmfile_fullpath):
                                os.remove(rmfile_fullpath)
            else:
                # Regular .zip for Proton-tkg
                #
                # Workaround for artifact .zip archive is actually .tar inside, wtf.
                f_count = 0
                for f in glob.glob(f"{install_folder}/*.tar"):
                    f_count += 1
                    tarfile.open(f, "r").extractall(install_dir)
                if f_count > 0:
                    shutil.rmtree(install_folder)
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
