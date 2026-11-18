from pytest_mock import MockerFixture

from PySide6.QtCore import QPoint, QRect, Qt

from pupgui2.windowutil import save_window_geometry, restore_window_geometry


def mock_screen(mocker: MockerFixture, width: int, height: int):
    screen = mocker.MagicMock()
    screen.availableGeometry.return_value = QRect(0, 0, width, height)
    return screen


def test_save_window_geometry(mocker: MockerFixture) -> None:

    """
    Given a window that is not maximized,
    When saving its geometry,
    Then it should store the position of its frame, the size inside it and maximized = False.
    """

    config_window_geometry_mock = mocker.patch('pupgui2.windowutil.config_window_geometry')

    window = mocker.MagicMock()
    window.isMaximized.return_value = False
    window.geometry.return_value = QRect(52, 62, 700, 500)
    window.frameGeometry.return_value = QRect(50, 40, 704, 524)

    save_window_geometry(window, 'main')

    config_window_geometry_mock.assert_called_once_with('main', {'maximized': False, 'posx': 50, 'posy': 40, 'width': 700, 'height': 500})


def test_save_window_geometry_maximized(mocker: MockerFixture) -> None:

    """
    Given a maximized window,
    When saving its geometry,
    Then it should store maximized = True and its normal size, but not its position.
    """

    config_window_geometry_mock = mocker.patch('pupgui2.windowutil.config_window_geometry')

    window = mocker.MagicMock()
    window.isMaximized.return_value = True
    window.normalGeometry.return_value = QRect(10, 20, 640, 480)

    save_window_geometry(window, 'main')

    config_window_geometry_mock.assert_called_once_with('main', {'maximized': True, 'width': 640, 'height': 480})


def test_restore_window_geometry_wayland(mocker: MockerFixture) -> None:

    """
    Given a stored geometry larger than the screen,
    When restoring it on Wayland,
    Then it should resize the window clamped to the screen, not move it, and maximize it.
    """

    mocker.patch('pupgui2.windowutil.config_window_geometry', return_value={'posx': 100, 'posy': 50, 'width': 1920, 'height': 1080, 'maximized': True})
    qguiapplication_mock = mocker.patch('pupgui2.windowutil.QGuiApplication')
    qguiapplication_mock.platformName.return_value = 'wayland'

    window = mocker.MagicMock()
    window.screen.return_value = mock_screen(mocker, 1280, 720)
    window.windowState.return_value = Qt.WindowState.WindowNoState

    restore_window_geometry(window, 'main')

    window.resize.assert_called_once_with(1280, 720)
    window.move.assert_not_called()
    window.setWindowState.assert_called_once_with(Qt.WindowState.WindowMaximized)


def test_restore_window_geometry_x11(mocker: MockerFixture) -> None:

    """
    Given a stored position on a second, larger screen,
    When restoring it on X11,
    Then it should clamp the size to that screen and move the window there.
    """

    mocker.patch('pupgui2.windowutil.config_window_geometry', return_value={'posx': 3000, 'posy': 100, 'width': 1920, 'height': 1080, 'maximized': False})
    qguiapplication_mock = mocker.patch('pupgui2.windowutil.QGuiApplication')
    qguiapplication_mock.platformName.return_value = 'xcb'
    qguiapplication_mock.screenAt.return_value = mock_screen(mocker, 2560, 1440)

    window = mocker.MagicMock()
    window.screen.return_value = mock_screen(mocker, 1280, 720)

    restore_window_geometry(window, 'main')

    window.resize.assert_called_once_with(1920, 1080)
    window.move.assert_called_once_with(QPoint(3000, 100))
    window.setWindowState.assert_not_called()


def test_restore_window_geometry_x11_origin(mocker: MockerFixture) -> None:

    """
    Given a stored position at the top left corner (0, 0),
    When restoring it on X11,
    Then it should still move the window there.
    """

    mocker.patch('pupgui2.windowutil.config_window_geometry', return_value={'posx': 0, 'posy': 0, 'width': 800, 'height': 600})
    qguiapplication_mock = mocker.patch('pupgui2.windowutil.QGuiApplication')
    qguiapplication_mock.platformName.return_value = 'xcb'
    qguiapplication_mock.screenAt.return_value = mock_screen(mocker, 1920, 1080)

    window = mocker.MagicMock()

    restore_window_geometry(window, 'main')

    window.move.assert_called_once_with(QPoint(0, 0))


def test_restore_window_geometry_x11_screen_gone(mocker: MockerFixture) -> None:

    """
    Given a stored position on a screen that is no longer connected,
    When restoring it on X11,
    Then it should only resize the window, clamped to its current screen.
    """

    mocker.patch('pupgui2.windowutil.config_window_geometry', return_value={'posx': 3000, 'posy': 100, 'width': 1920, 'height': 1080})
    qguiapplication_mock = mocker.patch('pupgui2.windowutil.QGuiApplication')
    qguiapplication_mock.platformName.return_value = 'xcb'
    qguiapplication_mock.screenAt.return_value = None

    window = mocker.MagicMock()
    window.screen.return_value = mock_screen(mocker, 1280, 720)

    restore_window_geometry(window, 'main')

    window.resize.assert_called_once_with(1280, 720)
    window.move.assert_not_called()


def test_restore_window_geometry_nothing_stored(mocker: MockerFixture) -> None:

    """
    Given no stored geometry,
    When restoring it,
    Then it should leave the window at its default size.
    """

    mocker.patch('pupgui2.windowutil.config_window_geometry', return_value={})
    window = mocker.MagicMock()

    restore_window_geometry(window, 'main')

    window.resize.assert_not_called()
    window.move.assert_not_called()
    window.setWindowState.assert_not_called()
