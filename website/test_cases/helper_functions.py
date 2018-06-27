import requests


def check_site_exist(url):
    try:
        site_ping = requests.head(url)
        if site_ping.status_code < 400:
            return True
        else:
            return False
    except Exception:
        return False
