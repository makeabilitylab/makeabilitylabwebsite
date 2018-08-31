from rest_framework import serializers
from website.models import Person, Publication, Talk, Video, Project, News
from django.core.files import File
import os
from django.conf import settings
import requests
import glob
import shutil

class PersonSerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        test_p = Person.objects.filter(first_name=validated_data.get('first_name'), last_name=validated_data.get('last_name'))
        if len(test_p) > 0:
            return test_p
        else:

            image_file = validated_data.pop('image')
            easter_egg_file = validated_data.pop('easter_egg')
            image_path = image_file.name
            ee_path = easter_egg_file.name
            image = File(open(image_path, 'rb'))
            easter_egg = File(open(ee_path, 'rb'))
            p = Person.objects.create(image=image, easter_egg=easter_egg, **validated_data)
            image.close()
            easter_egg.close()
            initial_path_image = p.image.path
            initial_path_ee = p.easter_egg.path
            p.image.name = os.path.join('person', p.image.name.split('/')[-1])
            new_path_image = os.path.join(settings.MEDIA_ROOT, p.image.name)
            shutil.copy(initial_path_image, new_path_image)

            p.easter_egg.name = os.path.join('person', p.easter_egg.name.split('/')[-1])
            new_path_ee = os.path.join(settings.MEDIA_ROOT, p.easter_egg.name)
            shutil.move(initial_path_ee, new_path_ee)
            p.save()
            return p

    class Meta:
        model = Person
        fields = '__all__'
        depth = 10

'''
https://stackoverflow.com/questions/38366605/exclude-a-field-from-django-rest-framework-serializer
to exclude a field from serialization, use the exclude feature
example: exclude = ('field1',)

More in depth explanation of how to use Django Rest Framework serializers found here:
http://www.django-rest-framework.org/tutorial/1-serialization/

the serializer will automatically scan relations between objects up to a certain depth and pass it to the JSON
http://www.django-rest-framework.org/api-guide/serializers/#specifying-nested-serialization
'''

class PublicationSerializer(serializers.ModelSerializer):
    authors = PersonSerializer(many=True)

    def create(self, validated_data):
        """
        Create and return a new `Publication` instance, given the validated data
        """
        authors = validated_data.pop('authors')
        serializer = PersonSerializer(data=authors, many=True)
        serializer.is_valid()
        serializer.save()
        pdf_file = validated_data.pop('pdf_file')
        pdf_name = pdf_file.name

        pdf = File(open(pdf_name, 'rb'))
        p = Publication.objects.create(pdf_file=pdf, **validated_data)
        pdf.close()
        for author in authors:
            person = Person.objects.get(first_name=author['first_name'], last_name=author['last_name'])
            p.authors.add(person)
        initial_path = p.pdf_file.path
        p.pdf_file.name = os.path.join('publications', p.pdf_file.name.split('/')[-1])
        new_path = os.path.join(settings.MEDIA_ROOT, p.pdf_file.name)
        shutil.copy(initial_path, new_path)
        p.save()
        #for f in glob.glob('./media/temp/*.pdf'):
        #    shutil.move(f, os.path.join('.', 'media', 'publications'))

        return p
        #serializer = PersonSerializer(data=authors, many=True)
        #if serializer.is_valid(raise_exception=True):
        #    authors = serializer.save(Publication=pub)

    def update(self, instance, validated_data):
        """
        Given a dictionary of deserialized field values, either update
        an existing model instance, or create a new model instance.
        """
        instance.title = validated_data.get('title',instance.title)
        instance.authors =validated_data.get('authors',instance.authors)
        instance.pdf_file =validated_data.get('pdf_file',instance.pdf_file)
        instance.book_title =validated_data.get('book_title',instance.book_title)
        instance.book_title_short =validated_data.get('book_title_short',instance.book_title_short)
        instance.date =validated_data.get('date',instance.date)
        instance.num_pages =validated_data.get('num_pages',instance.num_pages)
        instance.projects =validated_data.get('projects',instance.projects)
        instance.project_umbrellas =validated_data.get('project_umbrellas',instance.project_umbrellas)
        instance.keywords =validated_data.get('keywords',instance.keywords)
        instance.page_num_start =validated_data.get('page_num_start',instance.page_num_start)
        instance.page_num_end =validated_data.get('page_num_end',instance.page_num_end)
        instance.official_url =validated_data.get('official_url',instance.official_url)
        instance.geo_location =validated_data.get('geo_location',instance.geo_location)
        instance.video =validated_data.get('video',instance.video)
        instance.talk =validated_data.get('talk',instance.talk)
        instance.series =validated_data.get('series', instance.series)
        instance.isbn =validated_data.get('isbn',instance.isbn)
        instance.doi =validated_data.get('doi',instance.doi)
        instance.publisher =validated_data.get('publisher',instance.publisher)
        instance.publisher_address =validated_data.get('publisher_address',instance.publisher_address)
        instance.acmid =validated_data.get('acmid',instance.acmid)
        instance.pub_venue_type =validated_data.get('pub_venue_type',instance.pub_venue_type)
        instance.extended_abstract =validated_data.get('extended_abstract',instance.extended_abstract)
        instance.peer_reviewed =validated_data.get('peer_reviewed',instance.peer_reviewed)
        instance.total_papers_submitted =validated_data.get('total_papers_submitted',instance.total_papers_submitted)
        instance.total_papers_accepted =validated_data.get('total_papers_accepted',instance.total_papers_accepted)
        instance.award =validated_data.get('award',instance.award)
        instance.save()
        return instance


    class Meta:
        model = Publication
        depth = 10
        #many to many: authors, projects, project_umbrellas,
        #one to one:video
        #fk: talk
        #choice fields: pub_venue_type, award
        fields = '__all__'

