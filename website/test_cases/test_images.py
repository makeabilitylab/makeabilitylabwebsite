from django.test import TestCase
from website.models import Photo
from django.core.files.images import ImageFile
from django.core.files import File

import website.test_cases.helper_functions as hf



class ImageModelTest(TestCase):
    def setUp(self):
        '''
        a = hf.get_files_in_dir_in_testData('.png', 'testJPEGs')
        print(a)
        for img_path in a:
            print(img_path)
            image = File(open(img_path, 'rb'))
            new_photo = Photo.objects.create(picture=image, caption="hello", alt_text="hello")
            new_photo.save()
        '''
        image = File(open("./media/testData/testJPEGs/test1.jpeg", 'rb'))
        new_photo = Photo(picture=image, caption="test", alt_text="TEST")
        new_photo.save()

    def test_images_not_empty(self):
        self.assertNotEqual(Photo.objects.all().count(), 0, 'no photos!')

    def test_images_exist(self):
        img = Photo.objects.all()[:1].get()
        self.assertIsNotNone(img.picture, 'photo for ' + img.alt_text + ' is not there!')

    def test_image_url_exist(self):
        for img in Photo.objects.all():
            self.assertNotEqual(img.picture.url, None, 'Image not found')

