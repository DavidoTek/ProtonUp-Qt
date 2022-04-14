class SteamApp:
    app_id = -1
    libraryfolder_id = -1
    game_name = ''
    compat_tool = ''
    app_type = ''
    deck_compatibility = 0

    def get_app_id_str(self):
        return str(self.app_id)
    
    def get_libraryfolder_id_str(self):
        return str(self.libraryfolder_id)
