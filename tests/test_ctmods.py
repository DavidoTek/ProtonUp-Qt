from PySide6.QtWidgets import QApplication

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
