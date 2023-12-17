import os
from website.models import Artifact

class Poster(Artifact):
    UPLOAD_DIR = 'posters/'
    THUMBNAIL_DIR = os.path.join(UPLOAD_DIR, 'images/')

    def get_upload_dir(self, filename):
        return os.path.join(self.UPLOAD_DIR, filename)

    def get_upload_thumbnail_dir(self, filename):
        return os.path.join(self.THUMBNAIL_DIR, filename)