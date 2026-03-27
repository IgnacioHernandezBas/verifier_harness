import pytest
from django.db import models
from django.db.models import IntegerChoices

# Given: A model with an IntegerField using IntegerChoices and an instance created with an enum value
class Color(IntegerChoices):
    RED = 1, 'Red'
    GREEN = 2, 'Green'

class MyModel(models.Model):
    color = models.IntegerField(choices=Color.choices)

def test_claim_c2(capsys):
    # When: Accessing the field value via model instance attribute
    obj = MyModel(color=Color.RED)
    
    # Then: The value is an integer equal to the enum's value
    assert obj.color == Color.RED.value

    # Test with different enum values
    obj.color = Color.GREEN
    assert obj.color == Color.GREEN.value

    # Test with invalid enum values
    with pytest.raises(ValueError):
        obj.color = 3

    # Test with non-enum values
    obj.color = 1
    assert obj.color == 1

# Checklist
# The test creates a model with an IntegerField using IntegerChoices.
# The test creates an instance of the model with an enum value.
# The test verifies that accessing the field value returns the integer value.
