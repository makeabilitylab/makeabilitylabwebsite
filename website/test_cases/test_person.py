from django.test import TestCase
from website.models import Person, Position
from django.utils import timezone

import datetime


class PersonStarWarsTest(TestCase):
    def setUp(self):
        johns = Person.objects.create(first_name="Johnson", last_name="Kuang")
        shiv = Person.objects.create(first_name="Shiven", last_name="Bhatt", )
        johns.save()
        shiv.save()

    def test_StarWars_picture_exists(self):
        johns = Person.objects.all().get(first_name="Johnson")
        shiv = Person.objects.all().get(first_name="Shiven")
        self.assertNotEqual(johns, None, "The random star wars image retrieval is not working")
        self.assertNotEqual(shiv, None, "The random star wars image retrieval is not working")

    def test_get_full_name(self):
        johns = Person.objects.all().get(first_name="Johnson")
        self.assertEqual(johns.get_full_name(), "Johnson Kuang")


class PersonPositionTests(TestCase):
    def setUp(self):
        johns = Person.objects.create(first_name="Johnson", last_name="Kuang")
        johns.save()
        pos = Position.objects.create(person=johns, start_date=timezone.now() + datetime.timedelta(days=30),
                                      end_date=timezone.now(), role="High School Student", title="Prof",
                                      department="computer science information")
        pos.save()

    def test_position_exists(self):
        johns = Person.objects.all().get(first_name="Johnson")
        self.assertNotEqual(johns.get_latest_position(), None, "Position is not defined")

    def test_method_test(self):
        johns = Person.objects.all().get(first_name="Johnson")
        johns_pos = Position.objects.all().get(person=johns)
        self.assertEqual(johns_pos.get_department_abbreviated(), "CS")

    # def test_position_status(self):


