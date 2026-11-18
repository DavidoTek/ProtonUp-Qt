from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QWidget

from pupgui2.util import config_window_geometry


def save_window_geometry(window: QWidget, window_name: str) -> None:
    """
    Store the size, position and maximized state of window.
    When the window is maximized, only its normal (un-maximized) size and the maximized flag are stored,
    so restoring and then un-maximizing gives back the size the user picked. The position from the last
    un-maximized close is kept, as the frame of a maximized window can differ from a normal one.
    """

    if window.isMaximized():
        geometry = window.normalGeometry()
        values: dict[str, int | bool] = {'maximized': True}
        if geometry.isValid():
            values.update({'width': geometry.width(), 'height': geometry.height()})
    else:
        geometry = window.geometry()
        # move() places the frame, while geometry() is the area inside it: store the frame's position
        # so the window doesn't drift by the title bar height on every start
        position = window.frameGeometry().topLeft()
        values = {'maximized': False, 'posx': position.x(), 'posy': position.y(), 'width': geometry.width(), 'height': geometry.height()}

    config_window_geometry(window_name, values)


def restore_window_geometry(window: QWidget, window_name: str) -> None:
    """
    Apply the stored size and maximized state to window before it is shown.
    The position is only restored on X11: Wayland compositors decide where windows go.
    """

    stored = config_window_geometry(window_name)

    position = None
    screen = window.screen() or QGuiApplication.primaryScreen()
    if QGuiApplication.platformName() == 'xcb' and 'posx' in stored and 'posy' in stored:
        position = QPoint(stored['posx'], stored['posy'])
        position_screen = QGuiApplication.screenAt(position)
        if position_screen is not None:
            screen = position_screen
        else:  # skip positions on a monitor that is gone
            position = None

    width, height = stored.get('width', 0), stored.get('height', 0)
    if width > 0 and height > 0:
        if screen:  # don't open bigger than the screen, e.g. after moving from a larger monitor
            available = screen.availableGeometry()
            width, height = min(width, available.width()), min(height, available.height())
        window.resize(width, height)

    if position is not None:
        window.move(position)

    if stored.get('maximized'):
        window.setWindowState(window.windowState() | Qt.WindowState.WindowMaximized)
