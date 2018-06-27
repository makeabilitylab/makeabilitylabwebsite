from django.test import TestCase
from website.models import Photo
from django.core.files.images import ImageFile

import website.test_cases.helper_functions as hf



class ImageModelTest(TestCase):
    def setUp(self):
        a = hf.get_files_in_dir_in_testData('.png', 'testImages')
        for img_path in a:
            fd = ImageFile.open(img_path)
            q = Photo.objects.create()
            q.picture.save('test'+str(a.index(img_path))+".png", fd.read(), True)

    def test_imagesexist(self):
        self.assertNotEqual(Photo.objects.all().count(), 0, 'no image!')
        for img in Photo.objects.all():
            self.assertNotEqual(img.picture(), None, 'photo for ' + img.alt_text() + ' is not there!')
    def test_image_url_exist(self):
        for img in Photo.objects.all():
            self.assertEqual(img.picture.url(), not None, "Image not found")