class TalkSerializer(serializers.ModelSerializer):
    speakers = PersonSerializer(many=True)

    def create(self, validated_data):
        speakers = validated_data.pop('speakers')
        serializer = PersonSerializer(data=speakers, many=True)
        serializer.is_valid()
        serializer.save()

        pdf_file = validated_data.pop('pdf_file')
        pdf_name = pdf_file.name

        pdf = File(open(pdf_name, 'rb'))

        raw_file = validated_data.pop('raw_file')
        if raw_file is not None:
            raw_name = raw_file.name
            raw_file = File(open(raw_name, 'rb'))
        else:
            raw_file = None

        p = Talk.objects.create(pdf_file=pdf, raw_file=raw_file, **validated_data)
        pdf.close()
        if p.raw_file:
            raw_file.close()

        for speaker in speakers:
            person = Person.objects.get(first_name=speaker['first_name'], last_name=speaker['last_name'])
            p.speakers.add(person)

        initial_path = p.pdf_file.path
        p.pdf_file.name = os.path.join('talks', p.pdf_file.name.split('/')[-1])
        new_path = os.path.join(settings.MEDIA_ROOT, p.pdf_file.name)
        shutil.copyfile(initial_path, new_path)

        if p.raw_file.name:
            initial_path_raw = p.raw_file.path
            p.raw_file.name = os.path.join('talks', p.raw_file.name.split('/')[-1])
            new_path = os.path.join(settings.MEDIA_ROOT, p.raw_file.name)
            shutil.copy(initial_path, new_path)

        p.save()
        # for f in glob.glob('./media/temp/*.pdf'):
        #    shutil.move(f, os.path.join('.', 'media', 'publications'))

        return p

    class Meta:
        model = Talk
        #Many to many fields: projects, project_umbralla, keywords, speakers
        fields = '__all__'
        depth = 10


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = '__all__'
        depth = 10

class VideoSerializer(serializers.ModelSerializer):
    project = ProjectSerializer()
    class Meta:
        model = Video
        fields = '__all__'
        depth = 10

class NewsSerializer(serializers.ModelSerializer):
    author = PersonSerializer()
    class Meta:
        model = News
        fields = '__all__'
        depth = 10