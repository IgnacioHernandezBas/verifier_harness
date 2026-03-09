import pytest
from django.db import models
from django.db.models import TextChoices, IntegerChoices

# Given: A model instance with a CharField or IntegerField with choices pointing to IntegerChoices or TextChoices
class MyModel(models.Model):
    class Color(TextChoices):
        RED = 'red', 'Red'
        GREEN = 'green', 'Green'

    class Size(IntegerChoices):
        SMALL = 1, 'Small'
        MEDIUM = 2, 'Medium'
        LARGE = 3, 'Large'

    color = models.CharField(max_length=10, choices=Color.choices)
    size = models.IntegerField(choices=Size.choices)

# When: Creating an instance of the model
def test_claim_c1():
    # Create a model instance with a CharField and choices pointing to TextChoices
    my_model = MyModel(color='red', size=1)

    # Then: The value returned by the getter of the field is of type str
    # Test passes with valid choice values
    assert isinstance(my_model.color, str)
    assert isinstance(my_model.size, int)

    # Test checks the type of the returned value
    assert my_model.color == 'red'
    assert my_model.size == 1

    # Test fails with invalid choice values
    with pytest.raises(ValueError):
        MyModel(color='invalid', size=1)

    # Test fails with missing choice value
    with pytest.raises(ValueError):
        MyModel(color=None, size=1)

    # Test fails with choice value not set
    with pytest.raises(ValueError):
        MyModel(color='', size=1)
