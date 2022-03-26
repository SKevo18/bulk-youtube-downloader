import typing as t

import requests
import os.path

from zipfile import ZipFile
from shutil import copyfileobj
from pathlib import Path

from piped_api import PipedClient
from piped_api.client import APIError


CLIENT = PipedClient()

ROOT_PATH = Path(__file__).parent
TO_DOWNLOAD_PATH = ROOT_PATH / 'to_download.txt'
DOWNLOAD_INTO = ROOT_PATH / 'downloaded'

TO_DOWNLOAD = set(video_id.strip() for video_id in open(TO_DOWNLOAD_PATH, 'r'))



def get_stream(video_id: str, type: t.Literal['autio', 'video']='audio') -> t.Optional[t.Tuple[str, str]]:
    """
        Get the best stream from YouTube video ID.

        Returns a tuple of `(video.title, stream_url)`.

        ### Parameters:
        - `video_id` - The ID of the YouTube video.
        - `type` - The type of stream to obtain.
    """

    try:
        video = CLIENT.get_video(video_id)

    except APIError as api_error:
        print(f'Video "{video_id}" couldn\'t be obtained: {str(api_error).splitlines()[0]}')
        return None

    just_mp4 = [stream for stream in video.get_streams(type=type) if stream.mime_type == f'{type}/mp4']

    return f"{video.uploader} - {video.title}", sorted(just_mp4, key=lambda stream: stream.quality)[0].url



def download_file(url: str, path: Path) -> None:
    """
        Downloads a file from `url` to `path` via [requests](https://2.python-requests.org/en/master/).

        Based on https://stackoverflow.com/a/67053532/ (thanks!).
        `urlretrive` and literally any other iterator and non-iterator based methods won't download the entire file, so I had to use an alternative approach.
    """

    total_content_size = int(requests.get(url, stream=True).headers['Content-Length'])

    if os.path.exists(path):
        temp_size = os.path.getsize(path)
        if total_content_size == temp_size:
            return

    else:
        temp_size = 0


    headers = {'Range': f'bytes={temp_size}-'}
    with requests.get(url, stream=True, headers=headers) as response:
        response.raise_for_status()

        with open(path, 'ab') as f:
            copyfileobj(response.raw, f, length=16*1024*1024)



def download_all(to_download: t.List[str]=TO_DOWNLOAD, type: str='audio') -> None:
    """
        Downloads all videos in `to_download`.

        ### Parameters:
        - `to_download` - A list of YouTube video IDs.
    """

    for video_id in to_download:
        packed_stream = get_stream(video_id, type=type)
        if packed_stream is None:
            continue

        title, url = packed_stream
        print(f'Downloading "{title}" from `{url}`...')

        download_file(url, DOWNLOAD_INTO / f'{title}.{"mp4" if type == "video" else "mp3"}')



def zip_all(*args, **kwargs):
    for file in DOWNLOAD_INTO.iterdir():
        if file.name.endswith(".mp3"):
            with ZipFile(DOWNLOAD_INTO / 'zipped' / 'audio.zip', 'w', *args, **kwargs) as zip_file:
                zip_file.write(file)

        elif file.name.endswith(".mp4"):
            with ZipFile(DOWNLOAD_INTO / 'zipped' / 'videos.zip', 'w', *args, **kwargs) as zip_file:
                zip_file.write(file)



def main():
    download_all()
    print("Downloaded all videos... zipping!")

    zip_all()
    print("Done!")



if __name__ == "__main__":
    main()
