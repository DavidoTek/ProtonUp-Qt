import os
import pathlib

import pytest
import pytest_responses

from responses import BaseResponse, RequestsMock

from pyfakefs.fake_filesystem import FakeFilesystem
from pyfakefs.fake_file import FakeFileWrapper

from pytest_mock import MockerFixture

from pupgui2.util import *
from pupgui2.constants import POSSIBLE_INSTALL_LOCATIONS, AWACY_GAME_LIST_URL, LOCAL_AWACY_GAME_LIST
from pupgui2.datastructures import SteamApp, LutrisGame, HeroicGame, Launcher


@pytest.fixture(scope='function')
def awacy_game_list(fs: FakeFilesystem):

    """
    Game List JSON for AreWeAntiCheatYet
    """

    awacy_game_list_fixture_path: str = f'{pathlib.Path(__file__).parent}/fixtures/util/awacy_game_list.json'

    fs.add_real_file(awacy_game_list_fixture_path)

    with open(awacy_game_list_fixture_path, 'r') as awacy_games_list:
        yield awacy_games_list


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


def test_get_random_game_name() -> None:

    """ Test whether get_random_game_name returns a valid game name for each launcher game type. """

    names: list[str] = ["game", "A super cool game", "A game with a very long name that is very long", "0123456789"]

    steam_app: list[SteamApp] = [SteamApp() for _ in range(len(names))]
    lutris_game: list[LutrisGame] = [LutrisGame() for _ in range(len(names))]
    heroic_game: list[HeroicGame] = [HeroicGame() for _ in range(len(names))]

    for i, name in enumerate(names):
        steam_app[i].game_name = name
        lutris_game[i].name = name
        heroic_game[i].title = name

    for i in range(10):
        assert get_random_game_name(steam_app) in names
        assert get_random_game_name(lutris_game) in names
        assert get_random_game_name(heroic_game) in names


def test_download_awacy_gamelist(responses: RequestsMock, fs: FakeFilesystem, mocker: MockerFixture, awacy_game_list: FakeFileWrapper) -> None:

    """
    Test that the AreWeAntiCheatYet game list JSON can be downloaded and written
    to the expected location successfully.
    """

    is_online_mock = mocker.patch('pupgui2.util.is_online')
    is_online_mock.return_value = True

    get_mock_body = awacy_game_list.read()
    get_mock: BaseResponse = responses.get(
        AWACY_GAME_LIST_URL,
        body=get_mock_body
    )

    fs.create_dir(TEMP_DIR)

    download_awacy_gamelist()

    # ensure the thread to write the gamelist to the file has finished
    for thread in threading.enumerate():
        if thread.name == '_download_awacy_gamelist':
            thread.join()

    file_content: str = ''
    with open(LOCAL_AWACY_GAME_LIST, 'r') as awacy_file:
        file_content = awacy_file.read()

    assert os.path.exists(LOCAL_AWACY_GAME_LIST)
    assert file_content == get_mock.body
    assert is_online_mock.call_count == 1


def test_download_awacy_gamelist_offline(mocker: MockerFixture) -> None:

    is_online_mock = mocker.patch('pupgui2.util.is_online')
    is_online_mock.return_value = False

    download_awacy_gamelist()

    assert not os.path.exists(LOCAL_AWACY_GAME_LIST)

    assert is_online_mock.call_count == 1
    assert is_online_mock.return_value == False
