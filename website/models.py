from django.db import models

from datetime import date
from website.utils.fileutils import UniquePathAndRename

class Person(models.Model):
    first_name = models.CharField(max_length=40)
    middle_name = models.CharField(max_length=50, blank=True, null=True)
    last_name = models.CharField(max_length=50)
    email = models.EmailField(blank=True, null=True)
    personal_website = models.URLField(blank=True, null=True)

    # Note: the ImageField requires the pillow library, which can be installed using pip
    # pip3 install Pillow
    # We use the get_unique_path function because otherwise if two people use the same
    # filename (something generic like picture.jpg), one will overwrite the other.
    image = models.ImageField(upload_to=UniquePathAndRename("person", True))
    # image_cropped = models.ImageField(editable=False)

    def get_full_name(self, includeMiddle=True):
        if self.middle_name and includeMiddle:
            return u"{0} {1} {2}".format(self.first_name, self.middle_name, self.last_name)
        else:
            return u"{0} {1}".format(self.first_name, self.last_name)

    def __str__(self):
        return self.get_full_name()

class Position(models.Model):
    person = models.ForeignKey(Person)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)

    # According to Django docs, best to have field choices within the primary
    # class that uses them. See https://docs.djangoproject.com/en/1.9/ref/models/fields/#choices
    MEMBER = "Member"
    COLLABORATOR = "Collaborator"

    ROLE_CHOICES = (
         (MEMBER, "Member"),
         (COLLABORATOR, "Collaborator"),
    )
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default=MEMBER)

    HIGH_SCHOOL = "High School Student"
    UGRAD = "Undergrad"
    MS_STUDENT = "MS Student"
    PHD_STUDENT = "PhD Student"
    POST_DOC = "Post-doc"
    ASSISTANT_PROF = "Assistant Professor"
    ASSOCIATE_PROF = "Associate Professor"
    FULL_PROF = "Professor"

    TITLE_CHOICES = (
         (HIGH_SCHOOL, HIGH_SCHOOL),
         (UGRAD, UGRAD),
         (MS_STUDENT, MS_STUDENT),
         (PHD_STUDENT, PHD_STUDENT),
         (POST_DOC, POST_DOC),
         (ASSISTANT_PROF, ASSISTANT_PROF),
         (ASSOCIATE_PROF, ASSOCIATE_PROF),
         (FULL_PROF, FULL_PROF),
    )
    title = models.CharField(max_length=50, choices=TITLE_CHOICES)

    department = models.CharField(max_length=50, default="Computer Science")
    school = models.CharField(max_length=60, default="University of Maryland")

    # Returns an abbreviated version of the department field
    def get_department_abbreviated(self):
        if self.department.lower() == "computer science":
            return 'CS'
        elif "information" in self.department.lower():
            return 'iSchool'
        elif "ischool" in self.department.lower():
            return 'iSchool'
        else:
            "".join(e[0] for e in self.department.split())

    def get_date_range_as_str(self):
        if self.start_date is not None and self.end_date is None:
            return "{}-".format(self.start_date.year)
        elif self.start_date is not None and self.end_date is not None and self.start_date.year == self.end_date.year:
            return "{}".format(self.start_date.year)
        else:
            return "{}-{}".format(self.start_date.year, self.end_date.year)

    # Returns true if collaborator
    def is_collaborator(self):
        return self.role == Position.COLLABORATOR

    # Returns true if member
    def is_member(self):
        return self.role == Position.MEMBER

    # Returns true if member is still active based on end date
    def is_active_member(self):
        return self.is_member() and \
               self.start_date is not None and self.start_date <= date.today() and \
               self.end_date is None or (self.end_date is not None and self.end_date >= date.today())

    def is_alumni_member(self):
        return self.is_member() and self.end_date != None and self.end_date < date.today()

    def __str__(self):
        return "Name={}, Role={}, Title={}".format(self.person.get_full_name(), self.role, self.title)

class Project(models.Model):
    name = models.CharField(max_length=255)
    short_name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class Keyword(models.Model):
    keyword = models.CharField(max_length=255)

    def __str__(self):
        return self.keyword

class Talk(models.Model):
    title = models.CharField(max_length=255)

    # A talk can be about more than one project
    projects = models.ManyToManyField(Project, blank=True, null=True)

    # TODO: remove the null = True from all of the following objects
    # including forum_name, forum_url, location, speakers, date, slideshare_url
    keywords = models.ManyToManyField(Keyword, blank=True, null=True)
    forum_name = models.CharField(max_length=255, null=True)
    forum_url = models.URLField(blank=True, null=True)
    location = models.CharField(max_length=255, null=True)

    # Most of the time talks are given by one person, but sometimes they are given by two people
    speakers = models.ManyToManyField(Person, null=True)

    date = models.DateField(null=True)
    slideshare_url = models.URLField(blank=True, null=True)

    # The PDF and raw files (e.g., keynote, pptx) are required
    # TODO: remove null=True from these two fields
    pdf_file = models.FileField(upload_to='talks/', null=True, default=None)
    raw_file = models.FileField(upload_to='talks/', blank=True, null=True, default=None)

    # The thumbnail should have null=True because it is added automatically later by a post_save signal
    # TODO: decide if we should have this be editable=True and if user doesn't add one him/herself, then
    # auto-generate thumbnail
    thumbnail = models.ImageField(upload_to='talks/images/', editable=False, null=True)

    # raw_file = models.FileField(upload_to='talks/')
    # print("In talk model!")

    def __str__(self):
        return self.title

