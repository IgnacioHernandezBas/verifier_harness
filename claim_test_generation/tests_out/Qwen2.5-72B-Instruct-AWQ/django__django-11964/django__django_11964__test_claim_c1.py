# Checklist TODO: Test must verify the type of the field value is str.
# Checklist TODO: Test must handle creation of model instances.
# Checklist TODO: Test must cover both TextChoices and IntegerChoices.
import pytest
from django.db import models
from django.db.models.enums import TextChoices, IntegerChoices

# Define a Django model with a CharField using TextChoices
class TestModelTextChoices(models.Model):
    class Choices(TextChoices):
        OPTION1 = '1', 'Option 1'
        OPTION2 = '2', 'Option 2'
    
    field = models.CharField(max_length=10, choices=Choices.choices)

# Define a Django model with an IntegerField using IntegerChoices
class TestModelIntegerChoices(models.Model):
    class Choices(IntegerChoices):
        OPTION1 = 1, 'Option 1'
        OPTION2 = 2, 'Option 2'
    
    field = models.IntegerField(choices=Choices.choices)

# Test the public API behavior of TextChoices and IntegerChoices in Django models.
def test_claim_c1():
    # GIVEN: A model instance with a CharField using TextChoices
    # WHEN: Creating an instance of the model
    instance_text_choices = TestModelTextChoices(field=TestModelTextChoices.Choices.OPTION1)
    # THEN: The value returned by the getter of the field is of type str
    assert isinstance(instance_text_choices.field, str)

    # GIVEN: A model instance with an IntegerField using IntegerChoices
    # WHEN: Creating an instance of the model
    instance_integer_choices = TestModelIntegerChoices(field=TestModelIntegerChoices.Choices.OPTION1)
    # THEN: The value returned by the getter of the field is of type str
    assert isinstance(instance_integer_choices.field, str)

    # GIVEN: A model instance with both CharField and IntegerField using choices
    # WHEN: Creating an instance of the model
    instance_both_choices = TestModelTextChoices(field=TestModelTextChoices.Choices.OPTION1)
    instance_both_choices.field = TestModelIntegerChoices.Choices.OPTION1
    # THEN: The value returned by the getter of the field is of type str
    assert isinstance(instance_both_choices.field, str)
    assert isinstance(instance_both_choices.field, str)

    # Test with a CharField using an invalid choice
    with pytest.raises(ValueError):
        TestModelTextChoices(field='invalid')

    # Test with an IntegerField using an invalid choice
    with pytest.raises(ValueError):
        TestModelIntegerChoices(field=999)

    # Test with a model that has both CharField and IntegerField with choices
    instance_both = TestModelTextChoices(field=TestModelTextChoices.Choices.OPTION1)
    instance_both.field = TestModelIntegerChoices.Choices.OPTION1
    assert isinstance(instance_both.field, str)
    assert isinstance(instance_both.field, str)
