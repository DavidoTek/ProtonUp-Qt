# pupgui2 compatibility tools module
# Boxtron
# Copyright (C) 2021 DavidoTek, partially based on AUNaseef's protonup

from PySide6.QtCore import QCoreApplication

from pupgui2.util import host_which
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

    def is_system_compatible(self):
        """
        Are the system requirements met?
        Return Type: bool
        """

        # Could be a generic method in future? Not sure how re-usable this is between ctmods
        tr_missing = QCoreApplication.instance().translate('ctmod_boxtron', 'missing')
        tr_found = QCoreApplication.instance().translate('ctmod_boxtron', 'found')
        msg_tr_title = QCoreApplication.instance().translate('ctmod_boxtron', 'Missing dependencies!')

        if all(host_which(dep) for dep in self.deps):
            return True
        msg = QCoreApplication.instance().translate('ctmod_boxtron', 'You need {DEPS} for Boxtron.'.format(DEPS=', '.join(self.deps))) + '\n\n'
        msg += '\n'.join(f'{dep_name}: {tr_missing if host_which(dep_name) else tr_found}' for dep_name in self.deps)
        msg += '\n\n' + QCoreApplication.instance().translate('ctmod_boxtron', 'Will continue installing Boxtron anyway.')

        self._emit_missing_dependencies(msg_tr_title, msg)

        return True  # install Boxtron anyway
