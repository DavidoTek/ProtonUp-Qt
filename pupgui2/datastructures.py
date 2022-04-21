from enum import Enum


class SteamDeckCompatEnum(Enum):
    UNKNOWN = 0
    UNSUPPORTED = 1
    PLAYABLE = 2
    VERIFIED = 3


class SteamApp:
    app_id = -1
    libraryfolder_id = -1
    game_name = ''
    compat_tool = ''
    app_type = ''
    deck_compatibility = {}

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
