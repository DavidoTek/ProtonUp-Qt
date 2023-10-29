# pupgui2 compatibility tools module
# DXVK with async patch for Lutris: https://github.com/Sporif/dxvk-async/
# Copyright (C) 2022 DavidoTek, partially based on AUNaseef's protonup

from PySide6.QtCore import QCoreApplication

from pupgui2.resources.ctmods.ctmod_z0dxvk import CtInstaller as DXVKInstaller


CT_NAME = 'DXVK Async'
CT_LAUNCHERS = ['lutris']
CT_DESCRIPTION = {'en': QCoreApplication.instance().translate('ctmod_z1dxvkasync', '''Vulkan based implementation of Direct3D 9, 10 and 11 for Linux/Wine with gplasync patch by Ph42oN.<br/><br/><b>Warning: Use only with singleplayer games!</b>''')}


class CtInstaller(DXVKInstaller):

    CT_URL = 'https://gitlab.com/api/v4/projects/43488626/releases'
    CT_INFO_URL = 'https://gitlab.com/Ph42oN/dxvk-gplasync/-/releases/'

    def __init__(self, main_window = None, request_headers = {}):
        if main_window and main_window.web_access_tokens.get('gitlab', None) and 'Authorization' not in request_headers:
            request_headers['Authorization'] = f'Authorization: Bearer {main_window.web_access_tokens.get("gitlab", None)}'

        super().__init__(main_window, request_headers)
