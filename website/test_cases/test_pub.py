from website.models import Publication
from django.test import TestCase
import requests


class PublicationsTest(TestCase):
    def test_pubs_exist(self):
        self.assertNotEqual(Publication.objects.all().count(), 0, 'no publications!')
        for pub in Publication.objects.all():
            self.assertNotEqual(pub.pdf_file, None, 'pdf for publication ' + pub.title + ' is missing!')


def check_site_exist(url):
    try:
        site_ping = requests.head(url)
        if site_ping.status_code < 400:
            return True
        else:
            return False
    except Exception:
        return False
