import os
import importlib.util


class CtLoader:
    
    ctmods = []
    ctobjs = []

    def __init__(self):
        pass
    
    def load_ctmods(self, ctmod_dir):
        """
        Load ctmods from ctmod_dir
        Return Type: bool
        """
        if not os.path.exists(ctmod_dir):
            return False
        files = os.listdir(ctmod_dir)
        for file in files:
            if file.startswith('ctmod_'):
                try:
                    ctmod_spec = importlib.util.spec_from_file_location(file.replace('.py', ''), os.path.join(ctmod_dir, file))
                    ctmod = importlib.util.module_from_spec(ctmod_spec)
                    ctmod_spec.loader.exec_module(ctmod)
                except:
                    print('Could not load ctmod', file)
                finally:
                    self.ctmods.append(ctmod)
                    self.ctobjs.append({
                        'name': ctmod.CT_NAME,
                        'launchers': ctmod.CT_LAUNCHERS,
                        'installer': ctmod.CtInstaller()
                    })
                    print('Loaded ctmod', ctmod.CT_NAME)
        return True
    
    def get_ctmods(self, launcher=None):
        """
        Get loaded ctmods, optionally sort by launcher
        Return Type: []
        """
        if launcher == None:
            return self.ctmods

        ctmods = []
        for ctmod in self.ctmods:
            if launcher in ctmod.CT_LAUNCHERS:
                ctmods.append(ctmod)
        return ctmods
    
    def get_ctobjs(self, launcher=None):
        """
        Get loaded ctmods, optionally sort by launcher
        Return Type: []
        """
        if launcher == None:
            return self.ctobjs

        ctobjs = []
        for ctobj in self.ctobjs:
            if launcher in ctobj['launchers']:
                ctobjs.append(ctobj)
        return ctobjs
