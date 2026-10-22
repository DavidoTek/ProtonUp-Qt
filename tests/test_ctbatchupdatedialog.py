import pathlib

from PySide6.QtWidgets import QApplication
from pytest_mock import MockerFixture

from pupgui2.pupgui2ctbatchupdatedialog import PupguiCtBatchUpdateDialog


def test_batch_update_dialog_lists_lowercase_proton(tmp_path: pathlib.Path, mocker: MockerFixture) -> None:

    """
    Test that compatibility tools with a lowercase 'proton' in their name, like Proton-CachyOS, can be selected.
    """

    for folder in ['GE-Proton11-1', 'proton-cachyos-11.0-20261015-slr-x86_64', 'SteamTinkerLaunch']:
        (tmp_path / folder).mkdir()

    mocker.patch('pupgui2.pupgui2ctbatchupdatedialog.install_directory', return_value=str(tmp_path))
    mocker.patch('pupgui2.pupgui2ctbatchupdatedialog.is_steam_running', return_value=False)

    app = QApplication()

    dialog = PupguiCtBatchUpdateDialog(current_ctool_name='GE-Proton11-1')
    combobox = dialog.ui.comboNewCtool

    assert [combobox.itemText(i) for i in range(combobox.count())] == ['proton-cachyos-11.0-20261015-slr-x86_64']
    assert dialog.ui.btnBatchUpdate.isEnabled()

    dialog.ui.close()
    QApplication.shutdown(app)
