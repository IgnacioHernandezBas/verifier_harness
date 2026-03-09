import pytest
from django.db import models

# Given: A model instance with a CharField pointing to TextChoices.
class Gender(models.TextChoices):
    MALE = 'M', 'Male'
    FEMALE = 'F', 'Female'

# Given: A model instance with an IntegerField pointing to IntegerChoices.
class YearInSchool(models.IntegerChoices):
    FRESHMAN = 1, 'Freshman'
    SOPHOMORE = 2, 'Sophomore'
    JUNIOR = 3, 'Junior'
    SENIOR = 4, 'Senior'

class Person(models.Model):
    gender = models.CharField(max_length=1, choices=Gender.choices)
    year_in_school = models.IntegerField(choices=YearInSchool.choices)

def test_claim_c2():
    # Test passes with valid TextChoices.
    # Given
    person = Person(gender=Gender.MALE)
    # When
    gender_str = str(person.gender)
    # Then
    assert gender_str == str(Gender.MALE.value)

    # Test passes with valid IntegerChoices.
    # Given
    person = Person(year_in_school=YearInSchool.FRESHMAN)
    # When
    year_str = str(person.year_in_school)
    # Then
    assert year_str == str(YearInSchool.FRESHMAN.value)

    # Test fails with invalid choice value.
    # Given
    person = Person(gender='X')  # Invalid choice
    # When
    with pytest.raises(ValueError):
        str(person.gender)  # This should raise an error because 'X' is not a valid choice
