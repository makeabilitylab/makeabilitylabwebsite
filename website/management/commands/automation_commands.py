from django.core.management.base import BaseCommand, CommandError
from website.models import Person, Position, Keyword, Publication
import bibtexparser

class Command(BaseCommand):
    def handle(self, *args, **options):
        with open('media/bibtex/froehlich_citations.bib') as bibtex_file:
            bibtex_str = bibtex_file.read()

        bib_database = bibtexparser.loads(bibtex_str)

        # print(bib_database.entries)
        
        print(bib_database.entries[0])
