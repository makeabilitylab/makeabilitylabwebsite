from website.models import Video
from django.test import TestCase
from website.test_cases.helper_functions import *
from django.conf import settings


class VideoTest (TestCase):

    @classmethod
    def setUpTestData(cls):
        # only run this test data stuff if in setup
        if settings.RUN_TEST_DATA:
            with open("./media/testData/testVideos/vid_urls.txt", 'r') as fin:
                raw_lines = list(fin)
            lines = list(map(lambda s:s.strip(), raw_lines))

            counter = 0
            for line in lines:
                cls.mock_vid = Video.objects.create(video_url=line, video_preview_url=None,
                                                    title='test video ' + str(counter), caption='', date=None, project=None)
                cls.mock_vid.save()
                counter = counter + 1

            working_url = get_working_url()
            cls.title_test_1 = Video.objects.create(video_url=working_url, video_preview_url=None,
                                                title='test title 1', caption='', date=None, project=None)
            cls.title_test_1.save()
            cls.title_test_2 = Video.objects.create(video_url=working_url, video_preview_url=None,
                                                title='_break_title_', caption='', date=None, project=None)
            cls.title_test_2.save()
            cls.title_test_3 = Video.objects.create(video_url=working_url, video_preview_url=None,
                                                title='BROKEN TITLE', caption='', date=None, project=None)
            cls.title_test_3.save()

    def test_videos_exist(self):
        self.assertNotEqual(Video.objects.all().count(), 0, 'no videos')

    def test_video_urls(self):
        for vid in Video.objects.all():
            self.assertEqual(check_site_exist(vid.video_url), True, 'url for video "' + vid.title + '" does not exist')
            self.assertEqual(check_site_exist(vid.video_url), True, 'preview url for video "' + vid.title + '" does not work')

    def test_video_embed(self):
        for vid in Video.objects.all():
            self.assertEqual(check_site_exist(vid.get_embed()), True, 'embed video url for video "' + vid.title + '" does not work')

    def test_video_title_format(self):
        for vid in Video.objects.all():
            title = vid.get_title()

            title_split = title.split(' ')
            for word in title_split:
                if word[0].isalpha() and word[0].islower():
                    self.assertEqual(False, True, "first letter of word is not uppercase")
                for char in word[1:]:
                    if char.isalpha() and char.isupper():
                        self.assertEqual(False, True, "following letters of word after first letter are not lowercase")









