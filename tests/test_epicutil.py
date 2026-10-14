import json

import pytest

from pupgui2.constants import POSSIBLE_INSTALL_LOCATIONS

from pupgui2.epicutil import *


@pytest.mark.parametrize('launcher, expected_epic_launcher', [
    *[pytest.param(install_loc.get('launcher'), install_loc.get('launcher') == 'epicgames', id = install_loc.get('display_name')) for install_loc in POSSIBLE_INSTALL_LOCATIONS]
])
def test_is_epic_launcher(launcher: str, expected_epic_launcher: bool) -> None:

    assert is_epic_launcher(launcher) == expected_epic_launcher


def test_get_epic_dir_from_install_dir() -> None:

    assert get_epic_dir_from_install_dir('/home/gaben/.local/share/com.epicgames.eglv2/compat/runtime/') == '/home/gaben/.local/share/com.epicgames.eglv2'


@pytest.fixture
def epic_dir(tmp_path):

    (tmp_path / 'compat' / 'runtime' / 'GE-Proton10-34').mkdir(parents=True)
    (tmp_path / 'compat' / 'runtime' / 'GE-Proton10-34' / 'proton').touch()
    (tmp_path / 'cache' / 'prod').mkdir(parents=True)
    (tmp_path / 'cache' / 'prod' / 'catalog-cache.json').write_text(json.dumps({'items': {'item1': {'item': {'id': 'item1', 'title': 'Among Us'}}}}))

    games = tmp_path / 'Games'
    for name in ['AmongUs', 'NativeGame', 'Pending']:
        (games / name).mkdir(parents=True)

    entries = [
        {'version': 1, 'entries': 0},
        {'installationId': 'A', 'complete': False, 'dir': str(games / 'AmongUs'), 'platform': 'Windows', 'itemId': 'item1', 'artifactId': 'art1'},
        {'installationId': 'A', 'complete': True, 'dir': str(games / 'AmongUs'), 'platform': 'Windows', 'itemId': 'item1', 'artifactId': 'art1', 'version': '7489', 'launchExecutable': 'Among Us.exe'},
        {'installationId': 'B', 'complete': True, 'dir': str(games / 'NativeGame'), 'platform': 'Linux', 'itemId': 'item2', 'artifactId': 'art2'},
        {'installationId': 'C', 'complete': False, 'dir': str(games / 'Pending'), 'platform': 'Windows', 'itemId': 'item3', 'artifactId': 'art3'},
        {'installationId': 'D', 'complete': True, 'dir': str(games / 'Removed'), 'platform': 'Windows', 'itemId': 'item4', 'artifactId': 'art4'},
    ]
    (tmp_path / 'installations.jsonl').write_text('\n'.join(json.dumps(e) for e in entries) + '\n')

    return str(tmp_path)


def write_pin(epic_dir: str, version: str) -> None:

    with open(os.path.join(epic_dir, 'compat', 'runtime', 'pin-cache.json'), 'w') as f:
        json.dump({'version': version}, f)


def add_runtime(epic_dir: str, name: str, with_proton: bool = True) -> None:

    os.makedirs(os.path.join(epic_dir, 'compat', 'runtime', name))
    if with_proton:
        open(os.path.join(epic_dir, 'compat', 'runtime', name, 'proton'), 'w').close()


def test_get_epic_runtimes(epic_dir: str) -> None:

    add_runtime(epic_dir, 'staging', with_proton=False)

    assert get_epic_runtimes(epic_dir) == ['GE-Proton10-34']


def test_get_epic_pinned_runtime(epic_dir: str) -> None:

    # Without pin-cache.json, the only installed runtime is used
    assert get_epic_pinned_runtime(epic_dir) == 'GE-Proton10-34'

    # Pinned version not installed yet, the only installed runtime is still used
    write_pin(epic_dir, 'GE-Proton10-40')
    assert get_epic_pinned_runtime(epic_dir) == 'GE-Proton10-34'

    add_runtime(epic_dir, 'GE-Proton10-40')
    assert get_epic_pinned_runtime(epic_dir) == 'GE-Proton10-40'


def test_get_epic_pinned_runtime_unknown(epic_dir: str) -> None:

    # Multiple runtimes and no usable pin: cannot be determined
    add_runtime(epic_dir, 'GE-Proton10-40')
    assert get_epic_pinned_runtime(epic_dir) == ''

    write_pin(epic_dir, 'GE-Proton10-50')
    assert get_epic_pinned_runtime(epic_dir) == ''


@pytest.mark.parametrize('content', ['[]', 'not json', '\udcff', '{"version": null}'])
def test_get_epic_pinned_runtime_malformed(epic_dir: str, content: str) -> None:

    with open(os.path.join(epic_dir, 'compat', 'runtime', 'pin-cache.json'), 'w', encoding='utf-8', errors='surrogateescape') as f:
        f.write(content)

    assert get_epic_pinned_runtime(epic_dir) == 'GE-Proton10-34'


def test_get_epic_game_list(epic_dir: str) -> None:

    games = {game.installation_id: game for game in get_epic_game_list(epic_dir)}

    assert sorted(games.keys()) == ['A', 'B']

    assert games['A'].title == 'Among Us'
    assert games['A'].platform == 'Windows'
    assert games['A'].executable == 'Among Us.exe'
    assert games['A'].compat_tool == 'GE-Proton10-34'
    assert games['A'].get_prefix_path() == os.path.join(epic_dir, 'compat', 'compatdata', 'art1', 'pfx')

    assert games['B'].title == 'NativeGame'  # Not in catalog cache, falls back to folder name
    assert games['B'].compat_tool == ''


def test_get_epic_game_list_missing_dir(tmp_path) -> None:

    assert get_epic_game_list(str(tmp_path / 'does-not-exist')) == []


def test_get_epic_game_list_without_titles(epic_dir: str) -> None:

    games = {game.installation_id: game for game in get_epic_game_list(epic_dir, pinned_runtime='GE-Proton10-40', with_titles=False)}

    assert games['A'].title == 'AmongUs'
    assert games['A'].compat_tool == 'GE-Proton10-40'


def test_get_epic_game_list_malformed(epic_dir: str) -> None:

    with open(os.path.join(epic_dir, 'cache', 'prod', 'catalog-cache.json'), 'w') as f:
        json.dump({'items': {'item1': {'item': None}, 'item2': 'foo'}}, f)

    with open(os.path.join(epic_dir, 'installations.jsonl'), 'a') as f:
        f.write('not json\n')
        f.write('[]\n')
        f.write(json.dumps({'installationId': 'E', 'complete': True, 'dir': None, 'platform': None}) + '\n')
        f.write(json.dumps({'installationId': 'F', 'complete': True, 'dir': os.path.join(epic_dir, 'Games', 'Pending'), 'platform': None, 'itemId': 7}) + '\n')

    games = {game.installation_id: game for game in get_epic_game_list(epic_dir)}

    assert sorted(games.keys()) == ['A', 'B', 'F']
    assert games['A'].title == 'AmongUs'
    assert games['F'].platform == ''
    assert games['F'].compat_tool == ''
