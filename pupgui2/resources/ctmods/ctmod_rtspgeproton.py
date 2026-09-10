# pupgui2 compatibility tools module
# SpookySkeleton's Proton-RTSP
# Copyright (C) 2021 DavidoTek, partially based on AUNaseef's protonup

from PySide6.QtCore import QCoreApplication

from pupgui2.resources.ctmods.ctmod_00protonge import CtInstaller as ProtonGECTInstaller


CT_NAME = 'Proton-RTSP'
CT_LAUNCHERS = ['steam', 'heroicproton', 'bottles', 'lutris']
CT_DESCRIPTION = {'en': QCoreApplication.instance().translate('ctmod_rtspgeproton', '''Compatibility tool for Steam Play based on Wine and additional components.''')}


class CtInstaller(ProtonGECTInstaller):

    BUFFER_SIZE = 4096
    CT_URL = 'https://api.github.com/repos/SpookySkeletons/proton-rtsp/releases'
    CT_INFO_URL = 'https://github.com/SpookySkeletons/proton-rtsp/releases/tag/'

    def __init__(self, main_window = None):
        super().__init__(main_window)