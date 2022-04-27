import os
import vdf
from steam.utils.appcache import parse_appinfo
from datastructures import SteamApp


_cached_app_list = []
_cached_steam_ctool_id_map = None


def get_steam_app_list(steam_config_folder, cached=False):
    """
    Returns a list of installed Steam apps and optionally game names and the compatibility tool they are using
    steam_config_folder = e.g. '~/.steam/root/config'
    Return Type: SteamApp[]
    """
    global _cached_app_list

    if cached and _cached_app_list != []:
        return _cached_app_list

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
            apps = update_steamapp_info(steam_config_folder, apps)
    except Exception as e:
        print('Error: Could not get a list of all Steam apps:', e)
    
    _cached_app_list = apps
    return apps


def get_steam_game_list(steam_config_folder, compat_tool='', cached=False):
    """
    Returns a list of installed Steam games and which compatibility tools they are using.
    Specify compat_tool to only return games using the specified tool.
    Return Type: SteamApp[]
    """
    games = []
    apps = get_steam_app_list(steam_config_folder, cached=cached)

    for app in apps:
        if app.app_type == 'game':
            if compat_tool != '':
                if app.compat_tool != compat_tool:
                    continue
            games.append(app)

    return games


def get_steam_ctool_list(steam_config_folder, only_proton=False, cached=False):
    """
    Returns a list of installed Steam compatibility tools (official tools).
    Return Type: SteamApp[]
    """
    ctools = []
    apps = get_steam_app_list(steam_config_folder, cached=cached)
    ctool_map = _get_steam_ctool_info(steam_config_folder)

    for app in apps:
        if app.app_id in ctool_map:
            app.ctool_name = ctool_map.get(app.app_id).get('name')
            app.ctool_from_oslist = ctool_map.get(app.app_id).get('from_oslist')
            if only_proton and ctool_map.get(app.app_id).get('from_oslist') != 'windows':
                continue
            ctools.append(app)

    return ctools


def _get_steam_ctool_info(steam_config_folder):
    """
    Returns a dict that maps the compatibility tool appid to tool info (name e.g. 'proton_7' and from_oslist)
    Return Type: dict.dict
        Contents: name, from_oslist
    """
    global _cached_steam_ctool_id_map

    if _cached_steam_ctool_id_map is not None:
        return _cached_steam_ctool_id_map

    appinfo_file = os.path.join(os.path.expanduser(steam_config_folder), '../appcache/appinfo.vdf')
    appinfo_file = os.path.realpath(appinfo_file)

    ctool_map = {}
    compat_tools = None
    try:
        with open(appinfo_file, 'rb') as f:
            header, apps = parse_appinfo(f)
            for steam_app in apps:
                if steam_app.get('appid') == 891390:
                    compat_tools = steam_app.get('data').get('appinfo').get('extended').get('compat_tools')
                    break
    except:
        pass
    finally:
        for t in compat_tools:
            ctool_map[compat_tools.get(t).get('appid')] = {'name': t, 'from_oslist': compat_tools.get(t).get('from_oslist')}
    
    _cached_steam_ctool_id_map = ctool_map
    return ctool_map


def update_steamapp_info(steam_config_folder, steamapp_list):
    """
    Get Steam game names and information for provided SteamApps
    Return Type: SteamApp list
    """
    appinfo_file = os.path.join(os.path.expanduser(steam_config_folder), '../appcache/appinfo.vdf')
    appinfo_file = os.path.realpath(appinfo_file)
    sapps = {}
    for app in steamapp_list:
        sapps[app.get_app_id_str()] = app
    cnt = 0
    try:
        with open(appinfo_file, 'rb') as f:
            header, apps = parse_appinfo(f)
            for steam_app in apps:
                appid_str = str(steam_app.get('appid'))
                if appid_str in sapps:
                    a = sapps[appid_str]
                    try:
                        a.game_name = steam_app.get('data').get('appinfo').get('common').get('name')
                    except:
                        a.game_name = ''
                    try:
                        a.deck_compatibility = steam_app.get('data').get('appinfo').get('common').get('steam_deck_compatibility')
                    except:
                        pass
                    if 'steamworks' not in a.game_name.lower() and 'proton' not in a.game_name.lower():
                        a.app_type = 'game'
                    cnt += 1
                if cnt == len(sapps):
                    break
    except:
        pass
    return list(sapps.values())


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
