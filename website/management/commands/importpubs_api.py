from django.core.management.base import BaseCommand, CommandError
from website.models import Person, Position, Keyword, Publication, Video, Project, Project_umbrella, Project_Role
import bibtexparser
from django.core.files import File
import requests
from django.utils import timezone
from datetime import date, datetime
import os
from random import choice


# Takes a key and a dictionary, returns the val if the key exists and otherwise returns none
def get_val_key(key, dic):
    if key in dic.keys():
        return dic[key]
    else:
        return None

def parse_authors(author_list):
    i = 0
    ret = list()
    authors_names =

'''
# Relies on names being separated by and
# Parses author list of the form lastname, rest of name and...
# Can parse out a middle name as well as first/last name
def parse_authors(author_list):
    i = 0
    ret = []
    authors_names = author_list.split(" and ")
    for author_ind in authors_names:
        last = author_ind[:author_ind.find(",")]
        rest = author_ind[author_ind.find(",") + 2:].split(" ")
        middle = ""
        for n in rest[1:]:
            middle += n + " "
        name = (rest[0], middle.strip(), last)
        ret.append(name)
    return ret


# Simple check to seee if a file is an image. Not strictly necessary but included for safety
def isimage(filename):
    """true if the filename's extension is in the content-type lookup"""
    ext2conttype = {"jpg": "image/jpeg",
                    "jpeg": "image/jpeg",
                    "png": "image/png",
                    "gif": "image/gif"}
    filename = filename.lower()
    return filename[filename.rfind(".") + 1:] in ext2conttype


# Randomly selects an image from the given directory
def get_random_starwars(direc):
    """Gets a random star wars picture to assign to new author"""
    images = [f for f in os.listdir(direc) if isimage(f)]
    return choice(images)


# Takes a list of authors in the form [(first, middle, last)] and returns a list of author objects, creating those that don't already exist
# Created People don't have a position or any information besides a name
# Info on how to do the queries came from here https://docs.djangoproject.com/en/1.9/topics/db/queries/
def get_authors(author_list):
    ret = []
    for author in author_list:
        test_p = Person.objects.filter(first_name=author[0], last_name=author[2])
        if len(test_p) > 0:
            ret.append(test_p[0])
        else:
            # Hard coded location of current import directory, in this case starwars rebel minifigs.
            direc = "import/images/StarWarsFiguresFullSquare/Rebels/"
            starwars = get_random_starwars(direc)
            image = File(open(direc + starwars, 'rb'))
            new_person = Person(first_name=author[0], last_name=author[2], middle_name=author[1], image=image,
                                easter_egg=image)
            new_person.save()
            ret.append(new_person)
    return ret


# Takes a string with lots of keywords and returns a list of those words
def parse_keywords(keyword_text):
    if keyword_text.find(';') == -1:
        ret = [word.strip().lower() for word in keyword_text.split(",")]
    else:
        ret = [word.strip().lower() for word in keyword_text.split(";")]
    return ret


# Takes a list of keyword strings and returns a list of keyword objects, creating those that don't already exist
# Info on how to do the queries came from here https://docs.djangoproject.com/en/1.9/topics/db/queries/
def get_keywords(keyword_list):
    ret = []
    for keyword in keyword_list:
        test_k = Keyword.objects.filter(keyword=keyword)
        if len(test_k) > 0:
            ret.append(test_k[0])
        else:
            new_keyword = Keyword(keyword=keyword)
            new_keyword.save()
            ret.append(new_keyword)
    return ret


def get_video(url, preview_url, date, title, caption):
    new_video = Video(video_url=url, video_preview_url=preview_url, date=date, title=title, caption=caption)
    new_video.save()
    return new_video


def parse_umbrellas(umbrellas):
    return [word.strip() for word in umbrellas.split(",")]


def get_umbrellas(umbrellas):
    ret = []
    for umbrella in umbrellas:
        test_um = Project_umbrella.objects.filter(name=umbrella)
        if len(test_um) > 0:
            ret.append(test_um[0])
        else:
            new_umbrella = Project_umbrella(name=umbrella, short_name=umbrella.lower().replace(" ", ""))
            new_umbrella.save()
            ret.append(new_umbrella)
    return ret


def get_project(project_name, project_umbrellas, authors, keywords, pub):
    test_proj = Project.objects.filter(name=project_name)
    if len(test_proj) > 0:
        proj = test_proj[0]
        for author in authors:
            test_auth = proj.project_role_set.filter(person=author)
            if len(test_auth) == 0:
                start_date = proj.start_date if proj.start_date else datetime.now()
                proj_role = Project_Role(person=author, project=proj, start_date=start_date)
                proj_role.save()
        for keyword in keywords:
            test_key = proj.keywords.filter(keyword=keyword.keyword)
            if len(test_key) == 0:
                proj.keywords.add(keyword)
        umbrellas = get_umbrellas(parse_umbrellas(project_umbrellas))
        for umbrella in umbrellas:
            pub.project_umbrellas.add(umbrella)
            test_umb = proj.project_umbrellas.filter(name=umbrella.name)
            if len(test_umb) == 0:
                proj.project_umbrellas.add(umbrella)
        return proj
    else:
        short_title = project_name.lower().replace(" ", "")
        proj = Project(name=project_name, short_name=short_title)
        proj.save()
        umbrellas = get_umbrellas(parse_umbrellas(project_umbrellas))
        for umbrella in umbrellas:
            proj.project_umbrellas.add(umbrella)
            pub.project_umbrellas.add(umbrella)
        for author in authors:
            start_date = proj.start_date if proj.start_date else datetime.now()
            proj_role = Project_Role(person=author, project=proj, start_date=start_date)
            proj_role.save()
        for keyword in keywords:
            proj.keywords.add(keyword)
        return proj


# Returns true if a title already exists in the database to avoid duplication
def exists(title):
    test_title = Publication.objects.filter(title=title)
    if len(test_title) > 0:
        return True
    else:
        return False


class Command(BaseCommand):
    jon_webpage_url = "http://cs.umd.edu/~jonf/"
    jon_bibtex_url = "http://www.cs.umd.edu/~jonf/bibtex_citations.txt"
    import_bibtex_dir = "/import/bibtex"

    help = "This is an importer for bibtex publication entries. " \
           " It will first check and read all files from ." + import_bibtex_dir + \
           ". If none exist, the importer will pull directly from " + jon_bibtex_url + \
           ". Regardless of source, for each bibtex entry, we will attempt to import it into the Django database." \
           " PDFs for these files are pulled from Jon's site" + jon_webpage_url + \
           ". The importer automatically handles adding of authors and keywords if they do not already exist."

    def handle(self, *args, **options):

        bib_file_count = 0
        full_bibtex_path = os.path.join(os.getcwd(), self.import_bibtex_dir)
        if os.path.exists(full_bibtex_path):
            for bib_file in os.listdir(full_bibtex_path):
                print("Parsing file " + bib_file)
                with open('import/bibtex/' + bib_file) as bibtex_file:
                    bibtex_str = bibtex_file.read()

                self.loadDatabase(bibtex_str)
                bib_file_count = bib_file_count + 1

        if bib_file_count == 0:
            print("No local bibtex files found, attempting to load: " + self.jon_bibtex_url)
            bibtex_str = requests.get(self.jon_bibtex_url).text
            print(bibtex_str)
            self.loadDatabase(bibtex_str)

    def loadDatabase(self, bibtex_str):
        # load the bibtex entries into a database
        bib_database = bibtexparser.loads(bibtex_str)

        # print(bib_database.entries)
        for entry in bib_database.entries:
            pdf_file_loc = self.jon_webpage_url + get_val_key('local_pdf', entry)
            title = get_val_key('title', entry)

            print(str(exists(title)) + " " + title)
            # This is important because if local_pdf is not set then this part will crash, if a PDF is not included nothing will be done
            # TODO see what to do if no PDF is included
            # skip entry if PDF is missing, title is missing, or if title is already in the database

            if pdf_file_loc != self.jon_webpage_url and title != None and not exists(title):

                book_title = get_val_key('booktitle', entry)
                book_title_short = get_val_key('booktitle_short', entry)

                num_pages = get_val_key('numpages', entry)
                geo_location = get_val_key('location', entry)
                print(geo_location)
                video_url = get_val_key('video_url', entry)

                # Compare to pub_venue_type
                pub_type = get_val_key('pub_type', entry)
                date_text = get_val_key('month', entry) + ", " + get_val_key("year", entry)
                series = get_val_key('series', entry)
                isbn = get_val_key('isbn', entry)
                doi = get_val_key('doi', entry)
                publisher = get_val_key('published', entry)
                publisher_address = get_val_key('address', entry)
                page_range = get_val_key('pages', entry)
                acmid = get_val_key('acmid', entry)
                url = get_val_key('url', entry)

                # There are many ways that page range doesn't exist so this is to cover those cases
                if page_range != None and page_range != 'tbd' and page_range != '-' and page_range != "":
                    # This is a workaround for entries with only one - instead of two
                    if "-" in page_range and not "--" in page_range:
                        page_start = page_range.split('-')[0]
                        page_end = page_range.split('-')[1]
                    else:
                        page_start = page_range.split('--')[0]
                        page_end = page_range.split('--')[1]
                    # This is a workaround for entries with this form {9:1--9:27},
                    if ":" in page_start:
                        page_start = page_start.split(":")[1]
                        page_end = page_end.split(":")[1]
                else:
                    page_start = None
                    page_end = None
                date = datetime.strptime(date_text, '%B, %Y')
                print(date.date())

                # Check type of pub and convert it to appropriate value
                if pub_type == None:
                    pub_venue_type = "Other"
                elif "conference" in pub_type:
                    pub_venue_type = "Conference"
                elif "journal" in pub_type:
                    pub_venue_type = "Journal"
                elif "thesis" in pub_type:
                    pub_venue_type = "MS Thesis"
                elif "workshop" in pub_type:
                    pub_venue_type = "Workshop"
                elif "poster" in pub_type:
                    pub_venue_type = "Poster"
                elif "book" in pub_type:
                    pub_venue_type = "Book"

                # Is this right?
                # TODO Fix this. This is not correct.
                elif "doctoral_colloqium" in pub_type:
                    pub_venue_type = "PhD Dissertation"

                # the rest aren't based  on examples so they need to be checked over for consistency with established practice
                elif "demo" in pub_type:
                    pub_venue_type = "Demo"
                elif "article" in pub_type:
                    pub_venue_type = "Article"

                # This should probably be moved above book once it's been checked
                elif "book_chapter" in pub_type:
                    pub_venue_type = "Book Chapter"
                elif "work_in_progress" in pub_type:
                    pub_venue_type = "Work in Progress"
                elif "late_breaking" in pub_type:
                    pub_venue_type = "Late Breaking Result"
                else:
                    pub_venue_type = "Other"
                peer_reviewed_val = get_val_key('peer_reviewed', entry)
                if peer_reviewed_val == "yes":
                    peer_reviewed = True
                else:
                    peer_reviewed = False

                total_papers_submitted = get_val_key('total_paper_submitted', entry)
                total_papers_accepted = get_val_key('total_papers_accepted', entry)

                # Parse award choices
                award_name = get_val_key('award', entry)
                if award_name == None:
                    award = None
                elif "Nomination" in award_name:
                    award = "Best Paper Nominee"
                elif "Honorable Mention" in award_name:
                    award = "Honorable Mention"
                elif "Award" in award_name:
                    award = "Best Paper Award"
                else:
                    award = None

                # Import file from web, then write it to a file, and finally open it as a File for django
                res = requests.get(pdf_file_loc)

                # TODO: update the filename so that it's FIRSTAUTHORLASTNAME_TITLECAMELCASE_VENUEYEAR.pdf
                filename = "import/temp/" + title + ".pdf"
                dirname = os.path.dirname(filename)
                if not os.path.exists(dirname):
                    os.makedirs(dirname)
                temp_file = open(filename, 'wb')
                temp_file.write(res.content)
                temp_file.close()
                pdf_file = File(open(filename, 'rb'))

                video_url = get_val_key('video_url', entry)
                preview_video_url = get_val_key('video_preview_url', entry)
                if video_url != None and len(video_url) > 0:
                    video = get_video(video_url, preview_video_url, date.date(), title, book_title_short)
                else:
                    video = None

                # Create the new publication
                # Items have to be saved before you can do many to many queries
                new_pub = Publication(title=title, geo_location=geo_location, book_title=book_title,
                                      book_title_short=book_title_short, num_pages=num_pages,
                                      pub_venue_type=pub_venue_type, peer_reviewed=peer_reviewed,
                                      total_papers_accepted=total_papers_accepted,
                                      total_papers_submitted=total_papers_submitted, award=award, pdf_file=pdf_file,
                                      date=date.date(), video=video, series=series, isbn=isbn, doi=doi,
                                      publisher=publisher, publisher_address=publisher_address, acmid=acmid,
                                      page_num_start=page_start, page_num_end=page_end, official_url=url)
                new_pub.save()

                # Info on how to do the many to many stuff is from here https://docs.djangoproject.com/en/1.9/topics/db/examples/many_to_many/
                # Parse authors
                author_str_list = parse_authors(get_val_key("author", entry))
                author_obj_list = get_authors(author_str_list)
                for author in author_obj_list:
                    new_pub.authors.add(author)
                # Parse keywords
                keyword_str_list = parse_keywords(get_val_key('keyword', entry))
                keyword_obj_list = get_keywords(keyword_str_list)
                for keyword in keyword_obj_list:
                    new_pub.keywords.add(keyword)
                project = get_val_key('project', entry)
                project_umbrellas = get_val_key('project_umbrellas', entry)
                if project != None and len(project) > 0:
                    project_obj = get_project(project, project_umbrellas, author_obj_list, keyword_obj_list, new_pub)
                    print(project_obj)
                    new_pub.projects.add(project_obj)
                elif project_umbrellas != None and len(project_umbrellas) > 0:
                    umbrellas = get_umbrellas(parse_umbrellas(project_umbrellas))
                    for umbrella in umbrellas:
                        new_pub.project_umbrellas.add(umbrella)
                        # Clean out import/temp

        os.system("rm import/temp/*")
'''
