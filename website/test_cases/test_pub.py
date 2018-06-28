from website.models import Publication, Video
from django.test import TestCase
from website.test_cases.helper_functions import *
from django.core.files import File


class PublicationsTest(TestCase):
    def setUp(self):
        # get the pdf from the testData folder under media,
        paths = get_files_in_dir_in_media('.pdf', 'testData/testPDFs')

        mock_vid = None

        for path in paths:
            pdf_test = File(open(path, 'rb'))
            mock_pub = Publication.objects.create(title='TestPublication', geo_location=None, book_title=None,
                                                  book_title_short=None, num_pages=None,
                                                  pub_venue_type=None, peer_reviewed=None,
                                                  total_papers_accepted=None,
                                                  total_papers_submitted=None, award=None, pdf_file=pdf_test,
                                                  date=None, video=mock_vid, series=None, isbn=None, doi=None,
                                                  publisher=None, publisher_address=None, acmid=None,
                                                  page_num_start=None, page_num_end=None, official_url='')
            mock_pub.save()
            pdf_test.close()

    def test_pubs_exist(self):
        self.assertNotEqual(Publication.objects.all().count(), 0, 'no publications!')

    def test_pubs_pdf_exist(self):
        for pub in Publication.objects.all():
            self.assertEqual(check_site_exist(pub.official_url), True, 'pdf official url for publication ' + pub.title + ' returns error')

    def test_pubs_video_exist(self):
        for pub in Publication.objects.all():
            self.assertIsNotNone(pub.video, 'video for publication ' + pub.title + ' is null!')
            self.assertEqual(check_site_exist(pub.video.video_url), True, 'video url for publication ' + pub.title + ' returns error')

    def test_pubs_thumbnail_exist(self):
        for pub in Publication.objects.all():
            self.assertNotEqual(pub.thumbnail, None, 'thumbnail for publication ' + pub.title + ' does not exist!')








