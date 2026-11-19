# pupgui2 compatibility tools module
# SpookySkeleton's Proton-RTSP
# Copyright (C) 2021 DavidoTek, partially based on AUNaseef's protonup

from PySide6.QtCore import QCoreApplication

from pupgui2.resources.ctmods.ctmod_00protonge import CtInstaller as GEProtonInstaller


CT_NAME = 'Proton-RTSP'
CT_LAUNCHERS = ['steam', 'heroicproton', 'bottles', 'lutris', 'advmode']
CT_DESCRIPTION = {'en': QCoreApplication.instance().translate('ctmod_rtspgeproton', '''Proton build for VRChat with livestream (RTSP) and media playback support, based on Proton Experimental.<br/><br/><b>Steam: after installing, open steam://unlockh264/ once, otherwise most videos will fail to play.</b> Run <i>steam steam://unlockh264/</i>, or <i>flatpak run com.valvesoftware.Steam steam://unlockh264/</i> for Flatpak Steam.<br/><br/>If YouTube videos still fail, try VRCVideoCacher.''')}


class CtInstaller(GEProtonInstaller):

    BUFFER_SIZE = 4096
    CT_URL = 'https://api.github.com/repos/SpookySkeletons/proton-rtsp/releases'
    CT_INFO_URL = 'https://github.com/SpookySkeletons/proton-rtsp/releases/tag/'

    def __init__(self, main_window = None):
        super().__init__(main_window)