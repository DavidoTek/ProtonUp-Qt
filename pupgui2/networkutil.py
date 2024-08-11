import os
from PySide6.QtCore import Property
import requests

from typing import Callable


def download_file(url: str, destination: str, progress_callback: Callable[[int], None] | Callable[..., None] = lambda *args, **kwargs: None, download_cancelled: Property | None = None, buffer_size: int = 65536, stream: bool = True, known_size: int = 0):
    """
    Download a file from a given URL using `requests` to a destination directory with download progress, with some optional parameters:
    * `progress_callback`: Function or Lambda that gets called with the download progress each time it changes
    * `download_cancelled`: Qt Property that can stop the download
    * `buffer_size`: Size of chunks to download the file in
    * `stream`: Lazily parse response - If response headers won't contain `'Content-Length'` and the file size is not known ahead of time, set this to `False` to get file size from response content length
    * `known_size`: If size is known ahead of time, this can be given to calculate download progress in place of Content-Length header (e.g. where it may be missing)

    Returns `True` if download succeeds, `False` otherwise.

    Raises: `OSError`, `requests.ConnectionError`, `requests.Timeout`
    Return Type: bool
    """

    # Try to get the data for the file we want
    try:
        response: requests.Response = requests.get(url, stream=stream)
    except (OSError, requests.ConnectionError, requests.Timeout) as e:
        print(f"Error: Failed to make request to URL '{url}', cannot complete download! Reason: {e}")
        raise e

    progress_callback(1)  # 1 = download started

    # Figure out file size for reporting download progress    
    if stream and response.headers.get('Transfer-Encoding', '').lower() == 'chunked':
        print("Warning: Using 'stream=True' in request but 'Transfer-Encoding' in Response is 'Chunked', so we may not get 'Content-Length' to parse file size!")

    # Sometimes ctmods can have access to the asset size, so they can give it to us
    # If it is not specified, or if it is zero/Falsey, try to get it from the response
    file_size = known_size
    if not known_size:
        file_size = int(response.headers.get('Content-Length', 0))

        # Sometimes Content-Length is not sent (such as for DXVK Async), so use response length in that case
        # See: https://stackoverflow.com/questions/53797628/request-has-no-content-length#53797919
        #
        # Only get response.content if we aren't streaming so that we don't hold up the entire function,
        # and defeating the point of streaming to begin with
        if not stream:
            file_size = len(response.content)

    if file_size <= 0:
        print('Warning: Failed to get file size, the progress bar may not display accurately!')

    if buffer_size <= 0:
        print(f"Warning: Buffer Size was '{buffer_size}', defaulting to '65536'")
        buffer_size = 65536

    # NOTE: If we don't get a known_size or if we can't get the size from Cotent-Length or the response size,
    #       we cannot report download progress!
    #
    #       Right now, only GitLab doesn't give us Content-Length because it uses Chunked Transfer-Encoding,
    #       but ctmods should be able to get the size and pass it as known_size.
    #
    #       If we ever make it this far without a file_size (e.g. we are stream=True and we don't get a
    #       Content-Length, or len(response.content) is 0), then then the progress bar will stall at 1% until
    #       the download finishes where it will jump to 99%, until extraction completes.
    try:
        chunk_count = int(file_size / buffer_size)
    except ZeroDivisionError as e:
        print(f'Error: Could not calculate chunk_count, {e}')
        print('Defaulting to chunk count of 1')
        chunk_count = 1

    current_chunk = 1

    # Get download filepath and download directory path without filename
    destination_file_path: str = os.path.expanduser(destination)
    destination_dir_path: str = os.path.dirname(destination_file_path)

    # Create download path if it doesn't exist (and make sure we have permission to do so)
    try:
        os.makedirs(destination_dir_path, exist_ok=True)
    except OSError as e:
        print(f'Error: Failed to create path to destination directory, cannot complete download! Reason: {e}')
        raise e
    
    # Download file and return progress to any given callback
    with open(destination, 'wb') as destination_file:
        for chunk in response.iter_content(chunk_size=buffer_size):
            chunk: bytes

            if download_cancelled:
                progress_callback(-2)  # -2 = Download cancelled
                return False

            if not chunk:
                continue

            _ = destination_file.write(chunk)
            destination_file.flush()

            download_progress = int(min(current_chunk / chunk_count * 98.0, 98.0))  # 1...98 = Download in progress
            progress_callback(download_progress)

            current_chunk += 1

    progress_callback(99)  # 99 = Download completed successfully
    return True

