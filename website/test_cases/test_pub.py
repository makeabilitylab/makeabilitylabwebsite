from website.models import Publication
from django.test import TestCase


class PublicationsTest(TestCase):
    def test_pubs_exist(self):
        self.assertNotEqual(Publication.objects.all().count(), 0, 'no publications!')
        for pub in Publication.objects.all():
            self.assertNotEqual(pub.pdf_file, None, 'pdf for publication ' + pub.title + ' is missing!')

