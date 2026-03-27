# Checklist TODO: Migration applies without prohibited operator error
# Checklist TODO: Deferred DDL expressions relabeled correctly
# Checklist TODO: Unique constraint integrity preserved post-migration
import pytest
from django.db import models, OperationalError
from django.db.migrations.operations.fields import AlterField
from django.db.migrations.state import ProjectState
from django.db.backends.base.schema import SchemaEditorBase
from django.test.utils import override_settings

@pytest.mark.django_db
def test_claim_c1():
    # GIVEN: Tag model with unique constraint on (name, value)
    class Tag(models.Model):
        name = models.CharField(max_length=100)
        value = models.CharField(max_length=100)
        class Meta:
            constraints = [
                models.UniqueConstraint(fields=['name', 'value'], name='tag_name_value_unique')
            ]
    
    # WHEN: Applying migration altering 'value' field
    project_state = ProjectState.from_model(Tag)
    new_state = project_state.clone()
    operation = AlterField('Tag', 'value', models.TextField())
    operation.state_forwards('Tag', new_state)
    
    with override_settings(DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3'}}):
        with pytest.raises(OperationalError) as exc_info:
            with SchemaEditorBase() as editor:
                operation.database_forwards('Tag', editor, project_state, new_state)
        
        # THEN: No OperationalError with prohibited operator message
        assert "the \".\" operator prohibited in index expressions" not in str(exc_info.value)
        
        # Check unique constraint still exists
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='index' AND name='tag_name_value_unique'
            """)
            assert cursor.fetchone() is not None
