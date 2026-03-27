# Checklist TODO: Model instance returns string value for TextChoices field
# Checklist TODO: No enum instance returned when accessing attribute
# Checklist TODO: Validation passes for both value equality and type check
import pytest
from django.db import models

def test_claim_c1(tmp_path, monkeypatch):
    # Configure minimal Django settings to avoid INSTALLED_APPS error
    settings_path = tmp_path / "settings.py"
    settings_path.write_text(
        "from django.conf import global_settings\n"
        "INSTALLED_APPS = global_settings.INSTALLED_APPS + ['test_app']\n"
    )
    monkeypatch.setenv("DJANGO_SETTINGS_MODULE", "settings")
    
    # Import django and setup after environment is configured
    import django
    django.setup()
    
    # Define model with TextChoices-based CharField
    class MyChoice(models.TextChoices):
        FIRST_CHOICE = 'first', 'First'
    
    class TestModel(models.Model):
        field_name = models.CharField(max_length=20, choices=MyChoice.choices)
        class Meta:
            app_label = 'test_app'
    
    # GIVEN: Model instance with TextChoices value
    instance = TestModel(field_name=MyChoice.FIRST_CHOICE)
    
    # WHEN: Accessing field value
    value = instance.field_name
    
    # THEN: Value is string, not enum instance
    assert value == 'first'  # String value matches expected
    assert isinstance(value, str)  # Type is str
