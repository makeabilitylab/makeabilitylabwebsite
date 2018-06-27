from website.models import Publication
from django.test import TestCase
from website.test_cases.helper_functions import *


class PublicationsTest(TestCase):
    def test_pubs_exist(self):
        self.assertNotEqual(Publication.objects.all().count(), 0, 'no publications!')

    def test_pubs_pdf_exist(self):
        for pub in Publication.objects.all():
            self.assertNotEqual(pub.pdf_file, None, 'pdf for publication ' + pub.title + ' does not exist!')

    def test_pubs_video_exist(self):
        for pub in Publication.objects.all():
            self.assertEqual(check_site_exist(pub.video.video_url), True, 'video url for publication ' + pub.title + ' returns error')

    def test_pubs_thumbnail_exist(self):
        for pub in Publication.objects.all():
            self.assertNotEqual(pub.thumbnail, None, 'thumbnail for publication ' + pub.title + ' does not exist!')








