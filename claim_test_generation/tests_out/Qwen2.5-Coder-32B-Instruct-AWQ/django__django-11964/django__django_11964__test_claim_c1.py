# Checklist TODO: Test passes with the fixed version
# Checklist TODO: Test fails with the buggy version
# Checklist TODO: Test only verifies public API behavior
import pytest
from django.db import models

# Given: A model with a CharField using TextChoices and an instance created with MyChoice.FIRST_CHOICE
class MyChoice(models.TextChoices):
    FIRST_CHOICE = 'first', 'First Choice'
    SECOND_CHOICE = 'second', 'Second Choice'

class MyModel(models.Model):
    choice_field = models.CharField(max_length=10, choices=MyChoice.choices)

def test_claim_c1():
    # Given
    instance = MyModel(choice_field=MyChoice.FIRST_CHOICE)

    # When: Accessing the field value via model instance attribute
    value = instance.choice_field

    # Then: The value is a string equal to 'first'
    assert value == 'first'

    # And: isinstance returns True for str
    assert isinstance(value, str)

    # Edge case: Accessing the field value before saving the model instance
    # (Already covered in the above steps as we didn't save the instance)

    # Edge case: Accessing the field value after changing it to another choice
    instance.choice_field = MyChoice.SECOND_CHOICE
    value_after_change = instance.choice_field

    # Then: The value is a string equal to 'second'
    assert value_after_change == 'second'

    # And: isinstance returns True for str
    assert isinstance(value_after_change, str)
