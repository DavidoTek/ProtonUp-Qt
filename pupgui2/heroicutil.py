import os
import json
import re

from typing import List, Dict

from pupgui2.datastructures import HeroicGame
from pupgui2.constants import EPIC_STORE_URL


def get_heroic_game_list(heroic_path: str) -> List[HeroicGame]:
    """
    Returns a list of installed games for Heroic Games at 'heroic_path' (e.g., '~/.config/heroic', '~/.var/app/com.heroicgameslauncher.hgl/config/heroic')
    Return Type: List[HeroicGame]
    """

    if not os.path.isdir(heroic_path):
        return []

    # "Nile" refers to Amazon Games
    store_paths: List[str] = [ os.path.join(heroic_path, 'sideload_apps', 'library.json'), os.path.join(heroic_path, 'gog_store', 'library.json'), os.path.join(heroic_path, 'store_cache', 'nile_library.json') ]
    legendary_path: str = os.path.abspath(os.path.join(heroic_path, '..', 'legendary', 'installed.json'))

    games_json: List = []
    for sp in store_paths:
        if os.path.isfile(sp):
            games_json_file = json.load(open(sp))

            games_json += games_json_file.get('games', [])  # GOG + sideload use 'games' as top-level object
            games_json += games_json_file.get('library', [])  # Nile uses 'library' as top-level object

    hgs: List[HeroicGame] = []
    for game in games_json:
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
        legendary_json = json.load(open(legendary_path))
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


# `is_installed` for GOG games is not always set properly
def is_gog_game_installed(game: HeroicGame) -> bool:
    """ Return True if a GOG game has an entry in heroic/gog_store/installed.json """

    return bool(get_gog_installed_game_entry(game))


def get_gog_installed_game_entry(game: HeroicGame) -> Dict:
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

    gog_gameinfo_json = json.load(open(gog_gameinfo_json_path))
    gog_gameinfo_name = gog_gameinfo_json.get('name', '')
    gog_gameinfo_playtasks = gog_gameinfo_json.get('playTasks', {})
    for playtasks in gog_gameinfo_playtasks:
        if playtasks.get('name', '').lower() == gog_gameinfo_name.lower():
            return playtasks.get('path', '')
    else:
        return ''
