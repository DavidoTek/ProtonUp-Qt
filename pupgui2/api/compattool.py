import enum
from typing import List

from .launcher import Launcher


class CompatToolStatus(enum.Enum):
    INSTALLED = enum.auto()  # tool is installed on the system (e.g. get_installed_versions)
    AVAILABLE = enum.auto()  # tool is available to download (e.g. fetch_releases)
    TO_BE_INSTALLED = enum.auto()  # same as AVAILABLE, but with launcher/install_dir populated (e.g. argument for get_tool)


class CompatToolType(enum.Enum):
    UNKNOWN = 0
    CUSTOM = 10   # user installed ctool (e.g. GE-Proton in compatibilitytools.d)
    STEAM_CT = 20 # Steam installed compatibility tool (e.g. Proton in steamapps)
    STEAM_RT = 21 # Steam Runtime (e.g. BattlEye/EAC Runtime in steamapps)


class CompatTool:

    def __init__(self, name: str, version: str, ctinstaller, install_dir: str, folder_name: str, launcher: Launcher=None, status: CompatToolStatus=None, display_name: str=None, ct_type: CompatToolType=None) -> None:
        """
        Defines an abstract compatibility tool for ProtonUp-Qt

        Parameters
        ----------
        name : str
            Internal name of the compatibility tool
        version : str
            Version of the compatibility tool
        ctinstaller : CtInstaller
            CtInstaller the compatibility tool belongs to
        install_dir : str
            Install directory. Example: ~/.steam/root/compatibilitytools.d
        folder_name : str
            Name of the compatibility tool folder. Example: GE-Proton7-41
        launcher : Launcher (optinal)
            Launcher for which the compatibility tools is installed
        status : CompatToolStatus (optional)
            Install status of the compatibilty tool
        display_name : str (optional)
            Display name of the compatibility tool. If not specified, folder_name will be used
        ct_type : CompatToolType(optional)
            See CompatToolType
        """
        self.name = name
        self.version = version
        self.ctinstaller = ctinstaller
        self.install_dir = install_dir
        self.folder_name = folder_name
        self.display_name = display_name
        self.launcher = launcher
        self.status = status
        self.ct_type = ct_type
        self.games = []  # can be of type SteamApp or LutrisGame

    def get_internal_name(self) -> str:
        return self.name

    def get_version(self) -> str:
        return self.version

    def get_ctinstaller(self):
        return self.ctinstaller

    def get_install_dir(self) -> str:
        return self.install_dir

    def get_folder_name(self) -> str:
        return self.folder_name

    def get_displayname(self) -> str:
        if self.display_name:
            return self.display_name
        else:
            return self.folder_name

    def get_launcher(self) -> Launcher:
        return self.launcher

    def get_status(self) -> CompatToolStatus:
        return self.status
    
    def get_ct_type(self) -> CompatToolType:
        return self.ct_type

    def add_games(self, games: List) -> List:
        self.games += games

    def get_game_count(self) -> int:
        return len(self.games)

    def uninstall(self) -> bool:
        return self.ctinstaller.uninstall_tool(self)
