import pathlib
import requests

import pytest
import pytest_responses

from collections.abc import Generator

from io import TextIOWrapper

from unittest.mock import call

from responses import BaseResponse, RequestsMock

from pyfakefs.fake_filesystem import FakeFilesystem
from pyfakefs.fake_file import FakeFileWrapper

from pytest_mock import MockerFixture

from pupgui2.constants import PROTONUPQT_GITHUB_URL, TEMP_DIR
from pupgui2.networkutil import *


@pytest.fixture(scope='function')
def sample_file(fs: FakeFilesystem) -> Generator[TextIOWrapper]:

    """
    Example file as a `GET` response for `download_file`.
    """

    parent_directory_path: pathlib.Path = pathlib.Path(__file__).parent

    example_response_file_path: str = os.path.join(parent_directory_path, 'fixtures', 'networkutil', 'example_file.txt')

    fs.add_real_file(example_response_file_path)

    with open(example_response_file_path, 'r') as example_response_file:
        yield example_response_file


@pytest.mark.parametrize(
    'progress_callback, buffer_size, stream, known_size, headers', [
        pytest.param(
            lambda progress: print(f'Progress is {progress}'),
            65536,
            True,
            64,  # File is 64 bytes
            { 'Content-Length': '64' },
            id = 'Happy Path with All Normal Values'
        ),

        # Varying buffer sizes
        pytest.param(
            lambda progress: print(f'Progress is {progress}'),
            4096,
            True,
            64,
            { 'Content-Length': '64' },
            id = 'buffer_size is 4096'
        ),
        pytest.param(
            lambda progress: print(f'Progress is {progress}'),
            0,
            True,
            64,
            { 'Content-Length': '64' },
            id = 'buffer_size is 0'
        ),
        pytest.param(
            lambda progress: print(f'Progress is {progress}'),
            0,
            True,
            -4096,
            { 'Content-Length': '64' },
            id = 'buffer_size is -4096'
        ),

        # Single value change
        pytest.param(
            lambda progress: print(f'Progress is {progress}'),
            65536,
            False,
            64,
            { 'Content-Length': '64' },
            id = 'stream is False'
        ),
        pytest.param(
            lambda progress: print(f'Progress is {progress}'),
            65536,
            True,
            0,
            { 'Content-Length': '64' },
            id = 'known_size is 0'
        ),
        pytest.param(
            lambda progress: print(f'Progress is {progress}'),
            65536,
            True,
            64,
            { 'Content-Length': '0' },
            id = 'Content-Length in headers is 0'
        ),
        pytest.param(
            lambda progress: print(f'Progress is {progress}'),
            65536,
            True,
            64,
            {},
            id = 'headers is {}'
        ),

        # stream=False, known_size=0, varying Content-Length
        pytest.param(
            lambda progress: print(f'Progress is {progress}'),
            65536,
            False,
            0,
            { 'Content-Length': '64' },
            id = 'stream is False, known_size is 0, Content-Length in headers is 64'
        ),
        pytest.param(
            lambda progress: print(f'Progress is {progress}'),
            65536,
            False,
            0,
            { 'Content-Length': '0' },
            id = 'stream is False, known_size is 0, Content-Length in headers is 0'
        ),
        pytest.param(
            lambda progress: print(f'Progress is {progress}'),
            65536,
            False,
            0,
            {},
            id = 'stream is False, known_size is 0, headers is {}'
        ),

        # stream=True, known_size=0, varying headers Content-Length
        pytest.param(
            lambda progress: print(f'Progress is {progress}'),
            65536,
            True,
            0,
            { 'Content-Length': '64' },
            id = 'known_size is 0, Content-Length in headers is 64'
        ),
        pytest.param(
            lambda progress: print(f'Progress is {progress}'),
            65536,
            True,
            0,
            { 'Content-Length': '0' },
            id = 'known_size is 0, Content-Length in headers is 0'
        ),
        pytest.param(
            lambda progress: print(f'Progress is {progress}'),
            65536,
            True,
            0,
            {},
            id = 'known_size is 0, headers is {}'
        ),
    ]
)
def test_download_file(progress_callback: Callable[[int], None] | Callable[..., None], buffer_size: int, stream: bool, known_size: int, headers: dict[str, str], sample_file: FakeFileWrapper, responses: RequestsMock, fs: FakeFilesystem, mocker: MockerFixture):

    """
    Given a valid URL and destination,
    When download_file attempts to download the data from a `GET` request,
    It should successfully download and write the file to the given destination.
    """

    # TODO a lto of this setup is going to be repeated, we should look to reduce it
    request_url: str = 'https://example.com'

    destination_file_path: str = os.path.join(TEMP_DIR, sample_file.file_object.name)

    progress_callback_spy = mocker.spy(progress_callback, '__call__')

    get_mock_body: str = sample_file.read()
    get_mock: BaseResponse = responses.get(
        request_url,
        body = get_mock_body,
        headers = headers
    )

    fs.create_dir(TEMP_DIR)

    result: bool = download_file(
        request_url,
        destination_file_path,
        progress_callback = progress_callback_spy,
        buffer_size = buffer_size,
        stream = stream,
        known_size = known_size
    )

    file_content: str = ''
    with open(destination_file_path, 'r') as downloaded_file:
        file_content = downloaded_file.read()

    # Figure out the chunk count to know how many times progress_callback will be called and what it will be called with

    expected_chunk_count = math.ceil(len(file_content) / (buffer_size or 65536)) or 1
    expected_progress_callback_calls = [ call(1) ]

    for chunk in range(1, expected_chunk_count + 1):
        download_progress = int(min(chunk / expected_chunk_count * 98.0, 98.0))
        expected_progress_callback_calls.append(call(download_progress))

    expected_progress_callback_calls.append( call(99) )

    assert result

    assert os.path.isfile(destination_file_path)

    assert get_mock.call_count == 1
    assert file_content == get_mock.body

    assert progress_callback_spy.call_count == len(expected_progress_callback_calls)
    progress_callback_spy.assert_has_calls(expected_progress_callback_calls)


