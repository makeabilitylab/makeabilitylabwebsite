from django.core.management.base import BaseCommand, CommandError
from website.models import Person, Keyword, Talk
import xmltodict as xd
from django.core.files import File
import requests
from django.utils import timezone
from datetime import date, datetime
import os


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
    authors_names=author_list.split(", ")
    for author_ind in authors_names:
        if 'and ' in author_ind:
            #if 'and' == author_ind.strip()[:3]:
                
            print(author_ind)
            last_two = author_ind.split("and ")
            print(last_two)
            for ind in last_two:
                ind = ind.strip()
                print(ind)
                names = ind.strip().split(" ")
                first = names[0]
                last = names[len(names)-1]
                middle = " ".join(names[1:-1]).strip()
                auth = (first, middle, last)
                if len(names)>1:
                    print(auth)
                    ret.append(auth)
        else:
            names = author_ind.strip().split(" ")
            first = names[0]
            last = names[len(names)-1]
            middle = " ".join(names[1:-1]).strip()
            auth = (first, middle, last)
            ret.append(auth)
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
    if keyword_text.find(';') == -1:
        ret = [word.strip().lower() for word in keyword_text.split(",")]
    else:
        ret = [word.strip().lower() for word in keyword_text.split(";")]
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

#Returns true if a title already exists in the database to avoid duplication
def exists(title):
    test_title=Publication.objects.filter(title=title)
    if len(test_title)>0:
        return True
    else:
        return False

class Command(BaseCommand):

    def handle(self, *args, **options):
        file_dic={}
        for talk_file in os.listdir(os.getcwd()+"/import/xml"):
            print("Parsing file "+talk_file)
            with open('import/xml/'+talk_file) as xml_file:
                talk_database=xd.parse(xml_file.read())['talks']['talk']
            #Iterate over all entries in each file
            for entry in talk_database:
                title = get_val_key('title', entry)
                forum_name = get_val_key('forum', entry)
                location = get_val_key('location', entry)
                date_text = get_val_key('date', entry)
                print(date_text)
                date=datetime.strptime(date_text, '%B %d, %Y')
                slideshare_url = get_val_key('slideshare', entry)
                print(slideshare_url)
                pdf_file = None
                pptx_file = None
                deck_url = get_val_key('deck', entry)
                if deck_url != None:
                    deck_url = "http://cs.umd.edu/~jonf/"+deck_url
                    res = requests.get(deck_url, stream=True)
                    temp_file = open('import/temp/'+title+'.pptx', 'wb')
                    for chunk in res.iter_content(chunk_size=4096):
                        if chunk:
                            temp_file.write(chunk)
                    temp_file.close()
                    pptx_file = File(open('import/temp/'+title+'.pptx', 'rb'))
                if title in file_dic.keys():
                    pdf_file = file_dic[title]
                    print("Using existing copy of pdf...")
                elif get_val_key('talk_pdf', entry)!=None:
                    pdf_url = "http://cs.umd.edu/~jonf/"+get_val_key('talk_pdf', entry)
                    res = requests.get(pdf_url)
                    temp_file = open('import/temp/'+title+".pdf", 'wb')
                    temp_file.write(res.content)
                    temp_file.close()
                    pdf_file = File(open("import/temp/"+title+".pdf", 'rb'))
                    file_dic[title] = pdf_file
                elif get_val_key('deck', entry):
                    #Handle pptx
                    file_name=get_val_key('deck', entry)
                    
                    file_name_short=file_name[file_name.find("/")+1:file_name.find(".")]
                    deck_url = "http://cs.umd.edu/~jonf/talks/autogen_pdfs/"+file_name_short+".pdf"
                    print(deck_url)
                    res = requests.get(deck_url)
                    temp_file = open('import/temp/'+file_name_short+".pdf", 'wb')
                    temp_file.write(res.content)
                    temp_file.close()
                    pdf_file = File(open('import/temp/'+file_name_short+".pdf", 'rb'))
                    file_dic[title] = pdf_file

                if pdf_file!=None:
                    if pptx_file!=None:
                        new_talk = Talk(title=title, date=date.date(), location=location, forum_name=forum_name, pdf_file=pdf_file, raw_file=pptx_file, slideshare_url=slideshare_url)
                    else:
                        new_talk = Talk(title=title, date=date.date(), location=location, forum_name=forum_name, pdf_file=pdf_file, slideshare_url=slideshare_url)
                    # Each item must be saved before authors and keywords can be added
                    new_talk.save()
                    #Info on how to do the many to many crap is from here https://docs.djangoproject.com/en/1.9/topics/db/examples/many_to_many/
                    speaker_list = get_authors(parse_authors(get_val_key('authors', entry)))
                    for speaker in speaker_list:
                        new_talk.speakers.add(speaker)
                    keyword_list = get_keywords(parse_keywords(get_val_key('keywords', entry)))
                    for keyword in keyword_list:
                        new_talk.keywords.add(keyword)
        os.system("rm import/temp/*")
