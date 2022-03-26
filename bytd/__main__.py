import typing as t

from piped_api import PipedClient


CLIENT = PipedClient()
TO_DOWNLOAD = (video_id.strip() for video_id in open('video_ids.txt', 'r'))



def get_stream_urls(video_id: str, type: t.Literal['autio', 'video']='audio'):
    """
        Get audio streams from video id
    """

    return CLIENT.get_video(video_id).get_streams(type=type)
