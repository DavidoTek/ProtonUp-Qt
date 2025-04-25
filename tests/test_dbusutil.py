import pupgui2.dbusutil  # needed for spies

import pytest

from pytest_mock import MockerFixture

from PySide6.QtDBus import QDBusMessage, QDBusConnection

from pupgui2.dbusutil import *

from pupgui2.constants import DBUS_DOWNLOAD_OBJECT_BASEPATH, DBUS_APPLICATION_URI


def test_create_and_send_dbus_message(mocker: MockerFixture) -> None:

    """
    Given a valid DBus bus Connection,
    When a message is constrtucted,
    It should send the constructed message on the given bus.
    """

    session_bus_mock = mocker.spy(QDBusConnection, 'sessionBus')

    session_bus_send_mock = mocker.patch('PySide6.QtDBus.QDBusConnection.send')
    session_bus_send_mock.return_value = True

    dbus_args: dict[str, str | list[str | dict[str, str]]] = {
        'object': 'echo',
        'interface': 'net.davidotek.pupgui2.Test',
        'signal_name': 'Test',
        'arguments': [
            'application://net.davidotek.pupgui2.Test',
            {
                'test-value': '1'
            }
        ]
    }

    result: bool = create_and_send_dbus_message(
        str(dbus_args['object']),
        str(dbus_args['interface']),
        str(dbus_args['signal_name']),
        dbus_args['arguments']
    )

    session_bus_send_mock_message_arg: QDBusMessage = session_bus_send_mock.call_args[0][0]

    assert result

    session_bus_mock.assert_called_once()

    session_bus_send_mock.assert_called_once()

    assert session_bus_send_mock.return_value

    assert isinstance(session_bus_send_mock_message_arg, QDBusMessage)

    assert session_bus_send_mock_message_arg.path() == os.path.join(DBUS_DOWNLOAD_OBJECT_BASEPATH, str(dbus_args['object']))
    assert session_bus_send_mock_message_arg.interface() == dbus_args['interface']
    assert session_bus_send_mock_message_arg.member() == dbus_args['signal_name']
    assert session_bus_send_mock_message_arg.arguments() == dbus_args['arguments']


def test_create_and_send_dbus_message_bus_not_connected(mocker: MockerFixture) -> None:

    """
    Given that `DBusConnection` fails to any event bus,
    When the connection query for `isConnected()` is `False`,
    Then we should return `False`,
    And not send a message.
    """

    session_bus_isConnected_mock = mocker.patch('PySide6.QtDBus.QDBusConnection.isConnected')
    session_bus_isConnected_mock.return_value = False

    session_bus_send_mock = mocker.patch('PySide6.QtDBus.QDBusConnection.send')
    session_bus_send_mock.return_value = False

    result: bool = create_and_send_dbus_message('', '', '', [])

    assert not result

    session_bus_isConnected_mock.assert_called_once()

    session_bus_send_mock.assert_not_called()


@pytest.mark.parametrize(
    'progress, count, should_progress_be_visible, should_count_be_visible', [
        pytest.param(0.1, 1, True, True, id = 'Progress (1%) should be visible, Count (1) should be visible'),
        pytest.param(1, 0, False, False, id = 'Progress (100%) should not be visible, Count (0) should not be visible'),
        pytest.param(0, 0, True, False, id = 'Progress (0%) should be visible, Count (0) should not be visible'),
        pytest.param(1, 1, False, True, id = 'Progress (100%) should not be visible, Count (1) should be visible'),

        pytest.param(100, 1, False, True, id = 'Progress (10,000%) should not be visible, Count (1) should be visible'),
        pytest.param(-1, 1, False, True, id = 'Progress (-100%) should not be visible, Count (1) should be visible'),
        pytest.param(1, -1, False, False, id = 'Progress (100%) should not be visible, Count (-1) should not be visible'),
    ]
)
def test_dbus_progress_message(progress: float, count: int, should_count_be_visible: bool, should_progress_be_visible: bool, mocker: MockerFixture) -> None:

    """
    Given a valid DBus bus Connection,
    When a progress message is sent with a given progress and count,
    Then we should send a valid DBus message on the expected progress bus,
    And it should contain the expected progress values
    And the count and progress visibility should match the expected values
    """

    session_bus_mock = mocker.spy(QDBusConnection, 'sessionBus')

    session_bus_send_mock = mocker.patch('PySide6.QtDBus.QDBusConnection.send')
    session_bus_send_mock.return_value = True

    create_and_send_dbus_message_spy = mocker.spy(pupgui2.dbusutil, 'create_and_send_dbus_message')

    expected_dbus_message_attrs = {
        'object': 'Update',
        'interface': 'com.canonical.Unity.LauncherEntry',
        'signal': 'Update',
        'arguments': [
            DBUS_APPLICATION_URI,
            {
                'progress': progress,
                'progress-visible': should_progress_be_visible,
                'count': count,
                'count-visible': should_count_be_visible,
            }
        ]
    }

    result: bool = dbus_progress_message(
        progress,
        count
    )

    create_and_send_dbus_message_spy_call_args = create_and_send_dbus_message_spy.call_args[0][:4]

    assert result

    assert create_and_send_dbus_message_spy_call_args == (
        expected_dbus_message_attrs['object'],
        expected_dbus_message_attrs['interface'],
        expected_dbus_message_attrs['signal'],
        expected_dbus_message_attrs['arguments']
    )

    session_bus_mock.assert_called_once()

    session_bus_send_mock.assert_called_once()
