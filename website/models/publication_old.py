from django.db import models
from django.conf import settings
from django.dispatch import receiver
from django.db.models.signals import pre_delete, post_save, m2m_changed, post_delete
from django.utils.text import get_valid_filename

from sortedm2m.fields import SortedManyToManyField

from datetime import date, datetime, timedelta
import os
import os.path
import logging
import re # for regular expressions

from .person import Person
from .project_umbrella import ProjectUmbrella
from .keyword import Keyword
from .video import Video
from .talk import Talk
from .poster import Poster

# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)

class PubAwardType(models.TextChoices):
    BEST_ARTIFACT_AWARD = "Best Artifact Award"
    BEST_ARTIFACT_RUNNERUP_AWARD = "Best Artifact Runner-up Award"
    BEST_PAPER_AWARD = "Best Paper Award"
    HONORABLE_MENTION = "Honorable Mention"
    BEST_PAPER_NOMINATION = "Best Paper Nominee"
    TEN_YEAR_IMPACT_AWARD = "10-Year Impact Award"

class PubVenueType(models.TextChoices):
    CONFERENCE = "Conference"
    ARTICLE = "Article"
    JOURNAL = "Journal"
    BOOK_CHAPTER = "Book Chapter"
    BOOK = "Book"
    DOCTORAL_CONSORTIUM = "Doctoral Consortium"
    MS_THESIS = "MS Thesis"
    PHD_DISSERTATION = "PhD Dissertation"
    WORKSHOP = "Workshop"
    POSTER = "Poster"
    DEMO = "Demo"
    WIP = "Work in Progress"
    LATE_BREAKING = "Late Breaking Result"
    PANEL = "Panel"
    OTHER = "Other"

