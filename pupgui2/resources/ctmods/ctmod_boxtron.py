# pupgui2 compatibility tools module
# Boxtron
# Copyright (C) 2021 DavidoTek, partially based on AUNaseef's protonup

from PySide6.QtCore import QCoreApplication

from pupgui2.resources.ctmods.ctmod_luxtorpeda import CtInstaller as LuxtorpedaInstaller


CT_NAME = 'Boxtron'
CT_LAUNCHERS = ['steam']
CT_DESCRIPTION = {'en': QCoreApplication.instance().translate('ctmod_boxtron', '''Steam Play compatibility tool to run DOS games using native Linux DOSBox.''')}


class CtInstaller(LuxtorpedaInstaller):

    BUFFER_SIZE = 4096
    CT_URL = 'https://api.github.com/repos/dreamer/boxtron/releases'
    CT_INFO_URL = 'https://github.com/dreamer/boxtron/releases/tag/'

    def __init__(self, main_window = None):
        super().__init__(main_window)
        self.extract_dir_name = 'boxtron'
        self.deps = [ 'doxbox', 'inotifywait', 'timidity' ]

    def is_system_compatible(self) -> bool:
        """
        Are the system requirements met?
        Return Type: bool
        """

        return super().is_system_compatible(ct_name = CT_NAME)
