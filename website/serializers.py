from rest_framework import serializers
from website.models import Person, Publication, Talk, Video, Project, Project_umbrella

class PublicationSerializer(serializers.ModelSerializer):

    def create(self, validated_data):
        """
        Create and return a new `Publication` instance, given the validated data
        """
        return Publication.objects.create(**validated_data)

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