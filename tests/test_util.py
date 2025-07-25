import os
import pathlib

import pytest
import pytest_responses

from responses import BaseResponse, RequestsMock

from pyfakefs.fake_filesystem import FakeFilesystem
from pyfakefs.fake_file import FakeFileWrapper

from pytest_mock import MockerFixture

from pupgui2.util import *
from pupgui2.constants import POSSIBLE_INSTALL_LOCATIONS, AWACY_GAME_LIST_URL, LOCAL_AWACY_GAME_LIST, GITLAB_API, GITHUB_API
from pupgui2.datastructures import SteamApp, LutrisGame, HeroicGame, Launcher, SteamUser


github_api_ratelimit_url: str = 'https://api.github.com/rate_limit/'


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


@pytest.mark.parametrize(
    'test_dict, expected_type', [
        pytest.param(
            { 'steam': 'Steam', 'lutris': 'Lutris' },
            str,
            id = 'Get string launcher keys from dict'
        ),
        pytest.param(
            { 2: 'two', 4: 'four' },
            int,
            id = 'Get integer keys from string value'
        ),
        pytest.param(
            { Launcher.WINEZGUI: True, Launcher.HEROIC: False },
            Launcher,
            id = 'Get Enum (Launcher) keys from boolean value'
        ),
    ],
)
def test_get_dict_key_from_value(test_dict: dict[str | int | Launcher, str | str | bool], expected_type: str | int | Launcher) -> None:

    """
    Test whether get_dict_key_from_value can retrieve the expected key of an expected type from a given dictionary,
    where the key-value pair can be of any type.
    """

    for key, value in test_dict.items():

        retrieved_key: str | int | Launcher = get_dict_key_from_value(test_dict, value)

        assert retrieved_key == key
        assert type(retrieved_key) is expected_type


@pytest.mark.parametrize(
    'launcher_paths, expected_launcher', [
        pytest.param(
            [ install_location['install_dir'] for install_location in POSSIBLE_INSTALL_LOCATIONS if install_location['launcher'] == 'steam' ],
            Launcher.STEAM,
            id='Steam Launcher'
        ),
        pytest.param(
            [ install_location['install_dir'] for install_location in POSSIBLE_INSTALL_LOCATIONS if install_location['launcher'] == 'lutris' ],
            Launcher.LUTRIS,
            id='Lutris Launcher'
        ),
        pytest.param(
            [ install_location['install_dir'] for install_location in POSSIBLE_INSTALL_LOCATIONS if install_location['launcher'] in ('heroicwine', 'heroicproton') ],
            Launcher.HEROIC,
            id='Heroic Wine / Heroic Proton Launcher'
        ),
        pytest.param(
            [ install_location['install_dir'] for install_location in POSSIBLE_INSTALL_LOCATIONS if install_location['launcher'] == 'bottles' ],
            Launcher.BOTTLES,
            id='Bottles Launcher'
        ),
        pytest.param(
            [ install_location['install_dir'] for install_location in POSSIBLE_INSTALL_LOCATIONS if install_location['launcher'] == 'winezgui' ],
            Launcher.WINEZGUI,
            id='WineZGUI Launcher'
        ),
    ]
)
def test_get_launcher_from_installdir(launcher_paths: list[str], expected_launcher: Launcher) -> None:

    """
    Test whether get_laucher_from_installdir returns the correct Launcher type Enum from the installdir path.
    """

    launcher_from_installdir: list[Launcher] = [ get_launcher_from_installdir(launcher_path) for launcher_path in launcher_paths ]

    assert all(launcher == expected_launcher for launcher in launcher_from_installdir)


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
    bad_names: list[str] = list("Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor".split(','))

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


def test_is_online(responses: RequestsMock) -> None:

    """
    Test that is_online will succeed when sending a GET request to the provided host returns success response.
    """

    timeout: int = 5

    get_mock: BaseResponse = responses.get(
        github_api_ratelimit_url,
        status = 200,
    )

    result: bool = is_online(host = github_api_ratelimit_url, timeout = timeout)

    assert result

    assert get_mock.call_count == 1
    assert get_mock.method == 'GET'
    assert get_mock.url == github_api_ratelimit_url
    assert get_mock.status == 200


