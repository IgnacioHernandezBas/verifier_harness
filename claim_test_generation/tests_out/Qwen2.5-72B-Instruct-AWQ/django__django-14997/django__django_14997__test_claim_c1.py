# Checklist TODO: Define the 'Tag' model with a unique constraint.
# Checklist TODO: Create and apply a migration that alters the 'value' field.
# Checklist TODO: Ensure no OperationalError is raised during the migration.
import pytest
from django.db import models, connection
from django.db.migrations import Migration, operations
from django.db.migrations.state import ProjectState

# Define the 'Tag' model with a unique constraint.
class Tag(models.Model):
    name = models.CharField(max_length=100)
    value = models.CharField(max_length=100)

    class Meta:
        unique_together = ('name', 'value')

# Create and apply a migration that alters the 'value' field.
class TestMigration(Migration):
    dependencies = []

    operations = [
        operations.AlterField(
            model_name='Tag',
            name='value',
            field=models.CharField(max_length=200, null=True),
        ),
    ]

def test_claim_c1():
    # GIVEN: A Django model 'Tag' with a unique constraint on 'name' and 'value' fields.
    # WHEN: Applying the migration that alters the 'value' field of the 'Tag' model.
    project_state = ProjectState()
    project_state.add_model(Tag)
    new_state = project_state.clone()
    migration = TestMigration()
    migration.apply(project_state, new_state)

    # THEN: No OperationalError is raised during the migration.
    with connection.schema_editor() as schema_editor:
        migration.apply(project_state, new_state, schema_editor=schema_editor)
