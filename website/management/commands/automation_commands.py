from django.core.management.base import BaseCommand, CommandError
from website.models import Person, Position, Keyword, Publication
import bibtexparser
from django.core.files import File
import requests
from django.utils import timezone
from datetime import date, datetime


#Takes a key and a dictionary, returns the val if the key exists and otherwise returns none
def get_val_key(key, dic):
    if key in dic.keys():
        return dic[key]
    else:
        return None

#Relies on names being seperated by and
#Parses author list of the form lastname, rest of name and...
#Can parse out a middle name as well as first/last name
def parse_authors(author_list):
    i=0
    ret=[]
    authors_names=author_list.split(" and ")
    for author_ind in authors_names:
        last=author_ind[:author_ind.find(",")]
        rest=author_ind[author_ind.find(",")+2:].split(" ")
        middle=""
        for n in rest[1:]:
            middle+=n+" "
        name=(rest[0], middle.strip(), last)
        ret.append(name)
    return ret

#Takes a list of authors in the form [(first, middle, last)] and returns a list of author objects, creating those that don't already exist
#Created People don't have a position or any information besides a name
#Info on how to do the queries came from here https://docs.djangoproject.com/en/1.9/topics/db/queries/
def get_authors(author_list):
    ret=[]    
    for author in author_list:
        test_p = Person.objects.filter(first_name = author[0], last_name = author[2])
        if len(test_p)>0:
            ret.append(test_p[0])
        else:
            new_person=Person(first_name=author[0], last_name=author[2], middle_name=author[1])
            new_person.save()
            ret.append(new_person)
    return ret

#Takes a string with lots of keywords and returns a list of those words
def parse_keywords(keyword_text):
    ret = [word.strip() for word in keyword_text.split(",")]
    print(ret)
    return ret

#Takes a list of keyword strings and returns a list of keyword objects, creating those that don't already exist
#Info on how to do the queries came from here https://docs.djangoproject.com/en/1.9/topics/db/queries/
def get_keywords(keyword_list):
    ret=[]
    for keyword in keyword_list:
        test_k=Keyword.objects.filter(keyword=keyword)
        if len(test_k)>0:
            ret.append(test_k[0])
        else:
            new_keyword=Keyword(keyword=keyword)
            new_keyword.save()
            ret.append(new_keyword)
    return ret

class Command(BaseCommand):
    
    def handle(self, *args, **options):
        with open('media/bibtex/froehlich_citations.bib') as bibtex_file:
            bibtex_str = bibtex_file.read()

        bib_database = bibtexparser.loads(bibtex_str)
        # print(bib_database.entries)
        print(bib_database.entries[0].keys())
        print(bib_database.entries[0]['author'])
        print(bib_database.entries[0]['keyword'])
        for entry in bib_database.entries:
            title=get_val_key('title', entry)
            book_title=get_val_key('booktitle', entry)
            book_title_short=get_val_key('booktitle_short', entry)
            
            num_pages=get_val_key('numpages', entry)
            geo_location=get_val_key('location', entry)
            video_url=get_val_key('video_url', entry)
            #Compare to pub_venue_type
            pub_type=get_val_key('pub_type', entry)
            date_text=get_val_key('month', entry)+", "+get_val_key("year", entry)
            
            date=datetime.strptime(date_text, '%B, %Y')
            print(date.date())
            if pub_type==None:
                pub_venue_type="Other"
            elif "conference" in pub_type:
                pub_venue_type="Conference"
            elif "journal" in pub_type:
                pub_venue_type="Journal"
            elif "thesis" in pub_type:
                pub_venue_type="MS Thesis"
            elif "workshop" in pub_type:
                pub_venue_type="Workshop"
            elif "poster" in pub_type:
                pub_venue_type="Poster"
            elif "book" in pub_type:
                pub_venue_type="Book"
            #Is this right?
            elif "doctoral_colloqium" in pub_type:
                pub_venue_type="PhD Dissertation"
            #the rest aren't based  on examples so they need to be checked over for consistency with established practice
            elif "demo" in pub_type:
                pub_venue_type="Demo"
            elif "article" in pub_type:
                pub_venue_type="Article"
            #This should probably be moved above book once it's been checked
            elif "book_chapter" in pub_type:
                pub_venue_type="Book Chapter"
            elif "work_in_progress" in pub_type:
                pub_venue_type="Work in Progress"
            elif "late_breaking" in pub_type:
                pub_venue_type="Late Breaking Result"
            else:
                pub_venue_type="Other"
            peer_reviewed_val=get_val_key('peer_reviewed', entry)
            if peer_reviewed_val=="yes":
                peer_reviewed=True
            else:
                peer_reviewed=False
            total_papers_submitted=get_val_key('total_paper_submitted', entry)
            total_papers_accepted=get_val_key('total_papers_accepted', entry)
            #Parse award choices
            award_name=get_val_key('award', entry)
            if award_name==None:
                award=None
            elif "Nomination" in award_name:
                award="Best Paper Nominee"
            elif "Honorable Mention" in award_name:
                award="Honorable Mention"
            elif "Award" in award_name:
                award="Best Paper Award"
            else:
                award=None
            pdf_file_loc="http://cs.umd.edu/~jonf/"+get_val_key('local_pdf', entry)
            res=requests.get(pdf_file_loc)
            temp_file=open("media/temp/temp.pdf", 'wb')
            temp_file.write(res.content)
            temp_file.close()
            pdf_file=File(open("media/temp/temp.pdf", 'rb'))
            #Create the new publication
            new_pub=Publication(title=title, geo_location=geo_location, book_title=book_title, book_title_short=book_title_short, num_pages=num_pages, video_url=video_url, pub_venue_type=pub_venue_type, peer_reviewed=peer_reviewed, total_papers_accepted=total_papers_accepted, total_papers_submitted=total_papers_submitted, award=award, pdf_file=pdf_file, date=date.date())
            #Items have to be saved before you can do many to many queries
            new_pub.save()
            #Info on how to do the many to many crap is from here https://docs.djangoproject.com/en/1.9/topics/db/examples/many_to_many/
            #Parse authors
            author_str_list=parse_authors(get_val_key("author", entry))
            author_obj_list=get_authors(author_str_list)
            for author in author_obj_list:
                new_pub.authors.add(author)
            #Parse keywords
            keyword_str_list=parse_keywords(get_val_key('keyword', entry))
            keyword_obj_list=get_keywords(keyword_str_list)

            for keyword in keyword_obj_list:
                new_pub.keywords.add(keyword)

            

    
