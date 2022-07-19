import os
import json
from typing import Dict, List
import vdf
from steam.utils.appcache import parse_appinfo

from .datastructures import SteamApp, AWACYStatus
from .constants import LOCAL_AWACY_GAME_LIST


_cached_app_list = []
_cached_steam_ctool_id_map = None


def get_steam_app_list(steam_config_folder: str, cached=False) -> List[SteamApp]:
    """
    Returns a list of installed Steam apps and optionally game names and the compatibility tool they are using
    steam_config_folder = e.g. '~/.steam/root/config'
    Return Type: List[SteamApp]
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
                ct = c.get(appid)
                if ct:
                    app.compat_tool = ct.get('name')
                apps.append(app)
                app_ids_str.append(str(appid))
            apps = update_steamapp_info(steam_config_folder, apps)
            apps = update_steamapp_awacystatus(apps)
    except Exception as e:
        print('Error: Could not get a list of all Steam apps:', e)

    _cached_app_list = apps
    return apps


def get_steam_game_list(steam_config_folder: str, compat_tool='', cached=False) -> List[SteamApp]:
    """
    Returns a list of installed Steam games and which compatibility tools they are using.
    Specify compat_tool to only return games using the specified tool.
    Return Type: List[SteamApp]
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


def get_steam_ctool_list(steam_config_folder: str, only_proton=False, cached=False) -> List[SteamApp]:
    """
    Returns a list of installed Steam compatibility tools (official tools).
    Return Type: List[SteamApp]
    """
    ctools = []
    apps = get_steam_app_list(steam_config_folder, cached=cached)
    ctool_map = _get_steam_ctool_info(steam_config_folder)

    for app in apps:
        ct = ctool_map.get(app.app_id)
        if ct:
            app.ctool_name = ct.get('name')
            app.ctool_from_oslist = ct.get('from_oslist')
            if only_proton and ct.get('from_oslist') != 'windows':
                continue
            ctools.append(app)

    return ctools


def _get_steam_ctool_info(steam_config_folder: str) -> Dict[str, Dict[str, str]]:
    """
    Returns a dict that maps the compatibility tool appid to tool info (name e.g. 'proton_7' and from_oslist)
    Return Type: Dict[str, dict]
        Contents: appid str -> {'name', 'from_oslist'}
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


def update_steamapp_info(steam_config_folder: str, steamapp_list: List[SteamApp]) -> List[SteamApp]:
    """
    Get Steam game names and information for provided SteamApps
    Return Type: List[SteamApp]
    """
    appinfo_file = os.path.join(os.path.expanduser(steam_config_folder), '../appcache/appinfo.vdf')
    appinfo_file = os.path.realpath(appinfo_file)
    sapps = {}
    for app in steamapp_list:
        sapps[app.get_app_id_str()] = app
    cnt = 0
    try:
        ctool_map = _get_steam_ctool_info(steam_config_folder)
        with open(appinfo_file, 'rb') as f:
            header, apps = parse_appinfo(f)
            for steam_app in apps:
                appid_str = str(steam_app.get('appid'))
                a = sapps.get(appid_str)
                if a:
                    try:
                        a.game_name = steam_app.get('data').get('appinfo').get('common').get('name')
                    except:
                        a.game_name = ''
                    try:
                        a.deck_compatibility = steam_app.get('data').get('appinfo').get('common').get('steam_deck_compatibility')
                    except:
                        pass
                    if steam_app.get('appid') not in ctool_map and 'steamworks' not in a.game_name.lower():
                        a.app_type = 'game'
                    cnt += 1
                if cnt == len(sapps):
                    break
    except:
        pass
    return list(sapps.values())


def update_steamapp_awacystatus(steamapp_list: List[SteamApp]) -> List[SteamApp]:  # Download file in thread on start...
    """
    Set the areweanticheatyet.com for the games.
    Return Type: List[SteamApp]
    """
    if not os.path.exists(LOCAL_AWACY_GAME_LIST):
        return steamapp_list

    try:
        f = open(LOCAL_AWACY_GAME_LIST, 'r')
        gm = {}
        for g in json.load(f):
            gm[g.get('name')] = g.get('status')
        f.close()

        for app in steamapp_list:
            if app.game_name != '' and app.game_name in gm:
                status = gm[app.game_name]
                if status == 'Supported':
                    app.awacy_status = AWACYStatus.ASUPPORTED
                elif status == 'Planned':
                    app.awacy_status = AWACYStatus.PLANNED
                elif status == 'Running':
                    app.awacy_status = AWACYStatus.RUNNING
                elif status == 'Broken':
                    app.awacy_status = AWACYStatus.BROKEN
                elif status == 'Denied':
                    app.awacy_status = AWACYStatus.DENIED
    except Exception as e:
        print('Error updating the areweanticheatyet.com status:', e)
        return steamapp_list

    return steamapp_list


def steam_update_ctool(game: SteamApp, new_ctool=None, steam_config_folder='') -> bool:
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


def steam_update_ctools(games: Dict[SteamApp, str], steam_config_folder='') -> bool:
    """
    Change compatibility tool for multiple games in Steam config vdf.
    Return Type: bool
    """
    config_vdf_file = os.path.join(os.path.expanduser(steam_config_folder), 'config.vdf')
    if not os.path.exists(config_vdf_file):
        return False

    try:
        d = vdf.load(open(config_vdf_file))
        c = d.get('InstallConfigStore').get('Software').get('Valve').get('Steam').get('CompatToolMapping')
        
        for game in games:
            game_id = game.app_id
            new_ctool = games[game]

            if str(game_id) in c:
                if new_ctool is None:
                    c.pop(str(game_id))
                else:
                    c.get(str(game_id))['name'] = str(new_ctool)
            else:
                c[str(game_id)] = {"name": str(new_ctool), "config": "", "priority": "250"}

        vdf.dump(d, open(config_vdf_file, 'w'), pretty=True)
    except Exception as e:
        print('Error, could not update Steam compatibility tools:', e, ', vdf:', config_vdf_file)
        return False
    return True


def is_steam_running() -> bool:
    """
    Returns True if the Steam client is running, False otherwise
    Return Type: bool
    """
    try:
        procs = os.listdir('/proc')
        for proc in procs:
            exe = os.path.join('/proc', proc, 'exe')
            if os.path.exists(exe):
                if 'steam' in os.readlink(exe):
                    return True
    except:
        pass
    return False
