from typing_extensions import LiteralString
import pytest

from pupgui2.util import *

from pupgui2.constants import POSSIBLE_INSTALL_LOCATIONS
from pupgui2.datastructures import SteamApp, LutrisGame, HeroicGame, Launcher, SteamUser


def test_build_headers_with_authorization() -> None:

    """
    Test whether the expected Authorization Tokens get inserted into the returned headers dict,
    that existing Authorization is replaced properly, and that all other existing headers are preserved.
    """

    user_agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36'

    # Simulate existing headers with old Authentiation to be replaced, and a User-Agent that should remain untouched
    request_headers: dict[str, Any] = {
        'Authorization': 'ABC123',
        'User-Agent': user_agent
    }

    # Simulate auth tokens that would normally come from the environment or config file
    authorization_tokens: dict[str, str] = {
        'github': 'gha_abc123daf456',
        'gitlab': 'glpat-zyx987wvu654',
    }

    github_token_call: dict[str, Any] = build_headers_with_authorization(request_headers, authorization_tokens, 'github')
    gitlab_token_call: dict[str, Any] = build_headers_with_authorization(request_headers, authorization_tokens, 'gitlab')

    unknown_token_call: dict[str, Any] = build_headers_with_authorization(request_headers, authorization_tokens, '')
    call_with_no_tokens: dict[str, Any] = build_headers_with_authorization(request_headers, {}, 'github')

    assert github_token_call.get('Authorization', '') == f'token {authorization_tokens["github"]}'
    assert gitlab_token_call.get('Authorization', '') == f'Bearer {authorization_tokens["gitlab"]}'

    assert unknown_token_call.get('Authorization', '') == ''
    assert call_with_no_tokens.get('Authorization', '') == ''

    assert github_token_call.get('User-Agent', '') == user_agent


def test_get_dict_key_from_value() -> None:

    """
    Test whether get_dict_key_from_value can retrieve the expected key from a dict by a value,
    where the key and value can be of any type.
    """

    dict_with_str_keys: dict[str, str] = {
        'steam': 'Steam',
        'lutris': 'Lutris',
    }

    dict_with_int_keys: dict[int, str] = {
        2: 'two',
        4: 'four'
    }

    dict_with_enum_keys: dict[Launcher, bool] = {
        Launcher.WINEZGUI: True,
        Launcher.HEROIC: False
    }

    test_dicts: list[dict[Any, Any]] = [
        dict_with_str_keys,
        dict_with_int_keys,
        dict_with_enum_keys,
    ]

    for test_dict in test_dicts:
        assert all( get_dict_key_from_value(test_dict, value) == key for key, value in test_dict.items() )


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

    # All possible WineZGUI paths
    winezgui_install_paths: list[str] = [ install_location['install_dir'] for install_location in POSSIBLE_INSTALL_LOCATIONS if install_location['launcher'] == 'winezgui' ]
    winezgui_install_path_tests: list[Launcher] = [ get_launcher_from_installdir(winezgui_path) for winezgui_path in winezgui_install_paths ]


    assert all(launcher == Launcher.STEAM for launcher in steam_install_path_tests)
    assert all(launcher == Launcher.LUTRIS for launcher in lutris_install_path_tests)
    assert all(launcher == Launcher.HEROIC for launcher in heroic_install_path_tests)
    assert all(launcher == Launcher.BOTTLES for launcher in bottles_install_path_tests)
    assert all(launcher == Launcher.WINEZGUI for launcher in winezgui_install_path_tests)


@pytest.mark.parametrize(
    'game_list, game_name_attr', [
        pytest.param([SteamApp() for _ in range(3)], 'game_name', id = 'Steam Games'),
        pytest.param([LutrisGame() for _ in range(3)], 'name', id = 'Lutris Games'),
        pytest.param([HeroicGame() for _ in range(3)], 'title', id = 'Heroic Games'),
    ]
)
def test_get_random_game_name(game_list: list[SteamApp] | list[LutrisGame] | list[HeroicGame], game_name_attr: str) -> None:

    """ Test whether get_random_game_name returns a valid game name for each launcher game type. """

    names: list[str] = ["game", "A super cool game", "A game with a very long name that is very long", "0123456789"]
    bad_names: list[LiteralString] = "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor".split(',')

    for i, game in enumerate(game_list):
        setattr(game, game_name_attr, names[i])

    for i in range(len(names) * 2):
        result: str = get_random_game_name(game_list)

        assert isinstance(result, str)

        assert result in names
        assert result not in bad_names


@pytest.mark.parametrize(
    'game_list, game_name_attr', [
        pytest.param([SteamApp() for _ in range(4)], 'game_name', id = 'Steam Games'),
        pytest.param([LutrisGame() for _ in range(4)], 'name', id = 'Lutris Games'),
        pytest.param([HeroicGame() for _ in range(4)], 'title', id = 'Heroic Games'),
    ]
)
def test_get_random_game_name_returns_str(game_list: list[SteamApp] | list[LutrisGame] | list[HeroicGame], game_name_attr: str) -> None:

    """ Test that get_random_game_name will always return a string. """

    names: list[int | float] = [12, 3.14, [1, 734, 12112121][0], -85, 99999999999]
    str_names: list[str] = [str(name) for name in names]

    for i, game in enumerate(game_list):
        setattr(game, game_name_attr, names[i])

    for i in range(len(names) * 2):

        result: str = get_random_game_name(game_list)

        assert isinstance(result, str)
        assert result in str_names


@pytest.mark.parametrize(
    'game_list', [
        pytest.param([], id = 'Empty List'),
        pytest.param((), id = 'Empty Tuple'),
        pytest.param([[], []], id = 'Empty List of Lists'),
        pytest.param([(), ()], id = 'Empty List of Tuples'),
        pytest.param([SteamUser(), SteamUser()], id = 'Empty List of SteamUser object')
    ]
)
def test_get_random_game_name_unknown(game_list) -> None:

    """ Test that get_random_game_name returns an empty string when given a list that does not have a known game type. """

    assert get_random_game_name(game_list) == ''
