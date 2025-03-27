# pupgui2 compatibility tools module
# Roberta
# Copyright (C) 2021 DavidoTek, partially based on AUNaseef's protonup

from PySide6.QtCore import QCoreApplication

from pupgui2.resources.ctmods.ctmod_00protonge import CtInstaller as GEProtonInstaller


CT_NAME = 'RTSP Proton'
CT_LAUNCHERS = ['steam', 'advmode']
CT_DESCRIPTION = {'en': QCoreApplication.instance().translate('ctmod_rtspgeproton', '''Fork of GE-Proton with enhanced Windows Media Foundation support.''')}


class CtInstaller(GEProtonInstaller):

    BUFFER_SIZE = 4096
    CT_URL = 'https://api.github.com/repos/SpookySkeletons/proton-ge-rtsp/releases'
    CT_INFO_URL = 'https://github.com/SpookySkeletons/proton-ge-rtsp/releases/tag/'

    def __init__(self, main_window = None):
        super().__init__(main_window)

