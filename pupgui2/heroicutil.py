import os
import json
import re
import tempfile

from typing import Any

from pupgui2.datastructures import HeroicGame
from pupgui2.datastructures import HeroicCompatTool
from pupgui2.constants import EPIC_STORE_URL


def get_heroic_game_list(heroic_path: str) -> list[HeroicGame]:
    """
    Returns a list of installed games for Heroic Games at 'heroic_path' (e.g., '~/.config/heroic', '~/.var/app/com.heroicgameslauncher.hgl/config/heroic')
    Return Type: list[HeroicGame]
    """

    if not os.path.isdir(heroic_path):
        return []

    # "Nile" refers to Amazon Games
    store_paths: list[str] = [ os.path.join(heroic_path, 'sideload_apps', 'library.json'), os.path.join(heroic_path, 'store_cache', 'gog_library.json'), os.path.join(heroic_path, 'store_cache', 'nile_library.json') ]
    legendary_path: str = os.path.join(heroic_path, 'legendaryConfig', 'legendary', 'installed.json')

    games_json: list[dict[str, Any]] = []
    for sp in store_paths:
        if os.path.isfile(sp):
            games_json_file: dict[str, Any] = json.load(open(sp))

            # 'games' and 'library' is a JSON array containing objects representing each game
            games_json += games_json_file.get('games', [])  # GOG + sideload use 'games' as top-level object
            games_json += games_json_file.get('library', [])  # Nile uses 'library' as top-level object

    hgs: list[HeroicGame] = []
    for game in games_json:
        game: dict[str, Any]
        hg = HeroicGame()

        hg.runner = game.get('runner', '')
        hg.app_name = game.get('app_name', '')
        hg.title = game.get('title', '')
        hg.developer = game.get('developer', '')
        hg.heroic_path = heroic_path
        # Sideloaded games uses folder_name as their full install path, GOG games store a folder_name but this is *just* their install folder name, Nile uses `"install": [ "install_path": "/foo/bar/foobar" ]`
        # Prioritise getting install_path for GOG games as this is the GOG game equivalent to 'folder_name'
        hg.install_path = get_gog_installed_game_entry(hg).get('install_path', '') or game.get('install', {}).get('install_path', '') or game.get('browserUrl', '') or game.get('folder_name', '')
        hg.store_url = game.get('store_url', '')
        hg.art_cover = game.get('art_cover', '')  # May need to replace path if it has 'file:///app/blah in name - See example in #168
        hg.art_square = game.get('art_square', '')
        hg.is_installed = game.get('is_installed', False) or is_gog_game_installed(hg)  # Some installed gog games may not be marked properly in library.json, so cross-reference with installed.json
        hg.wine_info = hg.get_game_config().get('wineVersion', {})
        # Sideloaded games store platform in its library.json (it has no installed.json) under the 'install' object
        # GOG games store the platform for the version of the installed game in `installed.json` (as GOG games can target multiple platforms, installed will show if the user has the Windows or Linux version)
        hg.platform = get_gog_installed_game_entry(hg).get('platform', '').capitalize() if hg.runner.lower() == 'gog' else game.get('install', {}).get('platform', '').capitalize()  # Capitalize ensures consistency
        # GOG and Epic store the exe name on its own, but sideloaded stores the full path, so for consistency get the basename for sideloaded apps
        # Native GOG games seem to just store the 'executable' as 'start.sh' script
        hg.executable = get_gog_game_executable(hg) if hg.runner.lower() == 'gog' else os.path.basename(game.get('install', {}).get('executable', ''))
        hg.is_dlc = game.get('install', {}).get('is_dlc', False)

        hgs.append(hg)

    # Legendary Games uses a separate structure, so build separately
    if os.path.isfile(legendary_path):
        legendary_json: dict[str, Any] = json.load(open(legendary_path))
        for app_name, game_data in legendary_json.items():
            lg = HeroicGame()

            lg.runner = 'legendary'  # Hardcoded 
            lg.app_name = app_name  # installed.json key is always the app_name 
            lg.title = game_data.get('title', '')
            lg.developer = ''  # Not stored or stored elsewhere?
            lg.heroic_path = heroic_path
            lg.install_path = game_data.get('install_path', '')
            lg.store_url = f'{EPIC_STORE_URL}{re.sub("[^a-zA-Z0-9]", "-", lg.title.lower())}'
            lg.art_cover = ''  # Not stored or stored elsewhere?
            lg.art_square = ''  # Not stored or stored elsewhere?
            lg.is_installed = True  # Games in Legendary `installed.json` should always be installed
            lg.wine_info = lg.get_game_config().get('wineVersion', {})  # Mirrors above, Legendary games should use the same GameConfig json structure
            lg.platform = game_data.get('platform', '').capitalize()  # Legendary stores this in `installed.json` and like GOG this stores the platform for the version the user downloaded
            lg.executable = game_data.get('executable', '')
            lg.is_dlc = game_data.get('is_dlc', False)  # If not set for some reason, assume its not DLC

            hgs.append(lg)

    return hgs


def is_heroic_launcher(launcher: str) -> bool:
    """ Returns True if the supplied launcher name is a valid name for Heroic Games Launcher, e.g. "heroicwine" """

    return any(hero in launcher for hero in ['heroicwine', 'heroicproton'])

