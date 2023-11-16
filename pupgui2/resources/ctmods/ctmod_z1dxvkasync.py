# pupgui2 compatibility tools module
# DXVK with async patch for Lutris: https://github.com/Sporif/dxvk-async/
# Copyright (C) 2022 DavidoTek, partially based on AUNaseef's protonup

from PySide6.QtCore import QCoreApplication

from pupgui2.resources.ctmods.ctmod_z0dxvk import CtInstaller as DXVKInstaller
from pupgui2.util import build_headers_with_authorization


CT_NAME = 'DXVK Async'
CT_LAUNCHERS = ['lutris']
CT_DESCRIPTION = {'en': QCoreApplication.instance().translate('ctmod_z1dxvkasync', '''Vulkan based implementation of Direct3D 9, 10 and 11 for Linux/Wine with gplasync patch by Ph42oN.<br/><br/><b>Warning: Use only with singleplayer games!</b>''')}


class CtInstaller(DXVKInstaller):

    CT_URL = 'https://gitlab.com/api/v4/projects/43488626/releases'
    CT_INFO_URL = 'https://gitlab.com/Ph42oN/dxvk-gplasync/-/releases/'

    def __init__(self, main_window = None):
        super().__init__(main_window)

        rs_headers = build_headers_with_authorization({}, main_window.web_access_tokens, 'gitlab')
        self.rs.headers.update(rs_headers)
