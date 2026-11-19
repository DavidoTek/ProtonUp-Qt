import hashlib
import importlib
import pathlib

from collections.abc import Generator
from unittest.mock import MagicMock

import pytest

from pytest_mock import MockerFixture

from PySide6.QtWidgets import QApplication, QMessageBox

from pupgui2.ctloader import CtLoader


class DummyMainWindow:
    """ Dummy MainWindow object for the CtLoader test. Works thanks to duck typing. """

    def __init__(self, web_access_tokens: dict[str, str]) -> None:
        self.web_access_tokens = web_access_tokens


def test_ctmod_loader() -> None:
    """
    Test loading of ctmods using CtLoader.
    """
    app = QApplication()
    
    dummy_main_window = DummyMainWindow({})

    ct_loader = CtLoader(main_window=dummy_main_window)

    # Ensure that ctmods are loaded successfully
    assert(ct_loader.load_ctmods() is True)

    # Ensure that ctmods are loaded (assume at least one ctmod is exists)
    assert(len(ct_loader.get_ctmods()) > 0)
    assert(len(ct_loader.get_ctobjs()) > 0)

    # Ensure that no advanced mode ctmods are loaded when advanced_mode is False
    assert(all(["advmode" not in ctmod.CT_LAUNCHERS for ctmod in ct_loader.get_ctmods(launcher=None, advanced_mode=False)]))

    QApplication.shutdown(app)


@pytest.fixture(scope='function')
def qapp() -> Generator[QApplication]:
    app = QApplication()
    yield app
    QApplication.shutdown(app)


@pytest.mark.parametrize('ctmod_name, get_data_attr', [
    ('ctmod_00protonge', '_CtInstaller__get_data'),
    ('ctmod_dwproton', '_get_dw_data'),
])
def test_get_tool_checksum_mismatch(ctmod_name: str, get_data_attr: str, tmp_path: pathlib.Path, mocker: MockerFixture, qapp: QApplication) -> None:
    """
    Test that a download failing its checksum reports an error instead of leaving the progress bar at 99%.
    """
    ctmod = importlib.import_module(f'pupgui2.resources.ctmods.{ctmod_name}')
    installer = ctmod.CtInstaller(DummyMainWindow({}))

    progress: list[int] = []
    message_boxes: list[tuple] = []
    installer.download_progress_percent.connect(progress.append)
    installer.message_box_message.connect(lambda *args: message_boxes.append(args))

    data = {'version': 'Proton-1', 'download': 'https://example.com/Proton-1.tar.gz', 'checksum': 'https://example.com/Proton-1.sha512sum'}
    mocker.patch.object(installer, get_data_attr, return_value=(data, None))

    installer.rs = MagicMock()
    installer.rs.get.return_value.text = f'{hashlib.sha512(b"expected").hexdigest()}  Proton-1.tar.gz\n'

    def download(url: str, destination: str, known_size: int = 0) -> bool:
        installer._CtInstaller__set_download_progress_percent(1)
        pathlib.Path(destination).write_bytes(b'corrupted')
        installer._CtInstaller__set_download_progress_percent(99)
        return True

    mocker.patch.object(installer, '_CtInstaller__download', side_effect=download)
    extract_tar = mocker.patch(f'pupgui2.resources.ctmods.{ctmod_name}.extract_tar')

    assert installer.get_tool('Proton-1', str(tmp_path / 'install'), str(tmp_path)) is False

    extract_tar.assert_not_called()
    assert progress == [1, 99, -1]
    assert len(message_boxes) == 1
    assert message_boxes[0][2] == QMessageBox.Icon.Warning
    assert 'Proton-1.tar.gz' in message_boxes[0][1]
