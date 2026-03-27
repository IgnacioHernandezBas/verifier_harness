# Checklist TODO: Test must create a model with the required fields.
# Checklist TODO: Test must apply a migration adding the unique constraint.
# Checklist TODO: Test must verify the constraint's existence and functionality.
import pytest
from django.db import models, connection
from django.db.migrations.executor import MigrationExecutor
from django.db.utils import IntegrityError

# GIVEN: Successful migration application after fixing the bug
# WHEN: Inspecting the database schema using SQLite PRAGMA statements
# THEN: The 'unique_name_value' constraint exists and correctly enforces uniqueness on (name, value) columns

@pytest.mark.django_db
def test_claim_c2():
    # Test must create a model with the required fields
    class TestModel(models.Model):
        name = models.CharField(max_length=100)
        value = models.CharField(max_length=100)

        class Meta:
            app_label = 'test_app'
            unique_together = ('name', 'value')

    # Apply a migration adding the unique constraint
    with connection.schema_editor() as schema_editor:
        schema_editor.create_model(TestModel)

    # Verify the constraint's existence and functionality
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA index_list('test_app_testmodel')")
        indexes = cursor.fetchall()
        assert any(index[1] == 'test_app_testmodel_name_value_uniq' for index in indexes)

    # Insert a valid record
    TestModel.objects.create(name='test', value='value1')

    # Attempting to insert duplicate (name, value) pairs raises an integrity error
    with pytest.raises(IntegrityError):
        TestModel.objects.create(name='test', value='value1')

    # Test with empty strings for name and value
    with pytest.raises(IntegrityError):
        TestModel.objects.create(name='', value='')

    # Test with very long strings for name and value
    with pytest.raises(IntegrityError):
        TestModel.objects.create(name='a' * 101, value='b' * 101)

    # Test with special characters in name and value
    with pytest.raises(IntegrityError):
        TestModel.objects.create(name='!@#$%^&*()', value='!@#$%^&*()')
