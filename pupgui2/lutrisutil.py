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
                working_dir = lg_config.get('game', {}).get('working_dir')
                exe_dir = lg_config.get('game', {}).get('exe')
                lutris_install_dir = working_dir or (os.path.dirname(str(exe_dir)) if exe_dir else None)

            lg.install_dir = os.path.abspath(lutris_install_dir) if lutris_install_dir else ''
            lgs.append(lg)
    except Exception as e:
        print('Error: Could not get lutris game list:', e)
    return lgs