@pytest.mark.parametrize(
    'expected_error', [
        pytest.param(requests.ConnectionError('Connection Error'), id = 'ConnectionError'),
        pytest.param(requests.Timeout('Timed Out'), id = 'Timeout'),
        pytest.param(OSError('OS Error'), id = 'OSError'),
    ]
)
def test_download_file_request_failed(responses: RequestsMock, expected_error: requests.ConnectionError | requests.Timeout | OSError) -> None:

    """
    Given a URL,
    When the `GET` request to the URL fails,
    It should raise the given exception.
    """

    get_file_mock = responses.get(PROTONUPQT_GITHUB_URL, body = expected_error)

    with pytest.raises(type(expected_error)) as raised_exception:
        _ = download_file(url = PROTONUPQT_GITHUB_URL, destination = '')

    assert raised_exception.type is type(expected_error)
    assert raised_exception.value.args[0] == expected_error.args[0]  # Check error message

    assert get_file_mock.call_count == 1
    assert get_file_mock.body == expected_error


def test_download_file_cannot_create_destination(sample_file: FakeFileWrapper, responses: RequestsMock, fs: FakeFilesystem, mocker: MockerFixture) -> None:

    """
    Given that we have successfully fetched a file to download,
    When we cannot create the directory path to write the file,
    It should raise an `OSError`.
    """

    request_url: str = 'https://example.com'

    destination_dir_path: str = os.path.join(TEMP_DIR, 'fakedir')
    destination_file_path: str = os.path.join(destination_dir_path, sample_file.file_object.name)

    get_mock_body: str = sample_file.read()
    get_mock: BaseResponse = responses.get(
        request_url,
        body = get_mock_body,
    )

    fs.create_dir(TEMP_DIR)

    os_makedirs_mock = mocker.patch('os.makedirs')
    os_makedirs_mock.side_effect = OSError('OS Error')

    with pytest.raises(OSError) as raised_exception:
        _ = download_file(
            request_url,
            destination_file_path,
        )

    assert not os.path.isdir(destination_dir_path)
    assert not os.path.isfile(destination_file_path)

    os_makedirs_mock.assert_called_once()
    os_makedirs_mock.assert_called_once_with(os.path.dirname(destination_file_path), exist_ok = True)

    assert type(os_makedirs_mock.side_effect) == raised_exception.type
    assert raised_exception.value.args[0] == os_makedirs_mock.side_effect.args[0]


def test_download_file_download_cancelled(sample_file: FakeFileWrapper, responses: RequestsMock, fs: FakeFilesystem, mocker: MockerFixture) -> None:

    """
    Given a file is successfully fetched and is being downloaded,
    When the download is cancelled,
    We should return cancelled to the `progress_callback` (`-2`)
    And return False.
    """

    request_url: str = 'https://example.com'

    destination_file_path: str = os.path.join(TEMP_DIR, sample_file.file_object.name)

    progress_callback: Callable[[int], None] = lambda progress: print(f'Progress is {progress}')
    progress_callback_spy = mocker.spy(progress_callback, '__call__')

    get_mock_body: str = sample_file.read()
    _ = responses.get(
        request_url,
        body = get_mock_body,
    )

    fs.create_dir(TEMP_DIR)

    result: bool = download_file(
        request_url,
        destination_file_path,
        progress_callback = progress_callback_spy,
        download_cancelled = Property(bool, False, None, None, "Download Cancelled")
    )

    assert not result

    assert progress_callback_spy.call_count == 2

    progress_callback_spy.assert_has_calls([ call(1), call(-2) ], any_order = False)
