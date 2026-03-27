# Checklist TODO: Test passes with the fixed version.
# Checklist TODO: Test fails with the buggy version.
# Checklist TODO: Test only verifies the behavioral property described in the claim.
import pytest
from django.db import models

# Define a model with an IntegerField using IntegerChoices.
class Gender(models.IntegerChoices):
    MALE = 1, 'Male'
    FEMALE = 2, 'Female'

class MyModel(models.Model):
    gender = models.IntegerField(choices=Gender.choices)

def test_claim_c2():
    # Given: A model with an IntegerField using IntegerChoices and an instance created with an enum value
    male_instance = MyModel(gender=Gender.MALE)
    female_instance = MyModel(gender=Gender.FEMALE)

    # When: Accessing the field value via model instance attribute before saving
    # Then: The value is an integer equal to the enum's value
    assert isinstance(male_instance.gender, int)
    assert male_instance.gender == Gender.MALE.value
    assert isinstance(female_instance.gender, int)
    assert female_instance.gender == Gender.FEMALE.value

    # When: Accessing the field value via model instance attribute after saving
    male_instance.save()
    female_instance.save()

    # Then: The value is an integer equal to the enum's value
    male_instance.refresh_from_db()
    female_instance.refresh_from_db()
    assert isinstance(male_instance.gender, int)
    assert male_instance.gender == Gender.MALE.value
    assert isinstance(female_instance.gender, int)
    assert female_instance.gender == Gender.FEMALE.value
