import os
from typing import Any

from PySide6.QtDBus import QDBusConnection, QDBusMessage

from pupgui2.constants import DBUS_APPLICATION_URI, DBUS_DOWNLOAD_OBJECT_BASEPATH, DBUS_INTERFACES_AND_SIGNALS


def create_and_send_dbus_message(object: str, interface: str, signal_name: str, arguments: list[Any], bus: QDBusConnection | None = None) -> None:

    """
    Create and send a QDBusMessage over a given bus.
    If no bus is given, will default to sessionBus
    """

    if bus is None:
        bus = QDBusConnection.sessionBus()

    # i.e. /net/davidotek/pupgui2/Update
    object_path: str = os.path.join(DBUS_DOWNLOAD_OBJECT_BASEPATH, object)

    message: QDBusMessage = QDBusMessage.createSignal(object_path, interface, signal_name)
    message.setArguments(arguments)

    # Don't send the message if bus is not valid (i.e. DBus is not running)
    if bus.isConnected():
        _ = bus.send(message)


def dbus_progress_message(progress: float, count: int = 0, bus: QDBusConnection | None = None) -> None:

    """
    Create and send download progress (between 0 and 1) information with optional count parameter on a given bus.
    If no bus is given, will default to sessionBus.
    """

    if bus is None:
        bus = QDBusConnection.sessionBus()

    arguments: dict[str, Any] = {
        'progress': progress,
        'progress-visible': progress >= 0 and progress < 1,
        'count': count,
        'count-visible': count > 0
    }

    # We need to tell the 'Update' signal to update on DBUS_APPLICATION_URI,
    # plus an 'arguments' dict with some extra information
    #
    # i.e. { 'progress': 0.7, 'progress-visible': True }
    message_arguments: list[str | dict[str, Any]] = [
        DBUS_APPLICATION_URI,
        arguments
    ]

    launcher_entry_update: dict[str, str] = DBUS_INTERFACES_AND_SIGNALS['LauncherEntryUpdate']
    
    interface: str = launcher_entry_update['interface']
    signal: str = launcher_entry_update['signal']
    object = 'Update'

    create_and_send_dbus_message(object, interface, signal, message_arguments, bus=bus)


