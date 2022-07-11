import typing as t

import typer
import aiohttp
import aiofile

from asyncio import Semaphore, sleep, run, wait_for, gather, set_event_loop_policy, WindowsSelectorEventLoopPolicy
from functools import wraps
from pathlib import Path

from piped_api import PipedClient
from piped_api.client import APIError


CLIENT = PipedClient()
"""A Piped client."""

ROOT_PATH = Path(__file__).parent
"""Root path of the project."""
TO_DOWNLOAD_PATH = ROOT_PATH / 'to_download.txt'
"""A list of YouTube IDs to download."""
DOWNLOAD_INTO = ROOT_PATH / 'downloaded'
"""To what folder should the files be downloaded?"""
DOWNLOAD_MB = 5
"""How much MB to process per download chunk? Choose your average download speed: lower or higher values will make download slower."""
MAX_TASKS = 5
"""Maximum number of concurrent downloads."""

TO_DOWNLOAD = set(video_id.strip() for video_id in open(TO_DOWNLOAD_PATH, 'r'))
"""List of YouTube IDs to download"""



def get_stream(video_id: str, stream_type: t.Literal['audio', 'video']='audio') -> t.Optional[t.Tuple[str, str]]:
    """
        Get the best stream from YouTube video ID.

        Returns a tuple of `(<video title>, stream_url)`.

        ### Parameters:
        - `video_id` - The ID of the YouTube video.
        - `type` - The type of stream to obtain.
    """

    try:
        video = CLIENT.get_video(video_id)

    except APIError as api_error:
        print(f'Video "{video_id}" couldn\'t be obtained: {str(api_error).splitlines()[0]}')
        return None

    to_sort = [stream for stream in video.get_streams(stream_type) if stream.mime_type == f'{stream_type}/mp4' and stream.video_only == False]

    return f"{video.uploader} - {video.title}", sorted(to_sort, key=lambda stream: stream.quality)[0].url



async def download(url: str, session: aiohttp.ClientSession, semaphore: Semaphore, download_to: Path):
    async with semaphore:
        async with session.get(url) as response:
            async with aiofile.async_open(download_to, 'wb') as f:
                typer.echo(f"Downloading {download_to.parts[-1]}...")

                # download file (by copilot, as if it worked at avoiding above error lol):
                # edit: no it doesn't work
                while True:
                    # FIXME: Fix stupid ClientPayloadError: Response payload is not complete
                    chunk = await response.content.read(DOWNLOAD_MB * 1024 * 1024)
                    if not chunk:
                        break
                    await f.write(chunk)
                    await sleep(0.1)



def run_async(func: t.Callable):
    @wraps(func)
    def wrapper(*args, **kwargs):
        async def coro_wrapper():
            return await func(*args, **kwargs)

        return run(coro_wrapper)

    return wrapper



def main(stream_type: str='audio'):
    async def _main():
        tasks = []
        semaphore = Semaphore(MAX_TASKS)

        async with aiohttp.ClientSession(headers={'Connection': 'keep-alive'}, timeout=aiohttp.ClientTimeout(total=60*60, sock_read=480)) as session:
            for video_id in TO_DOWNLOAD:
                packed_stream = get_stream(video_id, stream_type=stream_type)

                if packed_stream is None:
                    print(f"Couldn't obtain any stream for video ID `{video_id}`.")
                    return


                title, url = packed_stream
                download_to = DOWNLOAD_INTO / f'{title}.{"mp4" if stream_type == "video" else "mp3"}'
                if download_to.exists():
                    typer.echo(f"File {download_to.parts[-1]} already exists, skipping...")
                    continue

                tasks.append(wait_for(download(url, session, semaphore, download_to), timeout=None))

            await gather(*tasks)
        
        typer.echo(f"Done!")

    set_event_loop_policy(WindowsSelectorEventLoopPolicy())
    run(_main())



if __name__ == "__main__":
    typer.run(main)
