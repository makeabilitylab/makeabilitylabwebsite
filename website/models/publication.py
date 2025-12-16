import os
from django.db import models
from website.models import Artifact
import logging # for logging
from datetime import date # for date comparisons
import re # for regular expressions
import website.utils.timeutils as timeutils

class PubAwardType(models.TextChoices):
    BEST_ARTIFACT_AWARD = "Best Artifact Award"
    BEST_ARTIFACT_RUNNERUP_AWARD = "Best Artifact Runner-up Award"
    BEST_PAPER_AWARD = "Best Paper Award"
    HONORABLE_MENTION = "Honorable Mention"
    BEST_PAPER_NOMINATION = "Best Paper Nominee"
    TEN_YEAR_IMPACT_AWARD = "10-Year Impact Award"

    # This is a new UIST award started in 2024
    # Jae's CookAR paper won it
    BEST_PAPER_BELONGING_AND_INCLUSION_AWARD = "Best Paper Belonging and Inclusion Award"

    # This is a new CSCW award. Emma's paper won it in 2021
    # Recognitions for Contribution to Diversity and Inclusion represent strong examples of 
    # work that focuses on or serves minorities, otherwise excluded individuals or populations,
    # or intervenes in systemic structures of inequality, and selection of these recognitions were 
    # overseen by Equity and Accessibility Co-Chairs
    DIVERSITY_AND_INCLUSION_AWARD = "Diversity and Inclusion Award"


class PubType(models.TextChoices):
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

# This retrieves a Python logging instance (or creates it)
_logger = logging.getLogger(__name__)

