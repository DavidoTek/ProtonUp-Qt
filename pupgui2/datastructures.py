from enum import Enum


class SteamDeckCompatEnum(Enum):
    UNKNOWN = 0
    UNSUPPORTED = 1
    PLAYABLE = 2
    VERIFIED = 3


class AWACYStatus(Enum):
    UNKNOWN = 0
    UNCONFIRMED = 1
    CONFIRMED = 2
    SUPPORTED = 3
    DENIED = 4


class SteamApp:
    app_id = -1
    libraryfolder_id = -1
    game_name = ''
    compat_tool = ''
    app_type = ''
    deck_compatibility = {}
    ctool_name = ''  # Steam's internal compatiblity tool name, e.g. 'proton_7'
    ctool_from_oslist = ''
    awacy_status = AWACYStatus.UNKNOWN  # areweanticheatyet.com Status

    def get_app_id_str(self):
        return str(self.app_id)
    
    def get_libraryfolder_id_str(self):
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
