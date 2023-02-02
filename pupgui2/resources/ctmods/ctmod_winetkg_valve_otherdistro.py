# pupgui2 compatibility tools module
# Proton-Tkg https://github.com/Frogging-Family/wine-tkg-git
# Copyright (C) 2022 DavidoTek, partially based on AUNaseef's protonup

import os
import glob
import shutil
import tarfile
from zipfile import ZipFile

from PySide6.QtCore import QCoreApplication, Signal

from pupgui2.resources.ctmods.ctmod_protontkg import CtInstaller as TKGCtInstaller  # Use ProtonTKg Ctmod as base


CT_NAME = 'Wine Tkg (Valve Wine)'
CT_LAUNCHERS = ['lutris']
CT_DESCRIPTION = {'en': QCoreApplication.instance().translate('ctmod_winetkg_valve_otherdistro', '''Custom Wine build for running Windows games, built with the Wine-tkg build system.''')}


class CtInstaller(TKGCtInstaller):

    BUFFER_SIZE = 65536
    CT_URL = 'https://api.github.com/repos/Frogging-Family/wine-tkg-git/releases'
    CT_INFO_URL = 'https://github.com/Frogging-Family/wine-tkg-git/releases/tag/'
    CT_WORKFLOW_URL = 'https://api.github.com/repos/Frogging-Family/wine-tkg-git/actions/workflows'
    CT_ARTIFACT_URL = 'https://api.github.com/repos/Frogging-Family/wine-tkg-git/actions/runs/{}/artifacts'
    CT_INFO_URL_CI = 'https://github.com/Frogging-Family/wine-tkg-git/actions/runs/'
    PROTON_PACKAGE_NAME = 'wine-valvexbe'
    TKG_EXTRACT_NAME = 'wine_tkg'

    p_download_progress_percent = 0
    download_progress_percent = Signal(int)

    def __init__(self, main_window = None):
        super().__init__(main_window)