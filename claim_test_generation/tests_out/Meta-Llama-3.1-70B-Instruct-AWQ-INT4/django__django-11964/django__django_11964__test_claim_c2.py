import pytest
from django.db import models
from django.db.models import CharField, IntegerField
from django.db.models.enums import TextChoices, IntegerChoices

# Checklist: The test must show that the value returned by the getter of the field is equal to the value property of the enum value
# Checklist: The test must show that the __str__ method of the field value returns the expected string representation
# Checklist: The test must handle edge cases correctly

# Data setup: Create a model instance with a CharField and choices pointing to TextChoices
class Color(TextChoices):
    RED = 'red', 'Red'
    GREEN = 'green', 'Green'

class MyModel(models.Model):
    color = CharField(max_length=10, choices=Color.choices)

# Data setup: Create a model instance with an IntegerField and choices pointing to IntegerChoices
class Size(IntegerChoices):
    SMALL = 1, 'Small'
    MEDIUM = 2, 'Medium'
    LARGE = 3, 'Large'

class MyOtherModel(models.Model):
    size = IntegerField(choices=Size.choices)

def test_claim_c2(capsys):
    # Given: A model instance with a CharField or IntegerField with choices pointing to IntegerChoices or TextChoices
    my_model = MyModel(color=Color.RED)
    my_other_model = MyOtherModel(size=Size.MEDIUM)

    # When: Invoking __str__(...) on the field value
    color_str = str(my_model.color)
    size_str = str(my_other_model.size)

    # Then: The value returned by the getter of the field is equal to the value property of the enum value
    assert my_model.color == Color.RED.value
    assert my_other_model.size == Size.MEDIUM.value

    # Then: The __str__ method of the field value returns the expected string representation
    assert color_str == 'red'
    assert size_str == '2'

    # Edge case: Test with an invalid enum value
    with pytest.raises(ValueError):
        MyModel(color='invalid')

    # Edge case: Test with a non-enum value
    with pytest.raises(ValueError):
        MyOtherModel(size='invalid')

    # Edge case: Test with a field that does not have choices
    class MyThirdModel(models.Model):
        name = CharField(max_length=10)
    my_third_model = MyThirdModel(name='John')
    with pytest.raises(AttributeError):
        my_third_model.name.choices
