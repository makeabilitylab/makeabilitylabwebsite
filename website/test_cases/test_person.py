from django.test import TestCase
from website.models import Person, Position


class PersonStarWarsTest(TestCase):
    def setUp(self):
        jkuang = Person.objects.create(first_name="Johnson", last_name="Kuang")
        sbhatt = Person.objects.create(first_name="Shiven", last_name="Bhatt", )
        jkuang.save()
        sbhatt.save()

    def test_StarWars_picture_exists(self):
        p1 = Person.objects.all().get(first_name="Johnson")
        p2 = Person.objects.all().get(first_name="Shiven")
        self.assertNotEqual(p1, None, "The random star wars image retrieval is not working")
        self.assertNotEqual(p2, None, "The random star wars image retrieval is not working")


class PersonPositionTests(TestCase):
    def setUp(self):
        jkuang = Person.objects.create(first_name="Johnson", last_name="Kuang")
        jkuang.save()
        pos = Position

    # def test_position_status(self):


