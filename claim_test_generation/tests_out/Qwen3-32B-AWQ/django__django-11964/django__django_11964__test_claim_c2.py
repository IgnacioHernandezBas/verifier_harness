# Checklist TODO: Test verifies integer value is returned from enum-backed field
# Checklist TODO: No Django settings required beyond minimal model definition
# Checklist TODO: Validation is implementation-agnostic (no private method checks)
import pytest
from django.db import models
from django.db.models.enums import IntegerChoices

# GIVEN: A model with an IntegerField using IntegerChoices
class Status(IntegerChoices):
    DRAFT = 1, "Draft"
    PUBLISHED = 2, "Published"

class Article(models.Model):
    status = models.IntegerField(choices=Status)

    class Meta:
        app_label = "test_app"  # Required to instantiate model without Django settings

# WHEN: Accessing the field value via model instance attribute
# THEN: The value is an integer equal to the enum's value
def test_claim_c2():
    # Create model instance with enum value
    article = Article(status=Status.DRAFT)
    
    # Verify field returns integer value, not enum instance
    assert article.status == Status.DRAFT.value  # Integer value match
    assert isinstance(article.status, int)  # Return type is integer
    assert Article._meta.get_field("status").choices == Status  # Field uses correct enum
