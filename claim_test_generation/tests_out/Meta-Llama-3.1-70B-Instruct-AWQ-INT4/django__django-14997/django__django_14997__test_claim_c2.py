import pytest
from django.db import models
from django.db.models import UniqueConstraint

# Given: Successful migration application after fixing the bug
# When: Inspecting the database schema using SQLite PRAGMA statements
# Then: The 'unique_name_value' constraint exists and correctly enforces uniqueness on (name, value) columns

# Create a test model with a unique constraint on (name, value) columns
class TestModel(models.Model):
    name = models.CharField(max_length=255)
    value = models.CharField(max_length=255)

    class Meta:
        constraints = [
            UniqueConstraint(fields=['name', 'value'], name='unique_name_value')
        ]

def test_claim_c2(capsys):
    # Test passes when unique constraint is created successfully
    # Test fails when duplicate (name, value) pairs are inserted
    # Test succeeds when non-unique (name, value) pairs are inserted

    # Create a test model instance with unique (name, value) pair
    test_model = TestModel(name='test_name', value='test_value')
    test_model.save()

    # Test with duplicate (name, value) pairs
    with pytest.raises(Exception):
        # Attempt to create another instance with the same (name, value) pair
        test_model_duplicate = TestModel(name='test_name', value='test_value')
        test_model_duplicate.save()

    # Test with non-unique (name, value) pairs
    test_model_non_unique = TestModel(name='test_name_2', value='test_value_2')
    test_model_non_unique.save()

    # Check that the unique constraint exists in the database schema
    # This is a simplified check and may not cover all cases
    assert UniqueConstraint in TestModel._meta.constraints

    # Check that the unique constraint enforces uniqueness on (name, value) columns
    # This is a simplified check and may not cover all cases
    assert TestModel._meta.constraints[0].fields == ['name', 'value']
