from website.models import Video
from django.test import TestCase
from website.test_cases.helper_functions import *
from django.core.files import File


class VideoTest (TestCase):
    def setUp(self):
        vid_test_file = File(open("./media/testData/testVideos/vid_urls.txt", 'rb'))
        url_test = vid_test_file.readline()
        mock_vid = Video.objects.create(video_url=url_test, video_preview_url=None,
                                            title='test video', caption='', date=None, project=None)
        mock_vid.save()

    def test_videos_exist(self):
        self.assertNotEqual(Video.objects.all().count(), 0, 'no videos')

    def test_video_urls(self):
        for vid in Video.objects.all():
            self.assertEqual(check_site_exist(vid.video_url), True, 'url for video ' + vid.title + ' does not exist')
            self.assertEqual(check_site_exist(vid.video_url), True, 'preview url for video ' + vid.title + ' does not work')

    def test_video_embed(self):
        for vid in Video.objects.all():
            self.assertEqual(check_site_exist(vid.get_embed()), True, 'embed video url for video ' + vid.title + ' does not work')

    def test_video_title_format(self):
        for vid in Video.objects.all():
            title = vid.get_title()
            has_all_caps = True
            title_split = title.split(' ')
            for word in title_split:
                if not word.isupper():
                    has_all_caps = False
                    break
            self.assertEqual(has_all_caps, True, 'video title ' + vid.title + ' has incorrect format')








