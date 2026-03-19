# Checklist TODO: Model instance returns string value for TextChoices field
# Checklist TODO: No Django configuration errors during test setup
# Checklist TODO: Test passes in both buggy and fixed versions
import pytest
from django.db import models
from django.db.models.enums import TextChoices

def test_claim_c1(monkeypatch):
    # GIVEN: Set dummy SECRET_KEY to avoid configuration errors
    monkeypatch.setenv("DJANGO_SECRET_KEY", "dummy-key")
    monkeypatch.setattr("django.conf.global_settings.SECRET_KEY", "dummy-key")

    # Define TextChoices enum and model
    class MyChoice(TextChoices):
        FIRST_CHOICE = "first"

    class TestModel(models.Model):
        my_field = models.CharField(max_length=10, choices=MyChoice)

    # WHEN: Create instance with MyChoice.FIRST_CHOICE
    instance = TestModel(my_field=MyChoice.FIRST_CHOICE)

    # THEN: Field value is string 'first' and is instance of str
    assert instance.my_field == "first"
    assert isinstance(instance.my_field, str)
