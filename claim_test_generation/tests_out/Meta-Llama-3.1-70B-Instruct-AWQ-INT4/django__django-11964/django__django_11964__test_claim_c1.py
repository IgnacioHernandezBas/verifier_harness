import pytest
from django.db import models

# Create a model with a CharField using TextChoices
class MyChoice(models.TextChoices):
    FIRST_CHOICE = 'first', 'First Choice'
    SECOND_CHOICE = 'second', 'Second Choice'

class MyModel(models.Model):
    my_field = models.CharField(max_length=10, choices=MyChoice.choices)

# Given: A model with a CharField using TextChoices and an instance created with MyChoice.FIRST_CHOICE
def test_claim_c1(capsys):
    # When: Accessing the field value via model instance attribute
    obj = MyModel(my_field=MyChoice.FIRST_CHOICE)
    
    # Then: The value is a string equal to 'first' and isinstance returns True for str
    assert isinstance(obj.my_field, str)  # isinstance returns True for str
    assert obj.my_field == 'first'  # Accessed field value equals 'first'
    assert isinstance(obj.my_field, str)  # Accessed field value is a string

    # Test passes with the correct field value
    assert obj.my_field == 'first'
    
    # Test fails with an incorrect field value
    with pytest.raises(AssertionError):
        assert obj.my_field == 'second'
    
    # Test does not fail with internal implementation details
    # No need to test internal implementation details, just the public API behavior
