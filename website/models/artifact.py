from django.db import models
import logging # for logging
import os # for file handling
import website.utils.fileutils as ml_fileutils # for custom file handling
from sortedm2m.fields import SortedManyToManyField

# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)

def get_upload_dir(instance, filename):
    return instance.get_upload_dir(filename)

def get_upload_thumbnail_dir(instance, filename):
    return instance.get_thumbnail_dir(filename)

class Artifact(models.Model):
    """
    If you want to add a new artifact type, you should create a new model that inherits from this class.
    You must then also create a new Admin class that derives from ArtifactAdmin(admin.ModelAdmin):
    """
    title = models.CharField(max_length=255, blank=True, null=True)
    authors = SortedManyToManyField('Person', blank=True)
    date = models.DateField(null=True)
    date.help_text = "When was this artifact presented or published?"
    forum_name = models.CharField(max_length=255, null=True)
    forum_name.help_text = "Where was this artifact presented? Please use a short name like UIST, ASSETS, CHI, etc."
    forum_url = models.URLField(blank=True, null=True)
    forum_url.help_text = "A hyperlink to the forum (<i>e.g.,</i> if CHI, put https://chi2024.acm.org/)"
    location = models.CharField(max_length=255, null=True)
    location.help_text = "The geographic location of where this artifact was presented"
    
    # The artifacts themselves
    pdf_file = models.FileField(upload_to=get_upload_dir, null=True, default=None, max_length=255)
    pdf_file.help_text = "The rendered PDF of the talk"
    raw_file = models.FileField(upload_to=get_upload_dir, blank=True, null=True, default=None, max_length=255)
    raw_file.help_text = "The raw file (e.g., pptx, keynote) for the artifact. While not required, this is "\
        "<b>highly</b> recommended as it creates a better archive of the work"
    thumbnail = models.ImageField(upload_to=get_upload_thumbnail_dir, editable=False, null=True, max_length=255)
    
    # Project and keyword associations
    projects = models.ManyToManyField('Project', blank=True)
    projects.help_text = "Most artifacts are associated with only one project but "\
                         "keynotes, guest lectures, etc. might be associated with multiple projects"
    
    project_umbrellas = SortedManyToManyField('ProjectUmbrella', blank=True)
    keywords = models.ManyToManyField('Keyword', blank=True)
    keywords.help_text = "The keywords associated with this artifact"

    class Meta:
        abstract = True

    def get_upload_dir(self, filename):
        raise NotImplementedError("This method should be overridden in a child class")
    
    def get_upload_thumbnail_dir(self, filename):
        raise NotImplementedError("This method should be overridden in a child class")
    
    def get_first_author_last_name(self):
        """
        Returns the last name of the first author of the artifact.
        
        If the artifact has an ID and at least one author, it returns the last name of the first author.
        Otherwise, it returns "Unknown".
        """
        if self.id and self.authors.exists(): 
            return self.authors.first().last_name
        else:
            return "Unknown"
    
    get_first_author_last_name.short_description = 'First Author (Last Name)' # used in the admin display for column header

    def __str__(self):
        if self.id and self.authors.exists():          
            return "{}, '{}', {} {}".format(self.get_first_author_last_name(), self.title, self.forum_name, self.date)
        else:
            return f"Unknown, '{self.title}', {self.forum_name}, {self.date}"
    
    def delete(self, *args, **kwargs):
        """
        Overrides the default delete method to delete the associated files before deleting the model instance.

        This method attempts to delete the 'pdf_file', 'raw_file', and 'thumbnail' files associated with the instance.
        If a file does not exist in the storage, its deletion is skipped. If a file exists, it is deleted and a log 
        message is recorded. After attempting to delete the files, the method calls the parent class's delete method 
        to delete the model instance.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            None
        """
        _logger.debug(f"Started delete with self={self.id}, args={args}, kwargs={kwargs}")
   
        _logger.debug(f"Attempting to delete pdf_file={self.pdf_file} off filesystem")
        if self.pdf_file:
            if self.pdf_file.storage.exists(self.pdf_file.name):
                # In Django, when you call the delete() method on a FileField or an ImageField, it takes an optional 
                # save argument. If save is True, Django will save the model after deleting the file. However, in the 
                # context of deleting a model instance (which is what’s happening here), we don’t want to save the model 
                # after deleting the file, because the model itself is being deleted. And super().delete(*args, **kwargs)
                # will handle this for us
                pdf_file_full_path = self.pdf_file.path
                self.pdf_file.delete(False)
                _logger.debug(f"Deleted {pdf_file_full_path} off filesystem")
            else:
                _logger.debug(f"Could not delete pdf_file={self.pdf_file} as it does not exist on filesystem")
        
        _logger.debug(f"Attempting to delete raw_file={self.raw_file} off filesystem")
        if self.raw_file:
            raw_file_full_path = self.raw_file.path
            if self.raw_file.storage.exists(self.raw_file.name):
                self.raw_file.delete(False)
                _logger.debug(f"Deleted {raw_file_full_path} off filesystem")
            else:
                _logger.debug(f"Could not delete raw_file={self.raw_file} as it does not exist on filesystem")

        _logger.debug(f"Attempting to delete thumbnail={self.thumbnail} off filesystem")
        if self.thumbnail:
            thumbnail_full_path = self.thumbnail.path
            if self.thumbnail.storage.exists(self.thumbnail.name):
                self.thumbnail.delete(False)
                _logger.debug(f"Deleted {thumbnail_full_path} off filesystem")
            else:
                _logger.debug(f"Could not delete thumbnail={self.thumbnail} as it does not exist on filesystem")

        _logger.debug(f"Completed delete for artifact id={self.pk} and args={args} and kwargs={kwargs}")
        super().delete(*args, **kwargs)
        
    def save(self, *args, **kwargs):
        """
        Saves an artifact instance, performing additional tasks like:

        - Cleaning up old files when updating `pdf_file` or `raw_file`
        - Renaming files if author names change after the first save
        - Generating a thumbnail if one doesn't exist

        Args:
            *args (optional): Additional positional arguments passed to super().save()
            **kwargs (optional): Additional keyword arguments passed to super().save()

        Returns:
            None

        Raises:
            StorageError: If an error occurs while interacting with the storage system
            ValueError: If invalid arguments are provided
        """
        
        _logger.debug(f"Started save for self={self} with artifact id={self.pk} and args={args} and kwargs={kwargs}")
        _logger.debug(f"The pdf_file is currently {self.pdf_file}")
        if self.pdf_file:
            # In Django, when you call save() on a model instance, the FileField doesn’t immediately have its full path set. 
            # This is because the file hasn’t been saved to the storage system yet.
            _logger.debug(f"The local pdf_file path is: {self.pdf_file.name}")

            # Thus, self.pdf_file.path won't won't be correct until super.save() is called 
            # (the first time this Artifact instance is created)
            _logger.debug(f"The full pdf_file path is: {self.pdf_file.path}") 

        _logger.debug(f"The raw_file is currently {self.raw_file}")

        first_time_saved = self.id is None
        _logger.debug(f"For artifact.id={self.id}, first_time_saved={first_time_saved}")
        
        # Note that "update_fields" is custom filled by our save_model in ArtifactAdmin
        # It will never contain the m2m fields (e.g., authors, keywords, etc.) due to
        # how Django handles m2m fields. Instead, you can hook up an m2m_changed signal
        # as we have for authors_changed in signals.py
        if not first_time_saved and kwargs.get('update_fields') is not None:
            update_fields = kwargs['update_fields']
            _logger.debug(f"update_fields={update_fields}, checking to see if we have to do some cleanup on files")

            # type(self) will return the class of the current instance. For example, if self is an instance of Poster, type(self) 
            # will be Poster. This allows you to query the correct model without having to implement the save method in 
            # each child class. According to ChatGPT, using type(self) in this way is generally considered acceptable in Python and Django. 
            # It’s a common way to access the concrete class from an instance in a base class method. 
            orig_artifact = type(self).objects.get(pk=self.pk)

            # Check if pdf_file is one of the updated fields and, if so, delete the old file
            if 'pdf_file' in update_fields:
                _logger.debug(f"pdf_file is in update_fields, attempting to delete old pdf_file and corresponding thumbnail")
                if orig_artifact.pdf_file:
                    _logger.debug(f"orig_artifact.pdf_file={orig_artifact.pdf_file} exists, attempting to delete")
                    if orig_artifact.pdf_file.storage.exists(orig_artifact.pdf_file.name):
                        # The True argument in pdf_file.delete(True) is for the save parameter. This parameter determines 
                        # whether to save the model after the file has been deleted. If save is True, the model will be 
                        # saved after the file deletion. Since we're already in a save(), we don't want to call save
                        deleted_path = orig_artifact.pdf_file.path
                        orig_artifact.pdf_file.delete(False)
                        _logger.debug(f"Deleted pdf_file={deleted_path} off filesystem")
                    else:
                        _logger.debug(f"Could not delete pdf_file={orig_artifact.pdf_file} as it does not exist on filesystem")

                if orig_artifact.thumbnail:
                    _logger.debug(f"orig_artifact.thumbnail={orig_artifact.thumbnail} exists, attempting to delete")
                    if orig_artifact.thumbnail.storage.exists(orig_artifact.thumbnail.name):
                        deleted_path = orig_artifact.thumbnail.path
                        orig_artifact.thumbnail.delete(False)
                        _logger.debug(f"Deleted thumbnail={deleted_path} off filesystem")
                    else:
                        _logger.debug(f"Could not delete thumbnail={orig_artifact.thumbnail} as it does not exist on filesystem")
            
            if 'raw_file' in update_fields:
                _logger.debug(f"raw_file is in update_fields, attempting to delete old raw_file")
                if orig_artifact.raw_file:
                    _logger.debug(f"Attempting to delete raw_file={orig_artifact.raw_file} off filesystem")
                    if orig_artifact.raw_file:
                        if orig_artifact.raw_file.storage.exists(orig_artifact.raw_file.name):
                            deleted_path = orig_artifact.raw_file.path
                            orig_artifact.raw_file.delete(False)
                            _logger.debug(f"Deleted raw_file={deleted_path} off filesystem")
                        else:
                            _logger.debug(f"Could not delete raw_file={orig_artifact.raw_file} as it does not exist on filesystem")

        if not first_time_saved:
            # self.authors is a many-to-many field in Django. This field is not set
            # until after this model is first saved to the database (which is a bit funky)
            # This means that self.authors can't get set until after this save method completes the 
            # first time (that is, after super().save is called)
            # Hence, we have a flag "first_time_saved" that checks for this condition and
            # then attempts to continue only when author values have been set
            _logger.debug(f"The authors for the artifact are: {self.authors.all()}")
            if self.authors.exists():
                _logger.debug(f"An author exists, checking to see if filenames need to be renamed")
                if Artifact.do_filenames_need_updating(self):
                    _logger.debug(f"At least one filename needs to be renamed...")
                    new_filename_no_ext = Artifact.generate_filename(self)

                    if self.pdf_file:
                        old_pdf_filename = os.path.basename(self.pdf_file.name)
                        old_pdf_filename_no_ext, ext = os.path.splitext(old_pdf_filename)
                        if new_filename_no_ext != old_pdf_filename_no_ext:
                            _logger.debug(f"The new_filename_no_ext={new_filename_no_ext} and old_pdf_filename_no_ext={old_pdf_filename_no_ext} don't match. Renaming...")
                            # We call only rename artifact on filesystem and not the _db version as all of these
                            # changes will be saved back to the db with the super.save() call at end of this method
                            ml_fileutils.rename_artifact_on_filesystem(self.pdf_file, new_filename_no_ext)
                        else:
                            _logger.debug(f"The pdf filename matches {old_pdf_filename} so not renaming")
                    
                    if self.raw_file:
                        old_raw_filename = os.path.basename(self.raw_file.name)
                        old_raw_filename_no_ext, ext = os.path.splitext(old_raw_filename)
                        if new_filename_no_ext != old_raw_filename_no_ext:
                            _logger.debug(f"The new_filename_no_ext={new_filename_no_ext} and old_raw_filename_no_ext={old_raw_filename_no_ext} don't match. Renaming...")
                            ml_fileutils.rename_artifact_on_filesystem(self.raw_file, new_filename_no_ext)
                        else:
                            _logger.debug(f"The raw filename matches {old_raw_filename} so not renaming")

                    if self.thumbnail:
                        old_thumbnail_filename = os.path.basename(self.thumbnail.name)
                        old_thumbnail_filename_no_ext, ext = os.path.splitext(old_thumbnail_filename)
                        if new_filename_no_ext != old_thumbnail_filename_no_ext:
                            _logger.debug(f"The new_filename_no_ext={new_filename_no_ext} and old_thumbnail_filename_no_ext={old_thumbnail_filename_no_ext} don't match. Renaming...")
                            ml_fileutils.rename_artifact_on_filesystem(self.thumbnail, new_filename_no_ext)
                        else:
                            _logger.debug(f"The thumbnail filename matches {old_thumbnail_filename} so not renaming")
            else:
                _logger.debug("No authors exist yet, so will wait for m2m authors_changed to rename files")

            # Generate a thumbnail if one does not already exist
            pdf_filename = os.path.basename(self.pdf_file.name)
            pdf_filename_no_ext, ext = os.path.splitext(pdf_filename)
            thumbnail_filename = os.path.basename(pdf_filename_no_ext) + ".jpg" 
            thumbnail_filename_with_local_path = self.get_upload_thumbnail_dir(thumbnail_filename)
            thumbnail_exists_in_storage = self.thumbnail.storage.exists(thumbnail_filename_with_local_path)
            if not self.thumbnail or not thumbnail_exists_in_storage:
                _logger.debug(f"The thumbnail for artifact.id={self.id} does not exist at {thumbnail_filename_with_local_path}, generating...")
                
                # generate a thumbnail
                if self.pdf_file.storage.exists(self.pdf_file.name):
                    thumbnail_local_path = os.path.dirname(thumbnail_filename_with_local_path)
                    ml_fileutils.generate_thumbnail_for_pdf(self.pdf_file, self.thumbnail, thumbnail_local_path)
                else:
                    _logger.debug(f"Could not generate a thumbnail because the pdf {self.pdf_file.path} was not found in storage")
            elif thumbnail_exists_in_storage:
                _logger.debug(f"The thumbnail for artifact.id={self.id} already exists at {thumbnail_filename_with_local_path}, so not generating")

        _logger.debug(f"Calling super().save(*args, **kwargs)")

        super().save(*args, **kwargs)

        _logger.debug(f"Completed save for self={self} with artifact id={self.pk} and args={args} and kwargs={kwargs}")

    @staticmethod
    def do_filenames_need_updating(artifact):
        """
        This method checks if the filenames of the artifact's files (pdf_file, raw_file, thumbnail) need to be updated.
        It generates a new filename and compares it with the old filenames (without extensions).
        If the new filename doesn't match with any of the old filenames, it returns True indicating that filenames need to be updated.
        Otherwise, it returns False.

        Args:
            artifact (Artifact): The artifact object whose filenames are to be checked.

        Returns:
            bool: True if filenames need to be updated, False otherwise.
        """
        new_filename_no_ext = Artifact.generate_filename(artifact)

        if artifact.pdf_file:
            # We get the old filename (without the local path)
            old_pdf_filename = os.path.basename(artifact.pdf_file.name)
            old_pdf_filename_no_ext, ext = os.path.splitext(old_pdf_filename)
            if new_filename_no_ext != old_pdf_filename_no_ext:
                _logger.debug(f"The new_filename_no_ext={new_filename_no_ext} and old_pdf_filename_no_ext={old_pdf_filename_no_ext} don't match")
                return True
        
        if artifact.raw_file:
            old_raw_filename = os.path.basename(artifact.pdf_file.name)
            old_raw_filename_no_ext, ext = os.path.splitext(old_raw_filename)
            if new_filename_no_ext != old_raw_filename_no_ext:
                _logger.debug(f"The new_filename_no_ext={new_filename_no_ext} and old_raw_filename_no_ext={old_raw_filename_no_ext} don't match")
                return True
        
        if artifact.thumbnail:
            old_thumbnail_filename = os.path.basename(artifact.pdf_file.name)
            old_thumbnail_filename_no_ext, ext = os.path.splitext(old_thumbnail_filename)
            if new_filename_no_ext != old_thumbnail_filename_no_ext:
                _logger.debug(f"The new_filename_no_ext={new_filename_no_ext} and old_thumbnail_filename_no_ext={old_thumbnail_filename_no_ext} don't match")
                return True

        return False

    @staticmethod
    def generate_filename(artifact, file_extension=None, max_pub_title_length = -1):
        """
        Generates a filename for the given artifact.

        This method generates a filename based on the artifact's first author's last name, title, forum name, and date.
        If a file extension is provided, it is appended to the filename. Otherwise, a filename without extension is returned.

        Parameters:
        artifact (Artifact): The artifact for which the filename is to be generated.
        file_extension (str, optional): The file extension to be appended to the filename. Defaults to None.

        Returns:
        str: The generated filename.

        Example:
        >>> artifact = Artifact(first_author_last_name="Froehlich", title="Research Artifact Title", forum_name="CHI", date="2023-12-16")
        >>> generate_filename(artifact, file_extension=".pdf")
        'Froehlich_ResearchArtifactTitle_CHI2023.pdf'
        """
        
        # An empty string or a string with only whitespace characters is considered False in a boolean context.
        if not file_extension or not file_extension.strip():
            return ml_fileutils.get_filename_without_ext_for_artifact(
                    artifact.get_first_author_last_name(), artifact.title, 
                    artifact.forum_name, artifact.date)
        else:
            return ml_fileutils.get_filename_for_artifact(
                    artifact.get_first_author_last_name(), artifact.title, 
                    artifact.forum_name, artifact.date, file_extension)