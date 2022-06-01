import os
from re import A
import sqlite3

from .datastructures import LutrisGame

LUTRIS_PGA_GAMELIST_QUERY = 'SELECT slug, name, runner FROM games'


def get_lutris_game_list(lutris_data_dir: str):
    """
    Returns a list of installed games in Lutris
    Return Type: LutrisGame[]
    """
    pga_db_file = os.path.join(lutris_data_dir, 'pga.db')
    lgs = []
    try:
        con = sqlite3.connect(pga_db_file)
        cur = con.cursor()
        cur.execute(LUTRIS_PGA_GAMELIST_QUERY)
        res = cur.fetchall()
        for g in res:
            lg = LutrisGame()
            lg.slug = g[0]
            lg.name = g[1]
            lg.runner = g[2]
            lgs.append(lg)
    except Exception as e:
        print('Error: Could not get lutris game list:', e)
    return lgs
