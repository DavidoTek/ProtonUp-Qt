# pupgui2 compatibility tools module
# vkd3d-lutris for Lutris: https://github.com/lutris/vkd3d/
# Copyright (C) 2022 DavidoTek, partially based on AUNaseef's protonup

from PySide6.QtCore import QCoreApplication

from pupgui2.resources.ctmods.ctmod_vkd3dproton import CtInstaller as VKD3DInstaller


CT_NAME = 'vkd3d-lutris'
CT_LAUNCHERS = ['lutris', 'heroicwine', 'heroicproton']
CT_DESCRIPTION = {'en': QCoreApplication.instance().translate('ctmod_vkd3d-lutris', '''Fork of Wine's VKD3D which aims to implement the full Direct3D 12 API on top of Vulkan (Lutris Release).<br/><br/>https://github.com/lutris/docs/blob/master/HowToDXVK.md''')}

class CtInstaller(VKD3DInstaller):

    CT_URL = 'https://api.github.com/repos/lutris/vkd3d/releases'
    CT_INFO_URL = 'https://github.com/lutris/vkd3d/releases/tag/'

    def __init__(self, main_window = None):
        super().__init__(main_window)
