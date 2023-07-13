# pupgui2 compatibility tools module
# Proton-Tkg https://github.com/Frogging-Family/wine-tkg-git
# Copyright (C) 2022 DavidoTek, partially based on AUNaseef's protonup

from PySide6.QtCore import QCoreApplication

from pupgui2.resources.ctmods.ctmod_protontkg import CtInstaller as TKGCtInstaller  # Use ProtonTKg Ctmod as base


CT_NAME = 'Wine Tkg (Vanilla Wine)'
CT_LAUNCHERS = ['lutris', 'heroicwine', 'advmode']
CT_DESCRIPTION = {'en': QCoreApplication.instance().translate('ctmod_winetkg_vanilla_ubuntu', '''Custom Wine build for running Windows games, built with the Wine-tkg build system.''')}


class CtInstaller(TKGCtInstaller):

    PROTON_PACKAGE_NAME = 'wine-ubuntu.yml'

    def __init__(self, main_window = None):
        super().__init__(main_window)
