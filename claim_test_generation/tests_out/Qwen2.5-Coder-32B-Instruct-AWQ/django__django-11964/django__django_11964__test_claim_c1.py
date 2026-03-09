# Checklist TODO: Test passes with CharField and TextChoices
# Checklist TODO: Test passes with IntegerField and IntegerChoices
# Checklist TODO: Test fails with invalid choice value
import pytest
from django.db import models
from django.db.models.enums import TextChoices, IntegerChoices

class Gender(TextChoices):
    MALE = 'M', 'Male'
    FEMALE = 'F', 'Female'

class YearInSchool(IntegerChoices):
    FRESHMAN = 1, 'Freshman'
    SOPHOMORE = 2, 'Sophomore'
    JUNIOR = 3, 'Junior'
    SENIOR = 4, 'Senior'

class Person(models.Model):
    gender = models.CharField(max_length=1, choices=Gender.choices)
    year_in_school = models.IntegerField(choices=YearInSchool.choices)

def test_claim_c1():
    # Given: A model instance with a CharField using TextChoices
    # When: Creating an instance of the model with a valid choice value
    person_char = Person(gender=Gender.MALE)
    # Then: The value returned by the getter of the CharField is of type str
    assert isinstance(person_char.gender, str)

    # Given: A model instance with an IntegerField using IntegerChoices
    # When: Creating an instance of the model with a valid choice value
    person_int = Person(year_in_school=YearInSchool.FRESHMAN)
    # Then: The value returned by the getter of the IntegerField is of type str
    assert isinstance(person_int.year_in_school, str)

    # Given: A model instance with a CharField using TextChoices
    # When: Creating an instance of the model with the minimum value in choices
    person_char_min = Person(gender=Gender.FEMALE)
    # Then: The value returned by the getter of the CharField is of type str
    assert isinstance(person_char_min.gender, str)

    # Given: A model instance with an IntegerField using IntegerChoices
    # When: Creating an instance of the model with the maximum value in choices
    person_int_max = Person(year_in_school=YearInSchool.SENIOR)
    # Then: The value returned by the getter of the IntegerField is of type str
    assert isinstance(person_int_max.year_in_school, str)

    # Given: A model instance with a CharField using TextChoices
    # When: Creating an instance of the model with a non-existent choice value
    # Then: Test fails with invalid choice value
    with pytest.raises(ValueError):
        Person(gender='X')

    # Given: A model instance with an IntegerField using IntegerChoices
    # When: Creating an instance of the model with a non-existent choice value
    # Then: Test fails with invalid choice value
    with pytest.raises(ValueError):
        Person(year_in_school=99)
