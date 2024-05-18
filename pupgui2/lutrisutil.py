import os
from typing import List
import sqlite3

from pupgui2.datastructures import LutrisGame


LUTRIS_PGA_GAMELIST_QUERY = 'SELECT slug, name, runner, installer_slug, installed_at, directory FROM games'


def get_lutris_game_list(install_loc) -> List[LutrisGame]:
    """
    Returns a list of installed games in Lutris
    Return Type: List[LutrisGame]
    """
    install_dir = os.path.expanduser(install_loc.get('install_dir'))
    lutris_data_dir = os.path.join(install_dir, os.pardir, os.pardir)
    pga_db_file = os.path.join(lutris_data_dir, 'pga.db')
    lgs = []
    try:
        con = sqlite3.connect(pga_db_file)
        cur = con.cursor()
        cur.execute(LUTRIS_PGA_GAMELIST_QUERY)
        res = cur.fetchall()
        for g in res:
            lg = LutrisGame()
            lg.install_loc = install_loc
            lg.slug = g[0]
            lg.name = g[1]
            lg.runner = g[2]
            lg.installer_slug = g[3]
            lg.installed_at = g[4]
            
            # Lutris database file will only store some fields for games installed via an installer and not if it was manually added
            # If a game doesn't have an install dir (e.g. it was manually added to Lutris), try to use the following for the install dir:
            # - Working directory (may not be specified)
            # - Executable: may not be accurate as the exe could be heavily nested, but a good fallback)
            lutris_install_dir = g[5]
            if not lutris_install_dir:
                lg_config = lg.get_game_config()
                lg_game_config = lg_config.get('game', {})

                working_dir = lg_game_config.get('working_dir')
                exe_dir = lg_game_config.get('exe')

                lutris_install_dir = working_dir or (os.path.dirname(str(exe_dir)) if exe_dir else None)

                # If a LutrisGame config has an 'appid' in its 'game' section in its yml, assume runner is Steam
                if lg_game_config.get('appid', None) is not None:
                    lg.runner = 'steam'

            lg.install_dir = os.path.abspath(lutris_install_dir) if lutris_install_dir else ''
            lgs.append(lg)
    except Exception as e:
        print('Error: Could not get lutris game list:', e)
    return lgs


def is_lutris_game_using_runner(game: LutrisGame, runner: str) -> bool:

    """ Determine if a LutrisGame is using a given runner. """

    is_runner_name_valid = game.runner is not None and len(game.runner) > 0
    is_using_runner = game.runner == runner

    return is_runner_name_valid and is_using_runner


def is_lutris_game_using_wine(game: LutrisGame, wine_version: str = '') -> bool:

    """ Determine if a LutrisGame is using a given wine_version string. """

    is_using_wine = is_lutris_game_using_runner(game, 'wine')

    # Only check wine_version if it is passed
    if len(wine_version) > 0:
        is_using_wine_version = game.get_game_config().get('wine', {}).get('version', '') == wine_version
    else:
        is_using_wine_version = True

    return is_using_wine and is_using_wine_version
