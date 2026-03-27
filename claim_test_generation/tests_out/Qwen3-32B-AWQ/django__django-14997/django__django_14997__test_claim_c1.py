# Checklist TODO: Verifies no prohibited operator error occurs
# Checklist TODO: Confirms DDL references are properly relabeled
# Checklist TODO: Validates migration applies without database errors
import pytest
from django.db import models, connection
from django.db.migrations.operations.fields import AlterField
from django.db.models import UniqueConstraint
from django.test.utils import setup_test_model

# Given: Create Tag model with UniqueConstraint(name, value)
# When: Applying migration that alters 'value' field
# Then: No OperationalError raised with prohibited operator message

@pytest.mark.django_db
def test_claim_c1():
    # Setup test model with unique constraint
    class Tag(models.Model):
        name = models.CharField(max_length=100)
        value = models.CharField(max_length=100)
        class Meta:
            constraints = [UniqueConstraint(fields=['name', 'value'], name='tag_name_value_unique')]
    
    setup_test_model(Tag)
    
    # Create migration operation altering 'value' field
    operation = AlterField(
        'Tag',
        'value',
        models.TextField(null=True)  # Changed type and nullability
    )
    
    # Apply migration with schema editor
    with connection.schema_editor() as editor:
        operation.database_forwards('test_app', editor, None, None)
    
    # Verify no OperationalError raised with prohibited operator message
    # (No exception means test passes)
    # Additional assertions about DDL references if needed
    # (But primary verification is absence of specific error)
    pass