class Publication(Artifact):
    UPLOAD_DIR = 'publications/'
    THUMBNAIL_DIR = os.path.join(UPLOAD_DIR, 'images/')

    book_title = models.CharField(max_length=255, null=True)
    book_title.help_text = "This is the long-form proceedings title. For example, for UIST, this would be 'Proceedings of the 27th Annual ACM Symposium on User " \
                           "Interface Software and Technology.' For CHI, 'Proceedings of the 2017 CHI Conference on " \
                           "Human Factors in Computing Systems' "

    official_url = models.URLField(blank=True, null=True)
    official_url.help_text = "The official url link to the paper, often a DOI url like https://doi.org/10.1145/3441852.3476542"

    arxiv_url = models.URLField(blank=True, null=True)
    arxiv_url.help_text = "The arXiv url link to the paper, if available (e.g., https://arxiv.org/abs/2508.08524)"

    # Publications can have corresponding videos, talks, posters, etc.
    video = models.OneToOneField('Video', on_delete=models.DO_NOTHING, null=True, blank=True)
    talk = models.ForeignKey('Talk', blank=True, null=True, on_delete=models.DO_NOTHING)
    poster = models.ForeignKey('Poster', blank=True, null=True, on_delete=models.DO_NOTHING)
    code_repo_url = models.URLField(blank=True, null=True)
    code_repo_url.help_text = "URL to github or gitlab"

    # Publication details often required for bibtex
    series = models.CharField(max_length=255, blank=True, null=True)
    isbn = models.CharField(max_length=255, blank=True, null=True)
    doi = models.CharField(max_length=255, blank=True, null=True)
    publisher = models.CharField(max_length=255, blank=True, null=True)
    publisher_address = models.CharField(max_length=255, blank=True, null=True)
    acmid = models.CharField(max_length=255, blank=True, null=True)

     # Page numbers
    num_pages = models.IntegerField(null=True)
    num_pages.help_text = "The total number of pages in this publication (including references)"

    # TODO, see if there is an IntegerRangeField or something like that for page_num_start and end
    # There is an IntegerRangeField but it's only for Postgres... hmm
    page_num_start = models.IntegerField(blank=True, null=True)
    page_num_end = models.IntegerField(blank=True, null=True)

    pub_venue_type = models.CharField(max_length=50, choices=PubType.choices, null=True)
    extended_abstract = models.BooleanField(null=True)
    extended_abstract.help_text = "If the paper is not a *full* paper, it's likely an extended abstract (like a poster, demo, etc.)"
    peer_reviewed = models.BooleanField(null=True)

    total_papers_accepted = models.IntegerField(blank=True, null=True)
    total_papers_accepted.help_text = "The total number of papers accepted to the venue (if known)"
    total_papers_submitted = models.IntegerField(blank=True, null=True)
    total_papers_submitted.help_text = "The total number of papers submitted to the venue (if known)"

    award = models.CharField(max_length=50, choices=PubAwardType.choices, blank=True, null=True)

    def get_upload_dir(self, filename):
        return os.path.join(self.UPLOAD_DIR, filename)

    def get_upload_thumbnail_dir(self, filename):
        return os.path.join(self.THUMBNAIL_DIR, filename)
    
    def get_person(self):
        """Returns the first author"""
        return self.authors.all()[0]
    
    def get_formatted_forum_name(self):
        """Returns the formatted forum name with 'Proceedings of' prepended and year appended"""
        
        # If there's no forum name, return an empty string
        if not self.forum_name:
            return ""
        
        formatted_forum_name = ""

        if self.pub_venue_type == PubType.CONFERENCE:
            formatted_forum_name = "Proceedings of "
        elif self.is_extended_abstract():
            formatted_forum_name = "Extended Abstract Proceedings of "

        formatted_forum_name += self.forum_name
        formatted_forum_name += f" {self.date.year}"
        return formatted_forum_name

    def is_extended_abstract(self):
        """Returns True if this publication is an extended abstract"""
        return (self.extended_abstract or
                self.pub_venue_type == PubType.POSTER or
                self.pub_venue_type == PubType.DEMO or
                self.pub_venue_type == PubType.WIP or
                self.pub_venue_type == PubType.DOCTORAL_CONSORTIUM)

    def get_acceptance_rate(self):
        """Returns the acceptance rate as a percentage"""
        if self.total_papers_accepted and self.total_papers_submitted:
            return 100 * (self.total_papers_accepted / self.total_papers_submitted)
        else:
            return -1

    def is_best_paper(self):
        """Returns true if earned best paper, best artifact, or test of time award"""
        return self.award == PubAwardType.BEST_PAPER_AWARD or \
            self.award == PubAwardType.BEST_ARTIFACT_AWARD or \
            self.award == PubAwardType.TEN_YEAR_IMPACT_AWARD

    def is_honorable_mention(self):
        """Returns true if earned honorable mention or best paper nomination"""
        return self.award == PubAwardType.HONORABLE_MENTION or \
            self.award == PubAwardType.BEST_ARTIFACT_RUNNERUP_AWARD or \
            self.award == PubAwardType.BEST_PAPER_NOMINATION

    def to_appear(self):
        """Returns true if the publication date happens in the future (e.g., tomorrow or later)"""
        return self.date and self.date > date.today()

    def get_citation_as_html(self):
        """Returns a human readable citation as html"""
        citation = ", ".join([author.get_citation_name(full_name=False) for author in self.authors.all()]) + " "

        citation += f"({self.date.year}). "
        citation += self.title + ". "
        citation += f"<i>{self.get_formatted_forum_name()}</i>. "

        if self.official_url:
            citation += f"<a href={self.official_url}>{self.official_url}</a>"

        return citation

    def get_bibtex_id(self):
        """Generates and returns the bibtex id for this paper"""
        bibtex_id = self.get_first_author_last_name()

        forum = "unknown"
        if self.forum_name:
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

        # This line of code is removing all characters from bibtex_id that are not alphanumeric 
        # (i.e., not a letter or a number).
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

        if self.pub_venue_type is PubType.JOURNAL or\
            self.pub_venue_type is PubType.ARTICLE:
            bibtex += "@article{"
        else:
            bibtex += "@inproceedings{"


        bibtex += self.get_bibtex_id() + newline

        # start author block
        bibtex += " author={"
        citation_names = [author.get_citation_name(full_name=True) for author in self.authors.all()]
        bibtex += ' and '.join(citation_names)
        bibtex += "}," + newline

        # we (strangely) use triple braces here so that we can include literal { and } in the title
        bibtex += f" title={{{self.title}}},{newline}"
        bibtex += f" booktitle={{{self.book_title}}},{newline}"
        bibtex += f" booktitleshort={{{self.get_formatted_forum_name()}}},{newline}"

        if self.series:
            bibtex += " series = {" + self.series + "}," + newline

        bibtex += " year={{{}}},{}".format(self.date.year, newline)

        if self.isbn:
            bibtex += " isbn={{{}}},{}".format(self.isbn, newline)

        if self.location:
            bibtex += " location={{{}}},{}".format(self.location, newline)

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