class Publication(models.Model):
    title = models.CharField(max_length=255)
    authors = models.ManyToManyField(Person)

    # The PDF and raw files (e.g., keynote, pptx) are required
    # TODO: remove null=True from these two fields
    pdf_file = models.FileField(upload_to='talks/', null=True, default=None)

    book_title = models.CharField(max_length=255, null=True)
    book_title_short = models.CharField(max_length=255, null=True)

    # The thumbnail should have null=True because it is added automatically later by a post_save signal
    # TODO: decide if we should have this be editable=True and if user doesn't add one him/herself, then
    # auto-generate thumbnail
    thumbnail = models.ImageField(upload_to='talks/images/', editable=False, null=True)

    date = models.DateField(null=True)
    num_pages = models.IntegerField(null=True)

    # A publication can be about more than one project
    projects = models.ManyToManyField(Project, blank=True, null=True)

    # TODO, see if there is an IntegerRangeField or something like that for page_num_start and end
    page_num_start = models.IntegerField(blank=True, null=True)
    page_num_end = models.IntegerField(blank=True, null=True)
    official_url = models.URLField(blank=True, null=True)
    geo_location = models.CharField(max_length=255, blank=True, null=True)

    video_url = models.URLField(blank=True, null=True)
    video_preview_url = models.URLField(blank=True, null=True)
    talk = models.ForeignKey(Talk, blank=True, null=True)

    CONFERENCE = "Conference"
    ARTICLE = "Article"
    JOURNAL = "Journal"
    BOOK_CHAPTER = "Book Chapter"
    BOOK = "Book"
    MS_THESIS = "MS Thesis"
    PHD_DISSERTATION = "PhD Dissertation"
    WORKSHOP = "Workshop"
    POSTER = "Poster"
    DEMO = "Demo"
    WIP = "Work in Progress"
    LATE_BREAKING = "Late Breaking Result"
    OTHER = "Other"

    PUB_VENUE_TYPE_CHOICES = (
         (CONFERENCE, CONFERENCE),
         (ARTICLE, ARTICLE),
         (JOURNAL, JOURNAL),
         (BOOK_CHAPTER, BOOK_CHAPTER),
         (BOOK, BOOK),
         (MS_THESIS, MS_THESIS),
         (PHD_DISSERTATION, PHD_DISSERTATION),
         (WORKSHOP, WORKSHOP),
         (POSTER, POSTER),
         (DEMO, DEMO),
         (WIP, WIP),
         (LATE_BREAKING, LATE_BREAKING),
         (OTHER, OTHER),
    )

    #TODO: remove null=True from the following three
    pub_venue_type = models.CharField(max_length=50, choices=PUB_VENUE_TYPE_CHOICES, null=True)
    extended_abstract = models.NullBooleanField(null=True)
    peer_reviewed = models.NullBooleanField(null=True)

    total_papers_submitted = models.IntegerField(blank=True, null=True)
    total_papers_accepted = models.IntegerField(blank=True, null=True)

    BEST_PAPER_AWARD = "Best Paper Award"
    HONORABLE_MENTION = "Honorable Mention"
    BEST_PAPER_NOMINATION = "Best Paper Nominee"

    AWARD_CHOICES = (
        (BEST_PAPER_AWARD, BEST_PAPER_AWARD),
        (HONORABLE_MENTION, HONORABLE_MENTION),
        (BEST_PAPER_NOMINATION, BEST_PAPER_NOMINATION)
    )
    award = models.CharField(max_length=50, choices=AWARD_CHOICES, blank=True, null=True)

    def __str__(self):
        return self.title

class Poster(models.Model):
    publication = models.ForeignKey(Publication, blank=True, null=True)

    # If publication is set, then these fields will be drawn from Publication
    # and ignored here.
    title = models.CharField(max_length=255, blank=True, null=True)
    authors = models.ManyToManyField(Person, blank=True, null=True)

    # The PDF and raw files (e.g., illustrator, powerpoint)
    pdf_file = models.FileField(upload_to='posters/', null=True, default=None)
    raw_file = models.FileField(upload_to='posters/', null=True, default=None)

    # The thumbnail should have null=True because it is added automatically later by a post_save signal
    # TODO: decide if we should have this be editable=True and if user doesn't add one him/herself, then
    # auto-generate thumbnail
    thumbnail = models.ImageField(upload_to='posters/images/', editable=False, null=True)

    def __str__(self):
        if self.publication:
            return self.publication.title
        else:
            return self.title