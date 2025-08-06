# pupgui2 compatibility tools module
# Etaash-mathamsetty's Proton-EM
# Copyright (C) 2025 DavidoTek, partially based on AUNaseef's protonup


from PySide6.QtCore import QCoreApplication

from pupgui2.resources.ctmods.ctmod_00protonge import CtInstaller as GEProtonInstaller


CT_NAME = 'Proton-EM'
CT_LAUNCHERS: list[str] = ['steam', 'lutris', 'heroicproton', 'bottles', 'advmode']
CT_DESCRIPTION: dict[str, str] = {'en': QCoreApplication.instance().translate('ctmod_protonem', '''Fork of Valve's Proton with Wine-Wayland and AMD FidelityFX Super Resolution 4 patches.''',),}


class CtInstaller(GEProtonInstaller):

    CT_URL = 'https://api.github.com/repos/Etaash-mathamsetty/Proton/releases'
    CT_INFO_URL = 'https://github.com/Etaash-mathamsetty/Proton/releases/tag/'

    def __init__(self, main_window = None):
        super().__init__(main_window)

        self.release_format = 'tar.xz'
