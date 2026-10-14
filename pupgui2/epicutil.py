import os
import json

from typing import Any

from pupgui2.datastructures import EpicGame


# The Epic Games Launcher (v2, data in '~/.local/share/com.epicgames.eglv2') runs Windows games with a single,
# launcher-managed Proton runtime. The runtime version is pinned by Epic and installed to 'compat/runtime/<version>',
# prefixes are created per game in 'compat/compatdata/<artifactId>/pfx'. There is no per-game compatibility tool setting.


def get_epic_dir_from_install_dir(install_dir: str) -> str:
    """ Returns the Epic Games Launcher data directory for the runtime install directory, e.g. '~/.local/share/com.epicgames.eglv2' """

    return os.path.abspath(os.path.join(os.path.expanduser(install_dir), '../..'))


def is_epic_launcher(launcher: str) -> bool:
    """ Returns True if the supplied launcher name is the Epic Games Launcher """

    return launcher == 'epicgames'


def load_epic_json(path: str) -> dict[str, Any]:
    """ Returns the JSON object stored at 'path', or an empty dict if the file is missing, unreadable or not a JSON object """

    if not os.path.isfile(path):
        return {}

    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, ValueError) as e:  # ValueError includes JSONDecodeError and UnicodeDecodeError
        print(f'Could not read Epic Games Launcher file \'{path}\': {e}')
        return {}

    return data if isinstance(data, dict) else {}


def get_epic_runtimes(epic_dir: str) -> list[str]:
    """ Returns the folder names of all Proton runtimes installed in '<epic_dir>/compat/runtime', e.g. ['GE-Proton10-34'] """

    runtime_dir = os.path.join(epic_dir, 'compat', 'runtime')
    if not os.path.isdir(runtime_dir):
        return []

    return [d for d in os.listdir(runtime_dir) if os.path.isfile(os.path.join(runtime_dir, d, 'proton'))]


def get_epic_pinned_runtime(epic_dir: str) -> str:
    """
    Returns the folder name of the installed Proton runtime that the Epic Games Launcher uses for all Windows games, e.g. 'GE-Proton10-34'.
    Returns an empty string if it cannot be determined.
    """

    runtimes = get_epic_runtimes(epic_dir)

    version = load_epic_json(os.path.join(epic_dir, 'compat', 'runtime', 'pin-cache.json')).get('version', '')
    if version in runtimes:
        return version

    # Pinned version is unknown or not installed (yet): If there is only one runtime installed, the launcher has to use that one
    if len(runtimes) == 1:
        return runtimes[0]

    return ''


def get_epic_game_titles(epic_dir: str) -> dict[str, str]:
    """ Returns a dict mapping the catalog item id to the game title, read from the launcher's catalog cache """

    catalog_items = load_epic_json(os.path.join(epic_dir, 'cache', 'prod', 'catalog-cache.json')).get('items', {})
    if not isinstance(catalog_items, dict):
        return {}

    titles: dict[str, str] = {}
    for item_id, entry in catalog_items.items():
        item = entry.get('item') if isinstance(entry, dict) else None
        if isinstance(item, dict) and isinstance(item.get('title'), str):
            titles[item_id] = item['title']

    return titles


def get_epic_game_list(epic_dir: str, pinned_runtime: str | None = None, with_titles: bool = True) -> list[EpicGame]:
    """
    Returns a list of installed games for the Epic Games Launcher at 'epic_dir' (e.g. '~/.local/share/com.epicgames.eglv2')
    pinned_runtime: Proton runtime used by Windows games, determined with get_epic_pinned_runtime if None
    with_titles: Look up game titles in the catalog cache, otherwise the install folder name is used as title
    Return Type: list[EpicGame]
    """

    installations_path = os.path.join(epic_dir, 'installations.jsonl')
    if not os.path.isfile(installations_path):
        return []

    # installations.jsonl is an append-only journal: the first line is a header, every other line is a full
    # snapshot of one installation. The last snapshot for an installationId is the current state.
    installations: dict[str, dict[str, Any]] = {}
    try:
        with open(installations_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if isinstance(entry, dict) and isinstance(entry.get('installationId'), str):
                    installations[entry['installationId']] = entry
    except (OSError, ValueError) as e:
        print(f'Could not read Epic Games Launcher installations \'{installations_path}\': {e}')
        return []

    titles = get_epic_game_titles(epic_dir) if with_titles else {}
    if pinned_runtime is None:
        pinned_runtime = get_epic_pinned_runtime(epic_dir)

    def get_str(entry: dict[str, Any], key: str) -> str:
        value = entry.get(key)
        return value if isinstance(value, str) else ''

    egs: list[EpicGame] = []
    for installation_id, entry in installations.items():
        install_path = get_str(entry, 'dir')
        if entry.get('complete') is not True or not install_path or not os.path.isdir(install_path):
            continue

        eg = EpicGame()

        eg.installation_id = installation_id
        eg.namespace = get_str(entry, 'namespace')
        eg.item_id = get_str(entry, 'itemId')
        eg.artifact_id = get_str(entry, 'artifactId')
        eg.install_path = install_path
        eg.platform = get_str(entry, 'platform').capitalize()
        eg.executable = get_str(entry, 'launchExecutable')
        eg.version = get_str(entry, 'version')
        eg.title = titles.get(eg.item_id, '') or os.path.basename(os.path.normpath(install_path))
        eg.epic_dir = epic_dir
        eg.compat_tool = pinned_runtime if eg.is_windows() else ''

        egs.append(eg)

    return egs
