from pupgui2.util import *

from pupgui2.constants import POSSIBLE_INSTALL_LOCATIONS
from pupgui2.datastructures import SteamApp, LutrisGame, HeroicGame, Launcher


def test_get_launcher_from_installdir() -> None:

    """
    Test whether get_laucher_from_installdir returns the correct Launcher type Enum from the installdir path.
    """

    # All possible Steam paths
    steam_install_paths: list[str] = [ install_location['install_dir'] for install_location in POSSIBLE_INSTALL_LOCATIONS if install_location['launcher'] == 'steam' ]
    steam_install_path_tests: list[Launcher] = [ get_launcher_from_installdir(steam_path) for steam_path in steam_install_paths ]

    # All possible Lutris paths
    lutris_install_paths: list[str] = [ install_location['install_dir'] for install_location in POSSIBLE_INSTALL_LOCATIONS if install_location['launcher'] == 'lutris' ]
    lutris_install_path_tests: list[Launcher] = [ get_launcher_from_installdir(lutris_path) for lutris_path in lutris_install_paths ]

    # All possible Heroic paths
    heroic_install_paths: list[str] = [ install_location['install_dir'] for install_location in POSSIBLE_INSTALL_LOCATIONS if install_location['launcher'] in ['heroicwine', 'heroicproton'] ]
    heroic_install_path_tests: list[Launcher] = [ get_launcher_from_installdir(heroic_path) for heroic_path in heroic_install_paths ]

    # All possible Bottles paths
    bottles_install_paths: list[str] = [ install_location['install_dir'] for install_location in POSSIBLE_INSTALL_LOCATIONS if install_location['launcher'] == 'bottles' ]
    bottles_install_path_tests: list[Launcher] = [ get_launcher_from_installdir(bottles_path) for bottles_path in bottles_install_paths ]

    # All possible Bottles paths
    winezgui_install_paths: list[str] = [ install_location['install_dir'] for install_location in POSSIBLE_INSTALL_LOCATIONS if install_location['launcher'] == 'winezgui' ]
    winezgui_install_path_tests: list[Launcher] = [ get_launcher_from_installdir(winezgui_path) for winezgui_path in winezgui_install_paths ]


    assert all(launcher == Launcher.STEAM for launcher in steam_install_path_tests)
    assert all(launcher == Launcher.LUTRIS for launcher in lutris_install_path_tests)
    assert all(launcher == Launcher.HEROIC for launcher in heroic_install_path_tests)
    assert all(launcher == Launcher.BOTTLES for launcher in bottles_install_path_tests)
    assert all(launcher == Launcher.WINEZGUI for launcher in winezgui_install_path_tests)


def test_get_random_game_name():
    """ test whether get_random_game_name returns a valid game name """
    names = ["game", "A super cool game", "A game with a very long name that is very long", "0123456789"]

    steam_app = [SteamApp() for _ in range(len(names))]
    lutris_game = [LutrisGame() for _ in range(len(names))]
    heroic_game = [HeroicGame() for _ in range(len(names))]

    for i, name in enumerate(names):
        steam_app[i].game_name = name
        lutris_game[i].name = name
        heroic_game[i].title = name

    for i in range(10):
        assert get_random_game_name(steam_app) in names
        assert get_random_game_name(lutris_game) in names
        assert get_random_game_name(heroic_game) in names
