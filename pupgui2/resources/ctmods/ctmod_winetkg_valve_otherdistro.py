# pupgui2 compatibility tools module
# Proton-Tkg https://github.com/Frogging-Family/wine-tkg-git
# Copyright (C) 2022 DavidoTek, partially based on AUNaseef's protonup

from PySide6.QtCore import QCoreApplication, Signal

from pupgui2.resources.ctmods.ctmod_protontkg import CtInstaller as TKGCtInstaller  # Use ProtonTKg Ctmod as base


CT_NAME = 'Wine Tkg (Valve Wine)'
CT_LAUNCHERS = ['lutris', 'heroicwine']
CT_DESCRIPTION = {'en': QCoreApplication.instance().translate('ctmod_winetkg_valve_otherdistro', '''Custom Wine build for running Windows games, built with the Wine-tkg build system.''')}


class CtInstaller(TKGCtInstaller):

    BUFFER_SIZE = 65536
    PROTON_PACKAGE_NAME = 'wine-valvexbe'
    TKG_EXTRACT_NAME = 'wine_tkg'

    p_download_progress_percent = 0
    download_progress_percent = Signal(int)

    def __init__(self, main_window = None):
        super().__init__(main_window)
