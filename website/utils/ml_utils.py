"""
Hosts general utility functions for Makeability Lab Django website
"""
import re

# helper function to correctly capitalize a string, specify words to not capitalize in the articles list
# from: https://stackoverflow.com/a/3729957
# Note: this code written by J. Gilkeson and needs to be cleaned up (and/or removed if no longer needed)
def capitalize_title(s, exceptions):
    word_list = re.split(' ', s)       # re.split behaves as expected
    final = [word_list[0].capitalize()]
    for word in word_list[1:]:
        final.append(word if word in exceptions else word.capitalize())
    return " ".join(final)

#Standard list of words to not capitalize in a sentence
articles = ['a', 'an', 'and', 'as', 'at', 'but', 'by', 'for', 'from', 'is', 'of', 'on', 'or', 'nor', 'the', 'to', 'up', 'yet']

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