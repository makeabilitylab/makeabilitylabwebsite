from django.test import TestCase
from website.models import Photo
import os
from os.path import join


class ImageModelTest(TestCase):

    def get_image_path(self):
        for root, dirs, files in os.walk('website/test_cases/testData/test_img'):
            # debug information, just to get an idea how walk works.
            # currently we are traversing over all files with any extension
            print("Current directory", root)
            print("Sub directories", dirs)
            print("Files", files)
            image_urls = []
            for file in files:
                if file.startswith(self.title):
                    # now we have found the desired file.
                    # value of file: "myimagetitle.jpg" <-- no path info
                    # value of root: "/home/yourhome/gallery/static/images/myalbum"
                    # we want to use this information to create a url based on our static path, so we need only the path sections past "static"
                    # we can achieve this like so (just one way)
                    mypath = os.sep.join(os.path.join(root, file).split(os.sep)[4:])

                    # yields: /images/myalbum/myimagetitle.jpg

                    image_urls.append(mypath)
            return image_urls

    def setUp(self):
        for url in get_image_path():

    def test_imagesexist(self):
        self.assertNotEqual(Photo.objects.all().count(), 0, 'no image!')
        for img in Photo.objects.all():
            self.assertNotEqual(img.picture(), None, 'photo for ' + img.alt_text() + ' is not there!')
    def test_image_url_exist(self):
        for img in Photo.objects.all():
            self.assertEqual(img.picture.url(), not None, "Image not found")

