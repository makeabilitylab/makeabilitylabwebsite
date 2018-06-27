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

def get_files_in_dir_in_testData(filetype, dir):
    dir_file = './media/' + dir + '/*' + filetype
    try:
        return glob.glob(dir_file)
    except FileNotFoundError:
        print("Please check your file extension or dir")
    return None
