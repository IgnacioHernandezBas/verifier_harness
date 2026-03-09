# Checklist TODO: Test models with TextChoices and IntegerChoices fields.
# Checklist TODO: Verify the field getter returns the correct enum value.
# Checklist TODO: Include edge cases for robustness.
import pytest
from django.db import models
from django.db.models.enums import TextChoices, IntegerChoices

# Define a model with a CharField using TextChoices
class TestModelTextChoices(models.Model):
    class Choices(TextChoices):
        OPTION1 = '1', 'Option 1'
        OPTION2 = '2', 'Option 2'
    
    field = models.CharField(max_length=10, choices=Choices.choices)

# Define a model with an IntegerField using IntegerChoices
class TestModelIntegerChoices(models.Model):
    class Choices(IntegerChoices):
        OPTION1 = 1, 'Option 1'
        OPTION2 = 2, 'Option 2'
    
    field = models.IntegerField(choices=Choices.choices)

# Test models with TextChoices and IntegerChoices fields
def test_claim_c2():
    # GIVEN: A model instance with a CharField using TextChoices
    instance_text = TestModelTextChoices(field=TestModelTextChoices.Choices.OPTION1)
    
    # WHEN: Invoking __str__(...) on the field value
    # THEN: The value returned by the getter of the field is equal to the value property of the enum value
    assert str(instance_text.field) == str(TestModelTextChoices.Choices.OPTION1.value)
    
    # GIVEN: A model instance with an IntegerField using IntegerChoices
    instance_integer = TestModelIntegerChoices(field=TestModelIntegerChoices.Choices.OPTION1)
    
    # WHEN: Invoking __str__(...) on the field value
    # THEN: The value returned by the getter of the field is equal to the value property of the enum value
    assert str(instance_integer.field) == str(TestModelIntegerChoices.Choices.OPTION1.value)
    
    # Include edge cases for robustness
    # Test with a model instance where the field value is not set
    instance_text_unset = TestModelTextChoices()
    assert str(instance_text_unset.field) == ''
    
    instance_integer_unset = TestModelIntegerChoices()
    assert str(instance_integer_unset.field) == ''
    
    # Test with a model instance where the field value is set to an invalid choice
    instance_text_invalid = TestModelTextChoices(field='3')
    assert str(instance_text_invalid.field) == '3'
    
    instance_integer_invalid = TestModelIntegerChoices(field=3)
    assert str(instance_integer_invalid.field) == '3'
    
    # Test with a model instance where the field value is set to a valid choice but the choice is not defined in the enum
    instance_text_undefined = TestModelTextChoices(field='2')
    assert str(instance_text_undefined.field) == '2'
    
    instance_integer_undefined = TestModelIntegerChoices(field=2)
    assert str(instance_integer_undefined.field) == '2'
