import os
import vdf
from steam.utils.appcache import parse_appinfo


def get_steam_games_using_compat_tool(ver, steam_config_folder):
    """
    Get all games using a specified compatibility tool from Steam config.vdf
    'ver' should be the same as the internal name specified in compatibilitytool.vdf (Matches folder name in most cases)
    Return Type: str[]
    """
    config_vdf_file = os.path.join(os.path.expanduser(steam_config_folder), 'config.vdf')
    tools = []
    
    try:
        d = vdf.load(open(config_vdf_file))
        c = d.get('InstallConfigStore').get('Software').get('Valve').get('Steam').get('CompatToolMapping')

        for t in c:
            x = c.get(str(t))
            if x is None:
                continue
            if x.get('name') == ver:
                tools.append(t)
    except Exception as e:
        print('Error: Could not get list of Steam games using compat tool "' + str(ver) + '":', e)
        tools = ['-1']  # don't return empty list else compat tool would be listed as unused

    return tools


def get_steam_app_list(steam_config_folder):
    """
    Returns a list of installed Steam apps and optionally game names and the compatibility tool they are using
    steam_config_folder = e.g. '~/.steam/root/config'
    Return Type: dict[]
        Content: 'id', 'libraryfolder_id'
        Optional-Content: 'game_name', 'compat_tool', 'type'
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
                app = {'id': str(appid), 'libraryfolder_id': str(fid)}
                if appid in c:
                    app['compat_tool'] = c.get(appid).get('name')
                apps.append(app)
                app_ids_str.append(str(appid))
            
            game_names = get_steam_game_names_by_ids(steam_config_folder, app_ids_str)
            for a in apps:
                if int(a.get('id', -1)) in game_names:
                    a['game_name'] = game_names.get(int(a.get('id', -1)))
                    # Check if game or tool
                    if 'steamworks' not in a['game_name'].lower() and 'proton' not in a['game_name'].lower():
                        a['type'] = 'game'
    except Exception as e:
        print('Error: Could not get a list of all Steam apps:', e)
    
    return apps


def get_steam_game_list(steam_config_folder):
    """
    Returns a list of installed Steam games and which compatibility tools they are using.
    Return Type: dict[]
        Content: 'id', 'compat_tool', 'game_name'
    """
    games = []
    apps = get_steam_app_list(steam_config_folder)

    for app in apps:
        if app.get('type') == 'game':
            games.append(app)

    return games


def get_steam_game_names_by_ids(steam_config_folder, ids_str=[]):
    """
    Get steam game names by ids
    Return Type: dict[]
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


def steam_update_ctool(game_id=0, new_ctool=None, steam_config_folder=''):
    """
    Change compatibility tool for 'game_id' to 'new_ctool' in Steam config vdf
    Return Type: bool
    """
    config_vdf_file = os.path.join(os.path.expanduser(steam_config_folder), 'config.vdf')
    if not os.path.exists(config_vdf_file):
        return False
    
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
