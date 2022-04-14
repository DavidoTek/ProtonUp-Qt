import os
import vdf
from steam.utils.appcache import parse_appinfo
from datastructures import SteamApp


def get_steam_app_list(steam_config_folder):
    """
    Returns a list of installed Steam apps and optionally game names and the compatibility tool they are using
    steam_config_folder = e.g. '~/.steam/root/config'
    Return Type: SteamApp[]
    """
    libraryfolders_vdf_file = os.path.join(os.path.expanduser(steam_config_folder), 'libraryfolders.vdf')
    config_vdf_file = os.path.join(os.path.expanduser(steam_config_folder), 'config.vdf')

    apps = []
    app_ids_str = []

    try:
        v = vdf.load(open(libraryfolders_vdf_file))
        c = vdf.load(open(config_vdf_file)).get('InstallConfigStore').get('Software').get('Valve').get('Steam').get('CompatToolMapping')
        for fid in v.get('libraryfolders'):
            if 'apps' not in v.get('libraryfolders').get(fid):
                continue
            for appid in v.get('libraryfolders').get(fid).get('apps'):
                app = SteamApp()
                app.app_id = int(appid)
                app.libraryfolder_id = fid
                if appid in c:
                    app.compat_tool = c.get(appid).get('name')
                apps.append(app)
                app_ids_str.append(str(appid))
            
            game_names = get_steam_game_names_by_ids(steam_config_folder, app_ids_str)
            for a in apps:
                if a.app_id in game_names:
                    a.game_name = game_names.get(a.app_id)
                    # Check if game or tool
                    if 'steamworks' not in a.game_name.lower() and 'proton' not in a.game_name.lower():
                        a.app_type = 'game'
    except Exception as e:
        print('Error: Could not get a list of all Steam apps:', e)
    
    return apps


def get_steam_game_list(steam_config_folder, compat_tool=''):
    """
    Returns a list of installed Steam games and which compatibility tools they are using.
    Specify compat_tool to only return games using the specified tool.
    Return Type: SteamApp[]
    """
    games = []
    apps = get_steam_app_list(steam_config_folder)

    for app in apps:
        if app.app_type == 'game':
            if compat_tool != '':
                if app.compat_tool != compat_tool:
                    continue
            games.append(app)

    return games


def get_steam_ctool_list(steam_config_folder, only_proton=False):
    """
    Returns a list of installed Steam compatibility tools (official tools).
    Return Type: SteamApp[]
    """
    ctools = []
    apps = get_steam_app_list(steam_config_folder)

    # TODO

    return ctools


def get_steam_game_names_by_ids(steam_config_folder, ids_str=[]):
    """
    Get steam game names by ids
    Return Type: dict
        Maps game id to game name
    """
    appinfo_file = os.path.join(os.path.expanduser(steam_config_folder), '../appcache/appinfo.vdf')
    appinfo_file = os.path.realpath(appinfo_file)
    ids = []
    for id in ids_str:
        ids.append(int(id))
    names = {}
    try:
        with open(appinfo_file, 'rb') as f:
            header, apps = parse_appinfo(f)
            for steam_app in apps:
                if steam_app.get('appid') in ids:
                    try:
                        names[steam_app.get('appid')] = steam_app.get('data').get('appinfo').get('common').get('name')
                    except:
                        names[steam_app.get('appid')] = ''
                    ids.remove(steam_app.get('appid'))
                if len(ids) == 0:
                    break
    except:
        pass
    return names


def steam_update_ctool(game:SteamApp, new_ctool=None, steam_config_folder=''):
    """
    Change compatibility tool for 'game_id' to 'new_ctool' in Steam config vdf
    Return Type: bool
    """
    config_vdf_file = os.path.join(os.path.expanduser(steam_config_folder), 'config.vdf')
    if not os.path.exists(config_vdf_file):
        return False
    
    game_id = game.app_id
    
    try:
        d = vdf.load(open(config_vdf_file))
        c = d.get('InstallConfigStore').get('Software').get('Valve').get('Steam').get('CompatToolMapping')

        if str(game_id) in c:
            if new_ctool is None:
                c.pop(str(game_id))
            else:
                c.get(str(game_id))['name'] = str(new_ctool)
        else:
            c[str(game_id)] = {"name": str(new_ctool), "config": "", "priority": "250"}
        
        vdf.dump(d, open(config_vdf_file, 'w'), pretty=True)
    except Exception as e:
        print('Error, could not update Steam compatibility tool to', new_ctool, 'for game',game_id, ':',
              e, ', vdf:', config_vdf_file)
        return False
    return True
