from django.core.management.base import BaseCommand, CommandError
from website.models import Person, Position, Keyword, Publication, Video, Project, Project_umbrella, Project_Role
import bibtexparser
from django.core.files import File
import requests
from django.utils.six import BytesIO
from rest_framework.parsers import JSONParser
from website.serializers import PublicationSerializer
from django.utils import timezone
from datetime import date, datetime
import os
from random import choice
import urllib.request
import tempfile
import string
import shutil

def get_authors(pub):
    ret = list()
    for author in pub['authors']:
        print(author)
        if Person.objects.filter(first_name=author['first_name'], last_name=author['last_name']) is not None:
            pass
        else:
            new_person = Person(first_name=author['first_name'], middle_name=author['middle_name'], last_name=author['last_name'])

class Command(BaseCommand):
    def handle(self, *args, **options):
        url = 'https://makeabilitylab-test.cs.washington.edu/api/pubs/?format=json'
        response = requests.get(url).content
        stream = BytesIO(response)
        data = JSONParser().parse(stream)
        temp_dir = os.path.abspath('.')
        temp_dir = os.path.join(temp_dir, 'media', 'temp')
        temp_dir_image = os.path.abspath('.')
        temp_dir_image = os.path.join('media', 'person')


        print('preprocessing data')
        for item in data:
            url = item['pdf_file']
            title = url.split('/')[-1]
            r = requests.get(url, stream=True)
            file_path = os.path.join(temp_dir, title)
            with open(file_path, 'wb') as f:
                f.write(r.content)
            for object in item['authors']:
                image_url = object['image']
                easter_egg_url = object['easter_egg']
                r_image = requests.get(image_url, stream=True)
                r_ee = requests.get(easter_egg_url, stream=True)
                image_file_name = image_url.split('/')[-1]
                ee_file_name = easter_egg_url.split('/')[-1]
                image_file_path = os.path.join(temp_dir_image, image_file_name)
                ee_file_path = os.path.join(temp_dir_image, ee_file_name)
                with open(image_file_path, 'wb') as f:
                    f.write(r_image.content)
                with open(ee_file_path, 'wb') as f:
                    f.write(r_ee.content)
                object['image'] = File(open(image_file_path, 'rb'))
                object['easter_egg'] = File(open(ee_file_path, 'rb'))
            item['pdf_file'] = File(open(os.path.join('.', 'media', 'temp', title), 'rb'))
        serializer = PublicationSerializer(data=data, many=True)
        print('saving data...')
        serializer.is_valid()
        print(serializer.is_valid())
        print(serializer.errors)
        serializer.save()








    
