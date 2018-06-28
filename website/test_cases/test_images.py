from django.test import TestCase
from website.models import Photo
from django.core.files import File


from website.test_cases.helper_functions import *


class ImageModelTest(TestCase):
    def setUp(self):
        operationGetThosePATHS = get_files_in_dir_in_media('.jpeg', 'testData/testJPGs')s
        for path in operationGetThosePATHS:
            image = File(open(path, 'rb'))
            new_photo = Photo.objects.create(picture=image, caption="test", alt_text="TEST")
            new_photo.save()
            image.close()

    def test_images_not_empty(self):
        self.assertNotEqual(Photo.objects.all().count(), 0, 'no photos!')

    def test_images_exist(self):
        for img in Photo.objects.all():
            self.assertIsNotNone(img.picture, 'photo for ' + img.alt_text + ' is not there!')

    def test_image_url_exist(self):
        for img in Photo.objects.all():
            self.assertNotEqual(img.picture.url, None, 'Image not found')

