import pytest

from pupgui2.steamutil import calc_shortcut_app_id


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
