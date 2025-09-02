import pytest

import os

from pyfakefs.fake_filesystem import FakeFilesystem

from pupgui2.steamutil import calc_shortcut_app_id, is_valid_steam_install
from pupgui2.constants import HOME_DIR, POSSIBLE_INSTALL_LOCATIONS


KNOWN_STEAM_INSTALL_LOCATIONS: list[dict[str, str]] = [install_location for install_location in POSSIBLE_INSTALL_LOCATIONS if install_location['launcher'] == 'steam']


@pytest.mark.parametrize(
    'shortcut_dict, expected_appid', [
        pytest.param({ 'name': 'Half-Life 3', 'exe': 'hl3.exe' }, -758629442, id = 'Half-Life 3 (-758629442)'),
        pytest.param({ 'name': 'Twenty One', 'exe': '21.exe' }, -416959852, id = 'Twenty One (-416959852)'),
        pytest.param({ 'name': 'ProtonUp-Qt', 'exe': 'pupgui2' }, -1763982845, id = 'ProtonUp-Qt (-1763982845)')
    ]
)
def test_calc_shortcut_app_id(shortcut_dict: dict[str, str], expected_appid: int) -> None:

    result: int = calc_shortcut_app_id(shortcut_dict.get('name', ''), shortcut_dict.get('exe', ''))

    assert result == expected_appid


@pytest.mark.parametrize(
    'steam_path', [
        pytest.param(
            os.path.expanduser(install_location['install_dir']),
            id = f'{install_location["install_dir"]}'
        ) for install_location in KNOWN_STEAM_INSTALL_LOCATIONS
    ]
)
def test_is_valid_steam_install_happy_path(fs: FakeFilesystem, steam_path: str) -> None:

    """
    Given a path to a possible Steam installation,
    When the folder exists as a known Steam path with the config.vdf and libraryfolders.vdf files inside,
    Then it should return True.
    """

    config_dir: str = os.path.join(steam_path, 'config')

    config_vdf_path: str = os.path.join(config_dir, 'config.vdf')
    libraryfolders_vdf_path = os.path.join(config_dir, 'libraryfolders.vdf')

    fs.create_dir(steam_path)

    fs.create_file(config_vdf_path, create_missing_dirs = True)
    fs.create_file(libraryfolders_vdf_path, create_missing_dirs = True)

    result: bool = is_valid_steam_install(steam_path)

    assert result


@pytest.mark.parametrize(
  'symlink_path, real_path', [
    pytest.param(
        os.path.join(HOME_DIR, '.steam/steam'),
        os.path.join(HOME_DIR, '.local/share/Steam'),
        id = '~/.steam/steam -> ~/.local/share/Steam'
    ),
    pytest.param(
        os.path.join(HOME_DIR, '.steam/root'),
        os.path.join(HOME_DIR, '.local/share/Steam'),
        id = '~/.steam/root -> ~/.local/share/Steam'
    )
  ]
)
def test_is_valid_steam_install_symlink(fs: FakeFilesystem, symlink_path: str, real_path: str):

    """
    Given a symlink path to a Steam installation,
    When the pointed path is a valid Steam installation,
    Then it should return True.
    """

    config_dir = os.path.join(real_path, 'config')

    config_vdf_path: str = os.path.join(config_dir, 'config.vdf')
    libraryfolders_vdf_path = os.path.join(config_dir, 'libraryfolders.vdf')

    fs.create_dir(real_path)

    fs.create_file(config_vdf_path, create_missing_dirs = True)
    fs.create_file(libraryfolders_vdf_path, create_missing_dirs = True)

    fs.create_symlink(symlink_path, real_path)

    result: bool = is_valid_steam_install(symlink_path)

    assert result


@pytest.mark.parametrize(
    'path, should_folder_exist', [
        *[
            pytest.param(
                os.path.expanduser(install_location['install_dir']),
                True,
                id = f'Steam Path - {install_location["install_dir"]}'
            ) for install_location in KNOWN_STEAM_INSTALL_LOCATIONS
        ],

        *[
            pytest.param(
                os.path.expanduser(install_location['install_dir']),
                True,
                id = f'Non-Steam Path - {install_location["install_dir"]}'
            ) for install_location in POSSIBLE_INSTALL_LOCATIONS if install_location['launcher'] != 'steam'
        ],

        *[
            pytest.param(
                '/not/a/path',
                False,
                id = 'Invalid Path - Nested'
            ),
            pytest.param(
                'not-a-path',
                False,
                id = 'Invalid Path - Single'
            ),
        ]
    ]
)
def test_is_valid_steam_install_no_vdfs(fs: FakeFilesystem, path: str, should_folder_exist: bool) -> None:

    """
    Given a path to a possible Steam installation,
    When the folder does not exist
    Or the folder exists but without the config.vdf and libraryfolders.vdf files inside,
    Then it should return False.
    """

    if should_folder_exist:
        fs.create_dir(path)

    result: bool = is_valid_steam_install(path)

    assert not result
