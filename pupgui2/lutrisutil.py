import os
from typing import List
import sqlite3

from pupgui2.datastructures import LutrisGame


LUTRIS_PGA_GAMELIST_QUERY = 'SELECT slug, name, runner, installer_slug, installed_at FROM games'


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
            lgs.append(lg)
    except Exception as e:
        print('Error: Could not get lutris game list:', e)
    return lgs