def get_heroic_ctool_list(heroic_path: str) -> list[str]:
    """
    Returns the names of installed compatibility tools for Heroic at 'heroic_path' (e.g., '~/.config/heroic', '~/.var/app/com.heroicgameslauncher.hgl/config/heroic')
    Searches '<heroic_path>/tools/proton' and '<heroic_path>/tools/wine'
    """

    runners_path: list[str] = [os.path.join(heroic_path, 'tools', 'proton'), os.path.join(heroic_path, 'tools', 'wine') ]

    ctools: list[str] = []
    for c in dict.fromkeys(runners_path):  # de-duplicate, keep order
        if os.path.isdir(c):
            ctools.extend(d for d in os.listdir(c) if os.path.isdir(os.path.join(c, d)))

    return ctools

def heroic_build_tool_tree(runner: str, heroic_path: str) -> HeroicCompatTool:
    """
    Search for specific compatibility tool in proton and wine directory, pull data from the heroic installation directory and return them
    """
    
    tool = HeroicCompatTool()
    tool.displayname = runner
    base = os.path.join(os.path.realpath(os.path.expanduser(heroic_path)), 'tools')
    for ct_type in ('proton', 'wine'): 
        candidate = os.path.join(base, ct_type, runner)
        if os.path.isdir(candidate):
            tool.ct_dir = candidate
            tool.ct_type = ct_type
            break

    return tool

def heroic_update_ctool(game: HeroicGame, new_ctool: str, heroic_path='') -> bool:
    """
    Change compatibility tool from 'InternalHeroicAppID.json' to 'new_ctool' and respect proton
    and wine attribute differences. Changes will be applied to <heroic_dir>/GameConfigs/App.json
    """

    new_ct: HeroicCompatTool = heroic_build_tool_tree(new_ctool, heroic_path) # Build the necessary information of a proton version 
    
    # if the reported runner is proton then use Heroic's proton layout (e.g. bin/name/type) 
    # if the runner is wine (like wine tkg) however set more attributes
    if new_ct.ct_type == 'proton': 
        wine_version = {
            'bin': os.path.join(new_ct.ct_dir, 'proton'),
            'name': new_ct.displayname,
            'type': 'proton',
        }
    else:
        lib64 = os.path.join(new_ct.ct_dir, 'lib64')
        lib32 = os.path.join(new_ct.ct_dir, 'lib')
        wine_version = {
            'bin': os.path.join(new_ct.ct_dir, 'bin', 'wine'),
            'name': new_ct.displayname,
            'type': 'wine',
            'lib': lib64 if os.path.isdir(lib64) else '',
            'lib32': lib32 if os.path.isdir(lib32) else '',
            'wineserver': os.path.join(new_ct.ct_dir, 'bin', 'wineserver'),
        }

    # e.g. '<heroic_dir>/GamesConfig/<InternalAppID>.json'
    config_path = os.path.join( os.path.realpath(os.path.expanduser(heroic_path)), 'GamesConfig', f'{game.app_name}.json')

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Replace the whole wine Version section, so leftover keys such as
        # lib/lib32/wineserver from a previous wine runner are cleaned up
        data.setdefault(game.app_name, {})['wineVersion'] = wine_version

        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(config_path), suffix='.tmp') # write changes to .tmp file before migrating them to the actual config
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, config_path)
    except (OSError, json.JSONDecodeError) as e:
        print(f'[ERROR] Could not update Heroic config {config_path}: {e}')
        return False

    return True

# `is_installed` for GOG games is not always set properly
def is_gog_game_installed(game: HeroicGame) -> bool:
    """ Return True if a GOG game has an entry in heroic/gog_store/installed.json """

    return bool(get_gog_installed_game_entry(game))


def get_gog_installed_game_entry(game: HeroicGame) -> dict[str, Any]:
    """ Return JSON entry as dict for an installed GOG game from heroic/gog_store/installed.json """

    gog_installed_json_path = os.path.join(game.heroic_path, 'gog_store', 'installed.json')
    if not os.path.isfile(gog_installed_json_path) or not game.runner.lower() == 'gog':
        return {}

    gog_installed_json = json.load(open(gog_installed_json_path)).get('installed', [])
    for gog_game in gog_installed_json:
        if gog_game.get('appName', '') == game.app_name:
            return gog_game    
    else:
        return {}


def get_gog_game_executable(game: HeroicGame) -> str:
    """ Return the executable for a GOG game from its gameinfo file, or 'start.sh' for native Linux games. Will return empty string if no executable found. """

    # Proton games store it in `/path/to/install/goggame-<app_name>.info`, which is a JSON formatted file
    gog_gameinfo_filename = f'goggame-{game.app_name}.info'
    gog_gameinfo_json_path = os.path.join(game.install_path, gog_gameinfo_filename)

    # Native Linux games seem to only store 'start.sh' as their executable -- Assume native Linux if no wine_info
    if not game.wine_info:
        return 'start.sh'

    if not os.path.isfile(gog_gameinfo_json_path) or not game.runner.lower() == 'gog':
        return ''

    gog_gameinfo_json: dict[str, Any] = json.load(open(gog_gameinfo_json_path))
    gog_gameinfo_name: str = gog_gameinfo_json.get('name', '')
    gog_gameinfo_playtasks: dict[str, Any] = gog_gameinfo_json.get('playTasks', {})
    for playtasks in gog_gameinfo_playtasks:
        if playtasks.get('name', '').lower() == gog_gameinfo_name.lower():
            return playtasks.get('path', '')
    else:
        return ''