class Publication(models.Model):
    UPLOAD_DIR = 'publications/' # relative path
    THUMBNAIL_DIR = os.path.join(UPLOAD_DIR, 'images/') # relative path

    title = models.CharField(max_length=255)
    authors = SortedManyToManyField(Person)
    # authorsOrdered = models.ManyToManyField(Person, through='PublicationAuthorThroughModel')

    # The PDF is required
    pdf_file = models.FileField(upload_to=UPLOAD_DIR, null=False, default=None, max_length=255)

    book_title = models.CharField(max_length=255, null=True)
    book_title.help_text = "This is the long-form proceedings title. For example, for UIST, this would be 'Proceedings of the 27th Annual ACM Symposium on User " \
                           "Interface Software and Technology.' For CHI, 'Proceedings of the 2017 CHI Conference on " \
                           "Human Factors in Computing Systems' "
    forum_name = models.CharField(max_length=255, null=True)
    forum_name.help_text = "This is a shorter version of book title. For UIST, 'Proceedings of UIST 2014' " \
                           "For CHI, 'Proceedings of CHI 2017'"
    
    # TODO: remove null=True from the following three
    forum_url = models.URLField(blank=True, null=True)
    forum_url.help_text = "The url to the publication venue (e.g., https://chi2021.acm.org/ or https://cscw.acm.org/2022/)"

    # The thumbnail should have null=True because it is added automatically later by a post_save signal
    # TODO: decide if we should have this be editable=True and if user doesn't add one him/herself, then
    # auto-generate thumbnail
    thumbnail = models.ImageField(upload_to=THUMBNAIL_DIR, editable=False, null=True, max_length=255)

    date = models.DateField(null=True)
    date.help_text = "This is the publication date (e.g., first day of the conference in which the paper appears or the journal publication date)"
    num_pages = models.IntegerField(null=True)
    num_pages.help_text = "The total number of pages in this publication (including references)"

    # A publication can be about more than one project
    projects = SortedManyToManyField('Project', blank=True)
    project_umbrellas = SortedManyToManyField('ProjectUmbrella', blank=True)
    keywords = SortedManyToManyField('Keyword', blank=True)

    # TODO, see if there is an IntegerRangeField or something like that for page_num_start and end
    page_num_start = models.IntegerField(blank=True, null=True)
    page_num_end = models.IntegerField(blank=True, null=True)
    official_url = models.URLField(blank=True, null=True)
    official_url.help_text = "The official url link to the paper, often a DOI url like https://doi.org/10.1145/3441852.3476542"

    geo_location = models.CharField(max_length=255, blank=True, null=True)
    geo_location.help_text = "The physical location of the conference, if any. For example, CHI 2017 was in 'Denver, Colorado'"

    # Publications can have corresponding videos, talks, posters, etc.
    video = models.OneToOneField(Video, on_delete=models.DO_NOTHING, null=True, blank=True)
    talk = models.ForeignKey(Talk, blank=True, null=True, on_delete=models.DO_NOTHING)
    poster = models.ForeignKey(Poster, blank=True, null=True, on_delete=models.DO_NOTHING)
    code_repo_url = models.URLField(blank=True, null=True)
    code_repo_url.help_text = "URL to github or gitlab"

    series = models.CharField(max_length=255, blank=True, null=True)
    isbn = models.CharField(max_length=255, blank=True, null=True)
    doi = models.CharField(max_length=255, blank=True, null=True)
    publisher = models.CharField(max_length=255, blank=True, null=True)
    publisher_address = models.CharField(max_length=255, blank=True, null=True)
    acmid = models.CharField(max_length=255, blank=True, null=True)

    
    pub_venue_type = models.CharField(max_length=50, choices=PubVenueType.choices, null=True)
    extended_abstract = models.BooleanField(null=True)
    extended_abstract.help_text = "If the paper is not a *full* paper, it's likely an extended abstract (like a poster, demo, etc.)"
    peer_reviewed = models.BooleanField(null=True)

    total_papers_accepted = models.IntegerField(blank=True, null=True)
    total_papers_accepted.help_text = "The total number of papers accepted to the venue (if known)"
    total_papers_submitted = models.IntegerField(blank=True, null=True)
    total_papers_submitted.help_text = "The total number of papers submitted to the venue (if known)"

    award = models.CharField(max_length=50, choices=PubAwardType.choices, blank=True, null=True)

    def get_person(self):
        """Returns the first author"""
        return self.authors.all()[0]

    def is_extended_abstract(self):
        """Returns True if this publication is an extended abstract"""
        return (self.extended_abstract or
                self.pub_venue_type == self.POSTER or
                self.pub_venue_type == self.DEMO or
                self.pub_venue_type == self.WIP or
                self.pub_venue_type == self.DOCTORAL_CONSORTIUM)

    def get_acceptance_rate(self):
        """Returns the acceptance rate as a percentage"""
        if self.total_papers_accepted and self.total_papers_submitted:
            return 100 * (self.total_papers_accepted / self.total_papers_submitted)
        else:
            return -1

    def is_best_paper(self):
        """Returns true if earned best paper, best artifact, or test of time award"""
        return self.award == self.BEST_PAPER_AWARD or \
            self.award == self.BEST_ARTIFACT_AWARD or \
            self.award == self.TEN_YEAR_IMPACT_AWARD

    def is_honorable_mention(self):
        """Returns true if earned honorable mention or best paper nomination"""
        return self.award == self.HONORABLE_MENTION or \
            self.award == self.BEST_ARTIFACT_RUNNERUP_AWARD or \
            self.award == self.BEST_PAPER_NOMINATION

    def to_appear(self):
        """Returns true if the publication date happens in the future (e.g., tomorrow or later)"""
        return self.date and self.date > date.today()

    def get_citation_as_html(self):
        """Returns a human readable citation as html"""
        citation = ""
        author_idx = 0
        num_authors = self.authors.count()
        for author in self.authors.all():
            citation += author.get_citation_name(full_name=False)

            if (author_idx + 1) < num_authors:
                citation += ", "
            else:
                citation += " "

            author_idx += 1

        citation += "({}). ".format(self.date.year)
        citation += self.title + ". "
        citation += "<i>{}</i>. ".format(self.forum_name)

        if self.official_url:
            citation += "<a href={}>{}</a>".format(self.official_url, self.official_url)

        return citation

    def get_bibtex_id(self):
        """Generates and returns the bibtex id for this paper"""
        bibtex_id = self.get_person().last_name

        forum = self.forum_name.lower()
        if "proceedings of" in forum:
            forum = forum.replace('proceedings of', '')

        forum = forum.upper().replace(" ", "")
        if not forum[-1].isdigit():
            forum = forum + str(self.date.year)

        title_words = self.title.split()
        if len(title_words) > 0:
            bibtex_id += title_words[0]

        bibtex_id += forum

        bibtex_id = re.sub(r'[^a-zA-Z0-9]', '', bibtex_id)

        # code to make acronym from: https://stackoverflow.com/a/4355337
        title_acronym = ''.join(w[0] for w in self.title.split() if w[0].isupper())
        
        # if self.doi:
        #     doi = self.doi.rsplit('/', 1)[-1]
        #     bibtex_id += doi

        bibtex_id += ","

        return bibtex_id


    def get_citation_as_bibtex(self, newline="<br/>", use_hyperlinks=True):
        """Returns bibtex citation as a string"""
        bibtex = ""

        if self.pub_venue_type is self.JOURNAL or\
            self.pub_venue_type is self.ARTICLE:
            bibtex += "@article{"
        else:
            bibtex += "@inproceedings{"


        bibtex += self.get_bibtex_id() + newline

        # start author block
        bibtex += " author={"

        author_idx = 0
        num_authors = self.authors.count()
        for author in self.authors.all():
            citation_name = author.get_citation_name(full_name=True)
            bibtex += citation_name

            if (author_idx + 1) < num_authors:
                bibtex += " and "

            author_idx += 1
        bibtex += "}," + newline
        # end author block

        bibtex += " title={{{}}},{}".format(self.title, newline)
        bibtex += " booktitle={{{}}},{}".format(self.book_title, newline)
        bibtex += " booktitleshort={{{}}},{}".format(self.forum_name, newline)

        if self.series:
            bibtex += " series = {" + self.series + "},"

        bibtex += " year={{{}}},{}".format(self.date.year, newline)

        if self.isbn:
            bibtex += " isbn={{{}}},{}".format(self.isbn, newline)

        if self.geo_location:
            bibtex += " location={{{}}},{}".format(self.geo_location, newline)

        if self.page_num_start and self.page_num_end:
            bibtex += " pages={{{}--{}}},{}".format(self.page_num_start, self.page_num_end, newline)

        if self.num_pages:
            bibtex += " numpages={{{}}},{}".format(self.num_pages, newline)

        if self.doi:
            if use_hyperlinks:
                bibtex += " doi={{<a href='{}'>{}</a>}},{}".format(self.doi, self.doi, newline)
            else:
                bibtex += " doi={{{}}},{}".format(self.doi, newline)
        elif self.official_url and "doi.org" in self.official_url:
            parts = self.official_url.split("doi.org/")
            if len(parts) > 1:
                bibtex += " doi={{{}}},{}".format(parts[1], newline)


        if self.official_url:
            if use_hyperlinks:
                bibtex += " url={{<a href='{}'>{}</a>}},{}".format(self.official_url, self.official_url, newline)
            else:
                bibtex += " url={{{}}},{}".format(self.official_url, newline)

        if self.acmid:
            bibtex += " acmid={{{}}},{}".format(self.acmid, newline)

        if self.publisher:
            bibtex += " publisher={{{}}},{}".format(self.publisher, newline)

        bibtex += "}"
        return bibtex

    def __str__(self):
        return self.title

    @staticmethod
    def generate_filename(instance, filename_extension = ".pdf", max_pub_title_length = -1):
        """Generates a filename for this publication instance"""
        person = instance.get_person()
        last_name = person.last_name
        year = instance.date.year

        # Remove spaces and non alphanumeric characters
        pub_title = ''.join(x for x in instance.title.title() if not x.isspace())
        pub_title = ''.join(e for e in pub_title if e.isalnum())

        # Get the publication venue but remove proceedings from it (if it exists)
        forum = instance.forum_name.lower()
        if "proceedings of" in forum.lower():
            forum = forum.replace('proceedings of', '')

        forum = forum.strip().upper()
        forum = ''.join(x for x in forum if not x.isspace())

        if not forum[-1].isdigit():
            forum = forum + str(year)

        # Only get the first N characters of the string if max_pub_title_length set
        if max_pub_title_length > 0 and max_pub_title_length < len(pub_title):
            pub_title = pub_title[0:max_pub_title_length]

        # Convert metadata into a filename
        new_filename = last_name + '_' + pub_title + '_' + forum + filename_extension

        # Use Django helper function to ensure a clean filename
        new_filename = get_valid_filename(new_filename)

        return new_filename

