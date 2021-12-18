"""
Hosts general utility functions for Makeability Lab Django website
"""

def get_video_embed(video_url):
    """Returns proper embed code for a video url"""

    if 'youtu.be' in video_url or 'youtube.com' in video_url:
        # https://youtu.be/i0IDbHGir-8 or https://www.youtube.com/watch?v=i0IDbHGir-8

        base_url = "https://youtube.com/embed"
        unique_url = video_url[video_url.find("/", 9):]

        # See https://developers.google.com/youtube/youtube_player_demo for details on parameterizing YouTube video
        return base_url + unique_url + "?showinfo=0&iv_load_policy=3"
    elif 'vimeo' in video_url:
        # https://player.vimeo.com/video/164630179
        vimeo_video_id = video_url.rsplit('/', 1)[-1]
        return "https://player.vimeo.com/video/" + vimeo_video_id
    else:
        return "unknown video service for '{}'".format(video_url)