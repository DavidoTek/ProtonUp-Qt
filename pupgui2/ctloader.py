import pkgutil
import importlib

from typing import List, Tuple

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMessageBox

from pupgui2.util import create_msgbox
from pupgui2.resources import ctmods


class CtLoader(QObject):
    
    ctmods = []
    ctobjs = []

    def __init__(self, main_window = None):
        self.main_window = main_window
        self.load_ctmods()

    def load_ctmods(self) -> bool:
        """
        Load ctmods
        Return Type: bool
        """
        failed_ctmods: List[Tuple[str, Exception]] = []
        for _, mod, _ in pkgutil.iter_modules(ctmods.__path__):
            if mod.startswith('ctmod_'):
                try:
                    ctmod = importlib.import_module(f'pupgui2.resources.ctmods.{mod}')
                    if ctmod is None:
                        failed_ctmods.append((mod.replace('ctmod_', ''), 'ctmod is None'))
                        print('Could not load ctmod', mod)
                        continue
                    self.ctmods.append(ctmod)
                    self.ctobjs.append({
                        'name': ctmod.CT_NAME,
                        'launchers': ctmod.CT_LAUNCHERS,
                        'description': ctmod.CT_DESCRIPTION,
                        'installer': ctmod.CtInstaller(main_window=self.main_window)
                    })
                    print('Loaded ctmod', ctmod.CT_NAME)
                except Exception as e:
                    failed_ctmods.append((mod.replace('ctmod_', ''), e))
                    print('Could not load ctmod', mod, ':', e)
        if len(failed_ctmods) > 0:
            detailed_text = ''
            ctmods_name = []
            for ctmod, e in failed_ctmods:
                ctmods_name.append(ctmod)
                detailed_text += f'{ctmod}: {e}\n'
            detailed_text = detailed_text.strip()
            create_msgbox(
                title=self.tr('Error!'),
                text=self.tr('Couldn\'t load the following compatibility tool(s):\n{TOOL_LIST}\n\nIf you believe this is an error, please report a bug on GitHub!')
                    .format(TOOL_LIST=', '.join(ctmods_name)),
                icon=QMessageBox.Warning,
                detailed_text=detailed_text
            )
        return True

    def get_ctmods(self, launcher=None, advanced_mode=True):
        """
        Get loaded ctmods, optionally sort by launcher
        Return Type: []
        """
        if launcher is None:
            return self.ctmods

        ctmods = [ctmod for ctmod in self.ctmods if launcher in ctmod.CT_LAUNCHERS and ('advmode' not in ctmod.CT_LAUNCHERS or advanced_mode)]

        return ctmods

    def get_ctobjs(self, launcher=None, advanced_mode=True):
        """
        Get loaded compatibility tools, optionally sort by launcher
        Return Type: List[dict]
        Content(s):
            'name', 'launchers', 'installer'
        """
        if launcher is None:
            return self.ctobjs

        ctobjs = []
        for ctobj in self.ctobjs:
            if launcher.get('launcher') in ctobj['launchers']:
                if 'advmode' in ctobj['launchers'] and not advanced_mode:
                    continue
                if 'native-only' in ctobj['launchers'] and launcher.get('type') != 'native':
                    continue
                ctobjs.append(ctobj)
        return ctobjs
