from rest_framework import serializers
from website.models import Person, Publication, Talk, Video, Project, Project_umbrella

class PublicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Publication
        #the serializer will automatically scan relations between objects up to a certain depth and pass it to the JSON
        #http://www.django-rest-framework.org/api-guide/serializers/#specifying-nested-serialization
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