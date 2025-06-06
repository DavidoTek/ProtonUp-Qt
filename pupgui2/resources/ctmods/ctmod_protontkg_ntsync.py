# pupgui2 compatibility tools module
# Proton-Tkg https://github.com/Frogging-Family/wine-tkg-git
# Copyright (C) 2022 DavidoTek, partially based on AUNaseef's protonup

from PySide6.QtCore import QCoreApplication

from pupgui2.resources.ctmods.ctmod_protontkg import CtInstaller as TKGCtInstaller  # Use ProtonTKg Ctmod as base


CT_NAME = 'Proton Tkg (Wine Master NTSYNC)'
CT_LAUNCHERS = ['steam', 'heroicproton', 'advmode']
CT_DESCRIPTION = {'en': QCoreApplication.instance().translate('ctmod_protontkg_winemaster_ntsync', '''Custom Proton build for running Windows games, built with the Wine-tkg build system.
<br/>
<br/>
This build is based on <b>Wine Master</b> and includes the <b>NTSYNC</b> patches (Requires a Kernel with NTSYNC support).''')}


class CtInstaller(TKGCtInstaller):

    PROTON_PACKAGE_NAME = 'proton-arch-ntsync-nopackage.yml'

    def __init__(self, main_window = None):
        super().__init__(main_window)
