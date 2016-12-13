from django.core.management.base import BaseCommand, CommandError
from website.models import Person, Keyword, Talk, Project, Project_umbrella, Project_Role
import xmltodict as xd
from django.core.files import File
import requests
from django.utils import timezone
from datetime import date, datetime
import os
from random import choice


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

def isimage(filename):
    """true if the filename's extension is in the content-type lookup"""
    ext2conttype = {"jpg": "image/jpeg",
                "jpeg": "image/jpeg",
                "png": "image/png",
                "gif": "image/gif"}
    filename = filename.lower()
    return filename[filename.rfind(".")+1:] in ext2conttype
#select random image from given directory
def get_random_starwars(direc):
    """Gets a random star wars picture to assign to new author"""
    images = [f for f in os.listdir(direc) if isimage(f)]
    return choice(images)


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
            #hardcoded location of directory to pull sample iamges from
            direc = "import/images/StarWarsFiguresFullSquare/Rebels/"
            starwars = get_random_starwars(direc)
            image = File(open(direc+starwars, 'rb'))
            new_person=Person(first_name=author[0], last_name=author[2], middle_name=author[1], image=image, easter_egg=image)
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


def parse_umbrellas(umbrellas):
    return [word.strip() for word in umbrellas.split(",")]

def get_umbrellas(umbrellas):
    ret=[]
    for umbrella in umbrellas:
        test_um = Project_umbrella.objects.filter(name=umbrella)
        if len(test_um) > 0:
            ret.append(test_um[0])
        else:
            new_umbrella = Project_umbrella(name=umbrella, short_name=umbrella.lower().replace(" ", ""))
            new_umbrella.save()
            ret.append(new_umbrella)
    return ret

def get_project(project_name, project_umbrellas, authors, keywords, talk):
    test_proj = Project.objects.filter(name=project_name)
    if len(test_proj) > 0:
        proj = test_proj[0]
        for author in authors:
            test_auth = proj.project_role_set.filter(person=author)
            if len(test_auth) == 0:
                start_date = proj.start_date if proj.start_date else datetime.now()
                proj_role=Project_Role(person=author, project=proj, start_date=start_date)
                proj_role.save()
        for keyword in keywords:
            test_key = proj.keywords.filter(keyword=keyword.keyword)
            if len(test_key) == 0:
                proj.keywords.add(keyword)
        umbrellas = get_umbrellas(parse_umbrellas(project_umbrellas))
        for umbrella in umbrellas:
            talk.project_umbrellas.add(umbrella)
            test_umb = proj.project_umbrellas.filter(name=umbrella.name)
            if len(test_umb) == 0:
                proj.project_umbrellas.add(umbrella)
        return proj
    else:
        short_title=project_name.lower().replace(" ", "")
        proj = Project(name=project_name, short_name=short_title)
        proj.save()
        umbrellas = get_umbrellas(parse_umbrellas(project_umbrellas))
        for umbrella in umbrellas:
            proj.project_umbrellas.add(umbrella)
            talk.project_umbrellas.add(umbrella)
        for author in authors:
            start_date = proj.start_date if proj.start_date else datetime.now()
            proj_role=Project_Role(person=author, project=proj, start_date=start_date)
            proj_role.save()
        for keyword in keywords:
            proj.keywords.add(keyword)
        return proj

#Returns true if a title already exists in the database to avoid duplication
def exists(title):
    test_title=Publication.objects.filter(title=title)
    if len(test_title)>0:
        return True
    else:
        return False

class Command(BaseCommand):
    help='This is a command to import talks from jons talk xml format. It will handle adding of new authors/keywords as needed. Pulls pdfs and pptx files from Jons site cs.umd.edu/~jonf'
    
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
                #If this talk has already been read we can reuse the same PDF.
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
                    filename = 'import/temp/'+file_name_short+".pdf"
                    dirname = os.path.dirname(filename)
                    if not os.path.exists(dirname):
                        os.makedirs(dirname)
                    temp_file = open(filename, 'wb')
                    temp_file.write(res.content)
                    temp_file.close()
                    pdf_file = File(open(filename, 'rb'))
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
                    project = get_val_key('project', entry)
                    project_umbrellas = get_val_key('project_umbrellas', entry)
                    if project != None and len(project)>0:
                        project_obj=get_project(project, project_umbrellas, speaker_list, keyword_list, new_talk)
                        print(project_obj)
                        new_talk.projects.add(project_obj)
                    elif project_umbrellas != None and len(project_umbrellas) > 0:
                        umbrellas = get_umbrellas(parse_umbrellas(project_umbrellas))
                        for umbrella in umbrellas:
                            new_talk.project_umbrellas.add(umbrella)
        #Clean out the temp directory when you're done
        os.system("rm import/temp/*")
