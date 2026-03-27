# Checklist TODO: Test must create a model instance with a specific choice.
# Checklist TODO: Test must access the field value and check its type.
# Checklist TODO: Test must verify the value matches the expected string.
import pytest
from django.db import models
from django.db.models.enums import TextChoices

# Define a Django model with a CharField using TextChoices
class MyChoice(TextChoices):
    FIRST_CHOICE = 'first', 'First Choice'
    SECOND_CHOICE = 'second', 'Second Choice'

class MyModel(models.Model):
    choice_field = models.CharField(max_length=10, choices=MyChoice.choices)

# Test function
def test_claim_c1():
    # GIVEN: A model with a CharField using TextChoices and an instance created with MyChoice.FIRST_CHOICE
    instance = MyModel(choice_field=MyChoice.FIRST_CHOICE)

    # WHEN: Accessing the field value via model instance attribute
    field_value = instance.choice_field

    # THEN: The value is a string equal to 'first' and isinstance returns True for str
    assert field_value == 'first'
    assert isinstance(field_value, str)
