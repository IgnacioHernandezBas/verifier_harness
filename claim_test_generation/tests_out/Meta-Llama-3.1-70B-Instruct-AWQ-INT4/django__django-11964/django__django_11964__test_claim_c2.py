import pytest
from django.db import models
from django.db.models import CharField, IntegerField
from django.db.models.enums import TextChoices, IntegerChoices

# Given: A model instance with a CharField or IntegerField with choices pointing to IntegerChoices or TextChoices
class MyModel(models.Model):
    class Color(TextChoices):
        RED = 'red', 'Red'
        GREEN = 'green', 'Green'

    class Size(IntegerChoices):
        SMALL = 1, 'Small'
        MEDIUM = 2, 'Medium'
        LARGE = 3, 'Large'

    color = CharField(max_length=10, choices=Color.choices)
    size = IntegerField(choices=Size.choices)

# When: Invoking __str__(...) on the field value
def test_claim_c2(capsys):
    # Test passes with CharField and TextChoices
    obj = MyModel(color='red')
    assert str(obj.color) == 'Red'

    # Test passes with IntegerField and IntegerChoices
    obj = MyModel(size=1)
    assert str(obj.size) == 'Small'

    # Test fails with incorrect field value
    obj = MyModel(color='blue')
    with pytest.raises(ValueError):
        str(obj.color)

    # Test with an empty choices list
    class EmptyChoices(TextChoices):
        pass
    obj = MyModel(color='red')
    obj.color.choices = EmptyChoices.choices
    with pytest.raises(ValueError):
        str(obj.color)

    # Test with a choices list containing only one value
    class SingleChoice(TextChoices):
        RED = 'red', 'Red'
    obj = MyModel(color='red')
    obj.color.choices = SingleChoice.choices
    assert str(obj.color) == 'Red'

    # Test with a field value that is not in the choices list
    obj = MyModel(color='blue')
    with pytest.raises(ValueError):
        str(obj.color)
