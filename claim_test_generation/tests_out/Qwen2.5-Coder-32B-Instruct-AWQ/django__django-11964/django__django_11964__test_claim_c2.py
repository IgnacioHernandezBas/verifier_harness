# Checklist TODO: Model instances correctly use TextChoices and IntegerChoices.
# Checklist TODO: Getter returns correct value for TextChoices.
# Checklist TODO: Getter returns correct value for IntegerChoices.
import pytest
from django.db import models
from django.db.models.enums import TextChoices, IntegerChoices

# Model instances correctly use TextChoices and IntegerChoices.
class Gender(TextChoices):
    MALE = 'M', 'Male'
    FEMALE = 'F', 'Female'

class YearInSchool(IntegerChoices):
    FRESHMAN = 1, 'Freshman'
    SOPHOMORE = 2, 'Sophomore'

class Person(models.Model):
    gender = models.CharField(max_length=1, choices=Gender.choices, default=Gender.MALE)
    year_in_school = models.IntegerField(choices=YearInSchool.choices, default=YearInSchool.FRESHMAN)

def test_claim_c2():
    # Given: A model instance with a CharField pointing to TextChoices.
    person_text = Person(gender=Gender.MALE)
    # When: Invoking __str__(...) on the field value
    # Then: The value returned by the getter of the field is equal to the value property of the enum value for TextChoices.
    assert str(person_text.gender) == str(Gender.MALE.value)

    # Given: A model instance with an IntegerField pointing to IntegerChoices.
    person_integer = Person(year_in_school=YearInSchool.FRESHMAN)
    # When: Invoking __str__(...) on the field value
    # Then: The value returned by the getter of the field is equal to the value property of the enum value for IntegerChoices.
    assert str(person_integer.year_in_school) == str(YearInSchool.FRESHMAN.value)

    # Edge case: Test with an invalid choice value for CharField.
    with pytest.raises(ValueError):
        Person(gender='X')

    # Edge case: Test with an invalid choice value for IntegerField.
    with pytest.raises(ValueError):
        Person(year_in_school=99)

    # Edge case: Test with the default value for both fields.
    person_default = Person()
    assert person_default.gender == Gender.MALE
    assert person_default.year_in_school == YearInSchool.FRESHMAN
