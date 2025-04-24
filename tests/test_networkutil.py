from io import TextIOWrapper
import pathlib
import requests

import pytest
import pytest_responses

from collections.abc import Generator

from responses import BaseResponse, RequestsMock

from pyfakefs.fake_filesystem import FakeFilesystem
from pyfakefs.fake_file import FakeFileWrapper

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
        

# TODO parametrize with different streams, buffer sizes, and mocked request headers?
# Want to test the print logs as well
def test_download_file(responses: RequestsMock, sample_file: FakeFileWrapper, fs: FakeFilesystem):

    """
    Given a valid URL and destination,
    When download_file attempts to download the data from a `GET` request,
    It should successfully download and write the file to the given destination.
    """

    request_url: str = 'https://example.com'

    destination_file_path: str = os.path.join(TEMP_DIR, sample_file.file_object.name)

    progress_callback: Callable[[int], None] = lambda progress: print(f'Progress is {progress}')

    get_mock_body: str = sample_file.read()
    get_mock: BaseResponse = responses.get(
        request_url,
        body = get_mock_body,
    )

    fs.create_dir(TEMP_DIR)

    result: bool = download_file(
        request_url,
        destination_file_path,
        buffer_size = 2
    )

    file_content: str = ''
    with open(destination_file_path, 'r') as downloaded_file:
        file_content = downloaded_file.read()

    assert result

    assert os.path.isfile(destination_file_path)

    assert get_mock.call_count == 1
    assert file_content == get_mock.body

# TODO test with other types of `progress_callbacks` (None and one that takes any number of arguments?)
# TODO test with `stream` as argument and in headers as `True` and `False` in a Parametrize'd test
# TODO test file_size as zero (can go in base test and test expected chunk count / calls to progress callback?)
# TODO test buffer_size as zero  (can go in base test and test expected chunk count / calls to progress callback?)

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

    # TODO assert against the print response too

    assert raised_exception.type is type(expected_error)
    assert raised_exception.value.args[0] == expected_error.args[0]  # Check error message

    assert get_file_mock.call_count == 1
    assert get_file_mock.body == expected_error


def test_download_file_cannot_create_destination(responses: RequestsMock, fs: FakeFilesystem) -> None:

    """
    Given that we have successfully fetched a file to download,
    When we cannot create the directory path to write the file,
    It should raise an `OSError`.
    """

    pass


def test_download_file_download_cancelled() -> None:

    """
    Given a file is successfully fetched and is being downloaded,
    When the download is cancelled,
    We should return cancelled to the `progress_callback` (`-2`)
    And return False.
    """

    # TODO check that we return false
    # TODO check that progress_callback is called last with '-2'
    pass