@pytest.mark.parametrize('expected_error', [
    pytest.param(
        requests.ConnectionError('Connection Error'), id='ConnectionError'
    ),
    pytest.param(
        requests.Timeout('Timeout Error'), id='Timeout'
    )
])
def test_is_online_errors(responses: RequestsMock, expected_error: requests.ConnectionError | requests.Timeout):

    """ Test that is_online will return False when an expected error is caught. """

    get_mock: BaseResponse = responses.get(
        github_api_ratelimit_url,
        body=expected_error
    )

    result = is_online(host = github_api_ratelimit_url)

    assert result == False

    assert get_mock.call_count == 1
    assert get_mock.body == expected_error


@pytest.mark.parametrize(
    'url, is_gitlab_api', [
        *[pytest.param(api, True, id = api) for api in GITLAB_API],
        pytest.param(GITHUB_API, False, id = GITHUB_API)
    ]
)
def test_is_gitlab_instance(url: str, is_gitlab_api: bool) -> None:

    """
    Test that a given GitLab API URL is detected successfully.
    """

    result: bool = is_gitlab_instance(url)

    assert result == is_gitlab_api


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


@pytest.mark.parametrize(
    'compat_tool_name, ctobjs, expected', [
        pytest.param(
            'GE-Proton9-27',
            [
                { 'name': 'Luxtorpeda' },
                { 'name': 'GE-Proton8-16' },
                { 'name': 'GE-Proton9-27' },
                { 'name': 'Proton-GE-5-2' },
                { 'name': 'Proton-tkg.10.6.a34b12f' }
            ],
            True,
            id = 'GE-Proton9-27 should be found'
        ),
        pytest.param(
            'Wine-tkg',
            [
                { 'name': 'Luxtorpeda' },
                { 'name': 'GE-Proton8-16' },
                { 'name': 'GE-Proton9-27' },
                { 'name': 'Proton-GE-5-2' },
                { 'name': 'Proton-tkg.10.6.a34b12f' }
            ],
            False,
            id = 'Wine-tkg should not be found'
        ),
        pytest.param(
            'GE-Proton9-2',
            [
                { 'name': 'Luxtorpeda' },
                { 'name': 'GE-Proton8-16' },
                { 'name': 'GE-Proton9-27' },
                { 'name': 'Proton-GE-5-2' },
                { 'name': 'Proton-tkg.10.6.a34b12f' }
            ],
            False,
            id = 'GE-Proton9-2 should not be found'
        ),
        
    ]
)
def test_compat_tool_available(compat_tool_name: str, ctobjs: list[dict[str, str]], expected: bool) -> None:

    """
    Given a list of dictionaries containing compatibility tools,
    When the name of the compatibility tool is in the list of dictionaries,
    Then it should return whether the given compatibility tool name is in the list of dictionaries
    """

    result: bool = compat_tool_available(compat_tool_name, ctobjs)

    assert result == expected


@pytest.mark.parametrize(
    'combobox_values, value, expected_index', [
        pytest.param(['a', 'b', 'c', 'd', 'e'], 'c', 2, id = 'Simple list'),
        pytest.param(['Steam', 'Lutris',' Heroic'], 'Lutris', 1, id = 'List of Launcher Names'),
        pytest.param(['GE-Proton', 'Proton-tkg', 'SteamTinkerLaunch'], 'SteamTinkerLaunch', 2, id = 'List of Compatibility Tool names'),
    ]
)
def test_get_combobox_index_by_value(combobox_values: list[str], value: str, expected_index: int) -> None:

    app = QApplication()

    combobox: QComboBox = QComboBox()

    combobox.addItems(combobox_values)

    result: int = get_combobox_index_by_value(combobox, value)

    assert combobox_values[result] == value
    assert result == expected_index

    QApplication.shutdown(app)
