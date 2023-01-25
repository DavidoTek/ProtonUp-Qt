import os
from enum import Enum
import vdf
import yaml


class SteamDeckCompatEnum(Enum):
    UNKNOWN = 0
    UNSUPPORTED = 1
    PLAYABLE = 2
    VERIFIED = 3


class AWACYStatus(Enum):
    UNKNOWN = 0
    DENIED = 4
    ASUPPORTED = 5
    PLANNED = 6
    RUNNING = 7
    BROKEN = 8


class CTType(Enum):
    UNKNOWN = 0
    CUSTOM = 10   # user installed ctool (e.g. GE-Proton in compatibilitytools.d)
    STEAM_CT = 20 # Steam installed compatibility tool (e.g. Proton in steamapps)
    STEAM_RT = 21 # Steam Runtime (e.g. BattlEye/EAC Runtime in steamapps)


class MsgBoxType(Enum):
    OK = 0
    OK_CANCEL = 1
    OK_CB = 2
    OK_CANCEL_CB = 3
    OK_CB_CHECKED = 4
    OK_CANCEL_CB_CHECKED = 5


class MsgBoxResult:
    BUTTON_OK = 0
    BUTTON_CANCEL = 1

    msgbox_type : MsgBoxType = None
    button_clicked = None
    is_checked : bool = None


class SteamApp:
    app_id = -1
    libraryfolder_id = -1
    libraryfolder_path = ''
    shortcut_id = -1  # Will be a number >=0 if it is a Non-Steam shortcut
    shortcut_path = ''
    game_name = ''
    compat_tool = ''
    app_type = ''
    deck_compatibility = {}
    ctool_name = ''  # Steam's internal compatiblity tool name, e.g. 'proton_7'
    ctool_from_oslist = ''
    awacy_status = AWACYStatus.UNKNOWN  # areweanticheatyet.com Status
    protondb_summary = {}  # protondb status summary from JSON file

    def get_app_id_str(self) -> str:
        return str(self.app_id)

    def get_libraryfolder_id_str(self) -> str:
        return str(self.libraryfolder_id)

    def get_deck_compat_category(self) -> SteamDeckCompatEnum:
        try:
            return SteamDeckCompatEnum(self.deck_compatibility.get('category'))
        except:
            return SteamDeckCompatEnum.UNKNOWN

    def get_deck_recommended_tool(self) -> str:
        try:
            return self.deck_compatibility.get('configuration').get('recommended_runtime', '')
        except:
            return ''

    def get_shortcut_id_str(self) -> str:
        return str(self.shortcut_id)
    
class BasicCompatTool:
    displayname = ''
    version = ''
    no_games = -1
    install_dir = ''
    install_folder = ''
    ct_type = CTType.UNKNOWN

    def __init__(self, displayname, install_dir, install_folder, ct_type = CTType.UNKNOWN) -> None:
        self.displayname = displayname
        self.install_dir = install_dir
        self.install_folder = install_folder
        self.ct_type = ct_type

    def set_version(self, ver : str) -> None:
        self.version = ver

    def get_displayname(self, unused_tr='unused') -> str:
        """ Returns the display name, e.g. GE-Proton7-17 or luxtorpeda v57 """
        displayname = self.displayname
        if self.version != '':
            displayname += f' {self.version}'
        if self.no_games == 0:
            displayname += f' ({unused_tr})'
        return displayname

    def get_internal_name(self) -> str:
        """
        Returns the internal name if available, e.g. Proton-stl.
        If unavailable, returns the displayname
        """
        compat_tool_vdf_path = os.path.join(self.install_dir, self.install_folder, 'compatibilitytool.vdf')
        if os.path.exists(compat_tool_vdf_path):
            compat_tool_vdf = vdf.load(open(compat_tool_vdf_path))
            if 'compatibilitytools' in  compat_tool_vdf and 'compat_tools' in compat_tool_vdf['compatibilitytools']:
                return list(compat_tool_vdf['compatibilitytools']['compat_tools'].keys())[0]

        return self.displayname

    def get_install_dir(self) -> str:
        """ Returns the install directory, e.g. .../compatibilitytools.d/ """
        return os.path.normpath(self.install_dir)

    def get_install_folder(self) -> str:
        """ Returns the install folder, e.g. GE-Proton7-17 or luxtorpeda """
        return self.install_folder


class LutrisGame:
    slug = ''
    name = ''
    runner = ''
    installer_slug = ''
    installed_at = 0

    install_loc = None

    def get_game_config(self):
        lutris_config_dir = self.install_loc.get('config_dir')
        if not lutris_config_dir:
            return {}
    
        # search a *.yml game configuration file that contains either the install_slug+installed_at or, if not found, the game slug
        fn = ''
        for game_cfg_file in os.listdir(os.path.join(os.path.expanduser(lutris_config_dir), 'games')):
            if str(self.installer_slug) in game_cfg_file and str(self.installed_at) in game_cfg_file:
                fn = game_cfg_file
                break
        else:
            for game_cfg_file in os.listdir(os.path.join(os.path.expanduser(lutris_config_dir), 'games')):
                if self.slug in game_cfg_file:
                    fn = game_cfg_file
                    break

        lutris_game_cfg = os.path.join(os.path.expanduser(lutris_config_dir), 'games', fn)
        if not os.path.exists(lutris_game_cfg):
            return {}
        with open(lutris_game_cfg, 'r') as f:
            return yaml.safe_load(f)
