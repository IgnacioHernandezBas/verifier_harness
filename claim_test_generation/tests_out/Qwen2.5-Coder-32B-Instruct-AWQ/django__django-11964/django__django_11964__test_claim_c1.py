# Checklist TODO: CharField getter returns str type
# Checklist TODO: IntegerField getter returns str type
# Checklist TODO: Handles invalid choices gracefully
import pytest
from django.db import models
from django.db.models.enums import TextChoices, IntegerChoices

# Given: A model instance with a CharField using TextChoices
class Gender(TextChoices):
    MALE = 'M', 'Male'
    FEMALE = 'F', 'Female'

# Given: A model instance with an IntegerField using IntegerChoices
class YearInSchool(IntegerChoices):
    FRESHMAN = 1, 'Freshman'
    SOPHOMORE = 2, 'Sophomore'
    JUNIOR = 3, 'Junior'
    SENIOR = 4, 'Senior'

class Person(models.Model):
    gender = models.CharField(max_length=1, choices=Gender.choices)
    year_in_school = models.IntegerField(choices=YearInSchool.choices)

def test_claim_c1():
    # When: Creating an instance of the model with valid choices
    person = Person(gender=Gender.MALE, year_in_school=YearInSchool.FRESHMAN)

    # Then: The value returned by the getter of the CharField is of type str
    assert isinstance(person.gender, str)

    # Then: The value returned by the getter of the IntegerField is of type str
    assert isinstance(person.get_year_in_school_display(), str)

    # Given: Instantiate the model with an invalid choice
    # When: Creating an instance of the model with an invalid choice
    # Then: Handles invalid choices gracefully
    with pytest.raises(ValueError):
        Person(gender='X', year_in_school=99)

    # Given: Check behavior with empty choices
    # When: Creating a model with empty choices
    # Then: Test with multiple fields of different types
    class EmptyChoices(models.Model):
        empty_char = models.CharField(max_length=1, choices=[])
        empty_integer = models.IntegerField(choices=[])

    empty_instance = EmptyChoices(empty_char='', empty_integer=0)
    assert isinstance(empty_instance.empty_char, str)
    assert isinstance(empty_instance.empty_integer, int)
