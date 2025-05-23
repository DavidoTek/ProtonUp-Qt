import pytest

from pupgui2.constants import POSSIBLE_INSTALL_LOCATIONS

from pupgui2.heroicutil import *

KNOWN_HEROIC_LAUNCHERS = ['heroicwine', 'heroicproton']

@pytest.mark.parametrize('launcher, expected_heroic_launcher', [
    *[pytest.param(install_loc.get('launcher'), install_loc.get('launcher') in KNOWN_HEROIC_LAUNCHERS, id = install_loc.get('display_name')) for install_loc in POSSIBLE_INSTALL_LOCATIONS]
])
def test_is_heroic_launcher(launcher: str, expected_heroic_launcher: bool) -> None:

    result: bool = is_heroic_launcher(launcher)

    assert result == expected_heroic_launcher
