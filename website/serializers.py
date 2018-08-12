from rest_framework import serializers
from website.models import Person, Publication, Talk, Video, Project, News

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
    class Meta:
        model = Publication
        depth = 10
        #many to many: authors, projects, project_umbrellas,
        #one to one:video
        #fk: talk
        #choice fields: pub_venue_type, award
        fields = '__all__'

class TalkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Talk
        #Many to many fields: projects, project_umbralla, keywords, speakers
        fields = '__all__'
        depth = 10


class PersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Person
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