def update_file_name_publication(sender, instance, action, reverse, **kwargs):
    # Reverse: Indicates which side of the relation is updated (i.e., if it is the forward or reverse relation that is being modified)
    # Action: A string indicating the type of update that is done on the relation.
    # post_add: Sent after one or more objects are added to the relation
    if action == 'post_add' and not reverse:
        
        new_filename = Publication.generate_filename(instance)

        # Change the path of the pdf file to point to the new file name
        instance.pdf_file.name = os.path.join(Publication.UPLOAD_DIR, new_filename)
        new_path = os.path.join(settings.MEDIA_ROOT, instance.pdf_file.name)
        
        initial_path = instance.pdf_file.path
        # Actually rename the existing file (aka initial_path) but only if it exists (it should!)
        if os.path.exists(initial_path):
            if initial_path != new_path:
                _logger.debug(f"Renaming filename for pub {instance} from {initial_path} to {new_path}")
                os.rename(initial_path, new_path)
                instance.save()
            else:
                _logger.debug(f"The pub {instance} has the correct filename with path, which is: {initial_path} so will not be renamed")
        else:
            _logger.error(f'The file {initial_path} does not exist and cannot be renamed to {new_path}')      

m2m_changed.connect(update_file_name_publication , sender=Publication.authors.through)

@receiver(pre_delete, sender=Publication)
def publication_delete(sender, instance, **kwards):
    """Deletes the pdf file and thumbnail when a publication is deleted"""
    if instance.thumbnail:
        instance.thumbnail.delete(True)
    if instance.pdf_file:
        instance.pdf_file.delete(True)
