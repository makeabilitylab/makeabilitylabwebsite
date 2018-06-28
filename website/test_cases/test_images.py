from django.test import TestCase
from website.models import Photo
from django.core.files.images import ImageFile
from django.core.files import File
from PIL import Image

import website.test_cases.helper_functions as hf


class ImageModelTest(TestCase):
    def setUp(self):
        operationGetThoseURLS = hf.get_files_in_dir_in_testData('.jpeg', 'testData/testJPGs')
        for urls in operationGetThoseURLS:
            image = File(open(urls, 'rb'))
            print(urls)
            new_photo = Photo(picture=image, caption="test", alt_text="TEST")
            print(new_photo)
            new_photo.save()
            image.close()
        '''
        for i in range(5):
            image=File(open(a[i], 'rb'))
            new_photo = Photo(picture=image, caption="test", alt_text="TEST")
            new_photo.save()
            image.close()

        
        image = File(open(a[0], 'rb'))
        new_photo = Photo(picture=image, caption="test", alt_text="TEST")
        new_photo.save()
        image.close()
        image = File(open("./media/testData/testJPGs/test2.jpeg", 'rb'))
        new_photo = Photo(picture=image, caption="test", alt_text="TEST")
        new_photo.save()
        image.close()
        '''
    def test_images_not_empty(self):
        self.assertNotEqual(Photo.objects.all().count(), 0, 'no photos!')

    def test_images_exist(self):
        img = Photo.objects.all()[:1].get()
        self.assertIsNotNone(img.picture, 'photo for ' + img.alt_text + ' is not there!')

    def test_image_url_exist(self):
        for img in Photo.objects.all():
            self.assertNotEqual(img.picture.url, None, 'Image not found')

