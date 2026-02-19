import pytest
from django.db import models
from django.db.models import CharField, IntegerField
from django.db.models.enums import TextChoices, IntegerChoices

# Given: A model instance with a CharField or IntegerField with choices pointing to IntegerChoices or TextChoices
class Color(TextChoices):
    RED = 'red', 'Red'
    GREEN = 'green', 'Green'

class Size(IntegerChoices):
    SMALL = 1, 'Small'
    MEDIUM = 2, 'Medium'
    LARGE = 3, 'Large'

class MyModel(models.Model):
    color = CharField(max_length=10, choices=Color.choices)
    size = IntegerField(choices=Size.choices)

# When: Creating an instance of the model
def test_claim_c1(capsys):
    # Test passes with valid choice value
    # Checklist: Test passes with valid choice value
    my_model = MyModel(color='red', size=1)
    assert isinstance(my_model.color, str)
    assert my_model.color == 'red'
    assert isinstance(my_model.size, int)
    assert my_model.size == 1

    # Test fails with invalid choice value
    # Checklist: Test fails with invalid choice value
    with pytest.raises(ValueError):
        MyModel(color='blue', size=1)

    # Test fails with missing choice value
    # Checklist: Test fails with missing choice value
    with pytest.raises(ValueError):
        MyModel(color=None, size=1)

    # Edge case: Choice value not set
    my_model = MyModel()
    assert my_model.color is None
    assert my_model.size is None

    # Assertion: The value returned by the getter of the field is of type str
    assert isinstance(my_model.color, (str, type(None)))
    assert isinstance(my_model.size, (int, type(None)))

    # Assertion: The value returned by the getter of the field matches the choice value
    my_model.color = 'red'
    my_model.size = 1
    assert my_model.color == 'red'
    assert my_model.size == 1
