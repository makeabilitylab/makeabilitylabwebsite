from django.test import TestCase
from website.models import Photo
from django.core.files.images import ImageFile
from django.core.files import File

import website.test_cases.helper_functions as hf


class ImageModelTest(TestCase):
    def setUp(self):
        '''
        with open('./media/testData/testJPGs/jpeg_urls.txt', 'w') as fwrite_urls:
            a = hf.get_files_in_dir_in_testData('.jpg', 'testData/testJPGs')
            for item in a:
                fwrite_urls.write("%s\n" % item)
        '''
        with open('./media/testData/testJPGs/jpeg_urls.txt', 'r') as fin:
            raw_lines = fin.readlines()
        lines = list(map(lambda s: s.strip(), raw_lines))
        print(lines)
        for i in range(len(lines)):
            file_name = "test"+str(int(i+1))+".jpg"
            print(file_name)
            image = File(open("./media/testData/testJPGs/"+file_name, 'rb'))
            new_photo = Photo(picture=image, caption="test", alt_text="TEST")
            new_photo.save()
        '''
        image = File(open("./media/testData/testJPGs/test1.jpg", 'rb'))
        new_photo = Photo(picture=image, caption="test", alt_text="TEST")
        new_photo.save()
        '''
    def test_images_not_empty(self):
        self.assertNotEqual(Photo.objects.all().count(), 0, 'no photos!')

    def test_images_exist(self):
        img = Photo.objects.all()[:1].get()
        self.assertIsNotNone(img.picture, 'photo for ' + img.alt_text + ' is not there!')

    def test_image_url_exist(self):
        for img in Photo.objects.all():
            self.assertNotEqual(img.picture.url, None, 'Image not found')

