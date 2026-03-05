import pytest
from django.db import models
from django.db.models.enums import TextChoices, IntegerChoices

# Define a model with CharField and IntegerField using TextChoices and IntegerChoices
class MyTextChoicesModel(models.Model):
    class MyTextChoices(TextChoices):
        OPTION_A = 'A', 'Option A'
        OPTION_B = 'B', 'Option B'

    class MyIntegerChoices(IntegerChoices):
        OPTION_1 = 1, 'Option 1'
        OPTION_2 = 2, 'Option 2'

    text_field = models.CharField(max_length=1, choices=MyTextChoices.choices)
    integer_field = models.IntegerField(choices=MyIntegerChoices.choices)

# Create an instance of the model with specific enum values
@pytest.fixture
def model_instance():
    return MyTextChoicesModel(text_field=MyTextChoices.OPTION_A, integer_field=MyIntegerChoices.OPTION_1)

# Set up the environment to import Django and the model
@pytest.fixture(autouse=True)
def setup_django_environment(monkeypatch):
    monkeypatch.setenv('DJANGO_SETTINGS_MODULE', 'test_settings')

# Test with an empty enum value
@pytest.mark.parametrize('field_name, value', [
    ('text_field', ''),
    ('integer_field', None)
])
def test_empty_enum_value(model_instance, field_name, value):
    setattr(model_instance, field_name, value)
    assert getattr(model_instance, field_name) == value

# Test with a non-existent enum value
@pytest.mark.parametrize('field_name, value', [
    ('text_field', 'C'),
    ('integer_field', 3)
])
def test_non_existent_enum_value(model_instance, field_name, value):
    with pytest.raises(ValueError):
        setattr(model_instance, field_name, value)

# Test with a model field that does not use choices
def test_non_choices_field():
    class NonChoicesModel(models.Model):
        text_field = models.CharField(max_length=1)
        integer_field = models.IntegerField()

    model_instance = NonChoicesModel(text_field='A', integer_field=1)
    assert model_instance.text_field == 'A'
    assert model_instance.integer_field == 1

# Test the main claim
def test_claim_c2(model_instance):
    # Model fields use TextChoices and IntegerChoices.
    assert model_instance.text_field == MyTextChoices.OPTION_A
    assert model_instance.integer_field == MyIntegerChoices.OPTION_1

    # Field values match enum values when accessed.
    assert model_instance.text_field == MyTextChoices.OPTION_A.value
    assert model_instance.integer_field == MyIntegerChoices.OPTION_1.value

    # String representation of field value matches enum value.
    assert str(model_instance.text_field) == str(MyTextChoices.OPTION_A.value)
    assert str(model_instance.integer_field) == str(MyIntegerChoices.OPTION_1.value)

    # Enum value is correctly retrieved from the model instance.
    assert model_instance.text_field == MyTextChoices.OPTION_A
    assert model_instance.integer_field == MyIntegerChoices.OPTION_1

# Tests cover edge cases and negative scenarios.
