import requests
import glob
import re


def check_site_exist(url):
    try:
        site_ping = requests.head(url)
        if site_ping.status_code < 400:
            return True
        else:
            return False
    except Exception:
        return False


def get_files_in_dir_in_media(filetype, dir):
    dir_file = './media/' + dir + '/*' + filetype
    try:
        return glob.glob(dir_file)
    except FileNotFoundError:
        print("Please check your file extension or dir")
    return None

def get_working_youtube_video_url():
    return "https://www.youtube.com/watch?v = beb8zCGMsbI"

def get_working_url():
    return "https://www.google.com"

def get_404_url():
    return "https://www.google.com/0"


