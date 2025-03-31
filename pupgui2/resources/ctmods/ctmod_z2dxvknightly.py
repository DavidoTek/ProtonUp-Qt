# pupgui2 compatibility tools module
# DXVK for Lutris (nightly version): https://github.com/doitsujin/dxvk/
# Copyright (C) 2022 DavidoTek, partially based on AUNaseef's protonup

import os

from PySide6.QtCore import QCoreApplication

from pupgui2.util import ghapi_rlcheck

from pupgui2.resources.ctmods.ctmod_z0dxvk import CtInstaller as DXVKInstaller


CT_NAME = 'DXVK (nightly)'
CT_LAUNCHERS = ['lutris', 'advmode']
CT_DESCRIPTION = {'en': QCoreApplication.instance().translate('ctmod_z2dxvknightly', '''Nightly version of DXVK (master branch), a Vulkan based implementation of Direct3D 8, 9, 10 and 11 for Linux/Wine.<br/><br/><b>Warning: Nightly version is unstable, use with caution!</b>''')}


class CtInstaller(DXVKInstaller):

    BUFFER_SIZE: int = 65536
    CT_WORKFLOW_URL: str = 'https://api.github.com/repos/doitsujin/dxvk/actions/workflows'
    CT_ARTIFACT_URL: str = 'https://api.github.com/repos/doitsujin/dxvk/actions/runs/{}/artifacts'
    CT_INFO_URL: str = 'https://github.com/doitsujin/dxvk/commit/'

    DXVK_WORKFLOW_NAME = 'artifacts'

    def __init__(self, main_window = None):

        super().__init__(main_window)

        self.release_format: str = 'zip'

    # TODO break out into separate util function and unit test with:
    #      * happy path
    #      * 30 successful workflows across pages (expired artifacts that spread them across pages)
    #      * successful workflows but not enough to mmatch the count (say 15 successful workflows)
    #      * 0 successful workflows (all failed) 
    def __fetch_workflows(self, count: int = 30) -> list:

        """
        Get all active, successful runs in the DXVK Linux-compatible workflow.
        Return Type: list
        """

        tags: list = []
        for workflow in self.rs.get(f'{self.CT_WORKFLOW_URL}?per_page={str(count)}').json().get("workflows", {}):
            if workflow['state'] != "active" or self.DXVK_WORKFLOW_NAME not in workflow['path']:
                continue

            page = 1
            while page != -1 and page < 5:  # fetch more (up to 5 pages) if first releases all failed
                at_least_one_failed = False  # ensure the reason that len(tags)=0 is that releases failed
                for run in self.rs.get(workflow['url'] + f'/runs?per_page={str(count)}&page={page}').json()['workflow_runs']:
                    if run['conclusion'] == "success":
                        tags.append(str(run['id']))
                    elif run['conclusion'] == "failure":
                        at_least_one_failed = True

                if len(tags) == 0 and at_least_one_failed:
                    page += 1
                else:
                    page = -1

        return tags

    def fetch_releases(self, count: int = 30, page: int = 1) -> list[str]:

        """
        List available releases.
        Return Type: str[]
        """

        return self.__fetch_workflows(count=count)

    # TODO break out into separate util functio and unit test
    def __get_artifact_url_from_id(self, id: str):
        """
        Get artifact by the workflow run ID.
        Return Type: str
        """
        print(f'{self.CT_ARTIFACT_URL.format(id)}?per_page=100')

        artifact_info = self.rs.get(f'{self.CT_ARTIFACT_URL.format(id)}?per_page=100').json()
        if artifact_info.get("total_count") != 1:
            return None

        return artifact_info["artifacts"][0]

    def __fetch_github_data(self, tag: str):

        """
        Fetch GitHub release information
        Return Type: dict
        Content(s):
            'version', 'date', 'download', 'size'
        """

        # Tag in this case is the workflow run ID
        data = self.__get_artifact_url_from_id(tag)
        if not data:
            return
        values = {'version': data['workflow_run']['head_sha'][:7], 'date': data['updated_at'].split('T')[0]}
        values['download'] = f'https://nightly.link/doitsujin/dxvk/actions/runs/{data["workflow_run"]["id"]}/{data["name"]}.zip'

        values['size'] = data['size_in_bytes']
        return values

    def __get_data(self, version: str, install_dir: str) -> tuple[dict | None, str | None]:

        """
        Get needed download data and path to extract directory.
        Return Type: diple[dict | None, str | None]
        """

        data = self.__fetch_github_data(version)
        if not data or not 'download' in data:
            return (None, None)

        # TODO This is hardcoded to Lutris as DXVK Nightly currently doesn't support any other launchers -- Could possibly add support for Heroic in future
        dxvk_dir = os.path.join(install_dir, '../../runtime/dxvk', 'dxvk-git-' + data['version'])

        return (data, dxvk_dir)

    def get_info_url(self, version: str) -> str:

        """
        Get link with info about version (eg. GitHub release page)
        Return Type: str
        """

        return self.CT_INFO_URL + version
