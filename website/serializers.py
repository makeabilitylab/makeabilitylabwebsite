from rest_framework import serializers
from website.models import Person, Publication, Talk, Video, Project, Project_umbrella

class PersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Person
        fields = ('id','first_name', 'middle_name', 'last_name', 'email', 'personal_website', 'github', 'twitter', 'bio', 'next_position', 'next_position_url', 'image', 'easter_egg')


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        #many to many: sponsors, project_umbrellas, keywords
        fields = ('name', 'short_name', 'sponsors', 'start_date', 'end_date', 'project_umbrellas', 'keywords', 'gallery_image', 'about', 'updated')
        depth = 3

class ProjectUmbrellaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project_umbrella
        #many to many: keywords
        fields = ('name',
                  'short_name',
                  'keywords')
        depth = 2

class PublicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Publication
        #the serializer will automatically scan relations between objects up to a certain depth and pass it to the JSON
        #http://www.django-rest-framework.org/api-guide/serializers/#specifying-nested-serialization
        depth = 5
        #many to many: authors, projects, project_umbrellas,
        #one to one:video
        #fk: talk
        #choice fields: pub_venue_type, award
        fields = ('title',
                  'authors',
                  'pdf_file',
                  'book_title',
                  'book_title_short',
                  'date',
                  'num_pages',
                  'projects',
                  'project_umbrellas',
                  'keywords',
                  'page_num_start',
                  'page_num_end',
                  'official_url',
                  'geo_location',
                  'video',
                  'talk',
                  'series'
                  'isbn',
                  'doi',
                  'publisher'
                  'publisher_address',
                  'acmid',
                  'pub_venue_type',
                  'extended_abstract',
                  'peer_reviewed',
                  'total_papers_submitted',
                  'total_papers_accepted',
                  'award')

class TalkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Talk
        #Many to many fields: projects, project_umbralla, keywords, speakers
        fields = ('title',
                  'projects',
                  'project_umbrellas',
                  'keywords',
                  'forum_name',
                  'forum_url',
                  'location',
                  'speakers',
                  'date',
                  'slideshare_url',
                  'pdf_file',
                  'raw_file',
                  'thumbnail'
        )
        depth = 4

class VideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Video
        fields = ('video_url',
                  'video_preview_url',
                  'title',
                  'caption',
                  'date',
                  'project')
        depth = 3