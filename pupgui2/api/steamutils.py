import vdf

from typing import *

from pupgui2.api.compattool import *
from pupgui2.api.launcher import *
from pupgui2.datastructures import *


def steam_update_ctool(game: SteamApp, new_ctool:CompatTool=None, steam_config_folder=None) -> bool:
    """
    Change compatibility tool for 'game_id' to 'new_ctool' in Steam config vdf
    Return Type: bool
    """
    steam_config_folder = steam_config_folder or new_ctool.get_launcher().get_config_dir()

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
                c.get(str(game_id))['name'] = str(new_ctool.get_internal_name())
        else:
            c[str(game_id)] = {"name": str(new_ctool.get_internal_name()), "config": "", "priority": "250"}

        vdf.dump(d, open(config_vdf_file, 'w'), pretty=True)
    except Exception as e:
        print('Error, could not update Steam compatibility tool to', new_ctool.get_internal_name(), 'for game',game_id, ':',
              e, ', vdf:', config_vdf_file)
        return False
    return True
