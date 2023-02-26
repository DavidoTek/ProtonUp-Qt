import os
import json

from typing import List, Dict

from pupgui2.datastructures import HeroicGame


def get_heroic_game_list(heroic_path: str) -> List[HeroicGame]:
    """
    Returns a list of installed games for Heroic Games at 'heroic_path' (e.g., '~/.config/heroic', '~/.var/app/com.heroicgameslauncher.hgl/config/heroic')
    Return Type: List[HeroicGame]
    """

    if not os.path.isdir(heroic_path):
        return {}

    store_paths: List[str] = [ os.path.join(heroic_path, 'sideload_apps', 'library.json'), os.path.join(heroic_path, 'gog_store', 'library.json') ]
    legendary_path: str = os.path.abspath(os.path.join(heroic_path, '..', 'legendary', 'installed.json'))

    games_json: List = []
    for sp in store_paths:
        if os.path.isfile(sp):
            games_json += json.load(open(sp)).get('games', [])

    hgs: List[HeroicGame] = []
    for game in games_json:
        hg = HeroicGame()

        hg.runner: str = game.get('runner', '')
        hg.app_name: str = game.get('app_name', '')
        hg.title: str = game.get('title', '')
        hg.developer: str = game.get('developer', '')
        hg.install: Dict[str, str] = game.get('install', {})
        hg.heroic_path: str = heroic_path
        # Sideloaded games uses folder_name as their full install path, GOG games store a folder_name but this is *just* their install folder name
        # Prioritise getting install_path for GOG games as this is the GOG game equivalent to 'folder_name'
        hg.install_path: str = get_gog_installed_game_entry(hg).get('install_path', '') if hg.runner == 'gog' else game.get('folder_name', '')
        hg.store_url: str = game.get('store_url', '')
        hg.art_cover: str = game.get('art_cover', '')  # May need to replace path if it has 'file:///app/blah in name - See example in #168
        hg.art_square: str = game.get('art_square', '')
        hg.is_installed: bool = game.get('is_installed', False) or is_gog_game_installed(hg)  # Some installed gog games may not be marked properly in library.json, so cross-reference with installed.json
        hg.wine_info: Dict[str, str] = hg.get_game_config().get('wineVersion', {})

        hgs.append(hg)

    # Legendary Games uses a separate structure, so build separately
    if os.path.isfile(legendary_path):
        legendary_json = json.load(open(legendary_path))
        for app_name, game_data in legendary_json.items():
            lg = HeroicGame()

            lg.runner: str = 'legendary'  # Hardcoded 
            lg.app_name: str = app_name  # installed.json key is always the app_name 
            lg.title: str = game_data.get('title', '')
            lg.developer: str = ''  # Not stored or stored elsewhere?
            lg.install: Dict[str, str] = { 'executable': game_data.get('executable', ''), 'is_dlc': game_data.get('is_dlc', False), 'platform': game_data.get('platform', '') }
            lg.heroic_path: str = heroic_path
            lg.install_path: str = game_data.get('install_path', '') 
            lg.art_cover: str = ''  # Not stored or stored elsewhere?
            lg.art_square: str = ''  # Not stored or stored elsewhere?
            lg.is_installed: str = True  # Games in Legendary `installed.json` should always be installed
            lg.wine_info: Dict[str, str] = lg.get_game_config().get('wineVersion', {})  # Mirrors above, Legendary games should use the same GameConfig json structure

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
    if not os.path.isfile(gog_installed_json_path) or not game.runner == 'gog':
        return {}

    gog_installed_json = json.load(open(gog_installed_json_path)).get('installed', [])
    for gog_game in gog_installed_json:
        if gog_game.get('appName', '') == game.app_name:
            return gog_game    
    else:
        return {}
