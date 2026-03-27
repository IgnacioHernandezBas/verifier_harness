# Checklist TODO: Model field returns integer when accessed
# Checklist TODO: Returned integer matches enum member value
# Checklist TODO: No enum instance returned from field access
import pytest
from django.db import models

def test_claim_c2():
    # Define IntegerChoices enum
    class Status(models.IntegerChoices):
        PENDING = 1
        COMPLETED = 2
        CANCELLED = 3

    # Define model with IntegerField using IntegerChoices
    class Task(models.Model):
        state = models.IntegerField(choices=Status)

    # GIVEN: Model instance with enum value
    task = Task(state=Status.COMPLETED)

    # WHEN: Accessing the field value
    result = task.state

    # THEN: Value is integer, not enum instance
    assert isinstance(result, int)  # Check type is int
    assert result == Status.COMPLETED.value  # Check value matches enum's value
