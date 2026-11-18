# pupgui2 window utilities
# Remember the main window's size, position and maximized state between runs (#449)

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QWidget

from pupgui2.util import config_window_geometry


def save_window_geometry(window: QWidget, window_name: str) -> None:
    """
    Store the size, position and maximized state of window.
    When the window is maximized, its normal (un-maximized) geometry is stored, so restoring
    and then un-maximizing gives back the size the user picked.
    """

    maximized = window.isMaximized()
    geometry = window.normalGeometry() if maximized else window.geometry()

    values: dict[str, int | bool] = {'maximized': maximized}
    if geometry.isValid():
        # move() places the frame, while geometry() is the area inside it: store the frame's position
        # so the window doesn't drift by the title bar height on every start
        position = geometry.topLeft() - (window.geometry().topLeft() - window.frameGeometry().topLeft())
        values.update({'posx': position.x(), 'posy': position.y(), 'width': geometry.width(), 'height': geometry.height()})

    config_window_geometry(window_name, values)


def restore_window_geometry(window: QWidget, window_name: str) -> None:
    """
    Apply the stored size and maximized state to window before it is shown.
    The position is only restored on X11: Wayland compositors decide where windows go.
    """

    stored = config_window_geometry(window_name)

    width, height = stored.get('width', 0), stored.get('height', 0)
    if width > 0 and height > 0:
        screen = window.screen() or QGuiApplication.primaryScreen()
        if screen:  # don't open bigger than the screen, e.g. after moving from a larger monitor
            available = screen.availableGeometry()
            width, height = min(width, available.width()), min(height, available.height())
        window.resize(width, height)

    if QGuiApplication.platformName() == 'xcb' and 'posx' in stored and 'posy' in stored:
        position = QPoint(stored['posx'], stored['posy'])
        if QGuiApplication.screenAt(position):  # skip positions on a monitor that is gone
            window.move(position)

    if stored.get('maximized'):
        window.setWindowState(window.windowState() | Qt.WindowState.WindowMaximized)
