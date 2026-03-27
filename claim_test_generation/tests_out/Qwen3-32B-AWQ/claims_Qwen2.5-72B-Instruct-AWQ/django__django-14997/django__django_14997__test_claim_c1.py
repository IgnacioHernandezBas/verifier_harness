# Checklist TODO: Apply migration without raising OperationalError
# Checklist TODO: Use SQLite backend for testing
# Checklist TODO: Verify successful schema alteration with unique constraints
import pytest
import os
import django
from django.db import models
from django.db.migrations.operations.fields import AlterField
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings

def test_claim_c1(tmpdir, monkeypatch):
    # GIVEN: Minimal Django setup with model and migration
    # Create temporary settings module
    settings_path = str(tmpdir.join("test_settings.py"))
    with open(settings_path, "w") as f:
        f.write("""
from pathlib import Path
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}
INSTALLED_APPS = ['testapp']
BASE_DIR = Path(__file__).parent
        """)
    
    # Configure Django settings
    monkeypatch.setitem(os.environ, "DJANGO_SETTINGS_MODULE", "testapp.settings")
    django.setup()

    # Create model with unique constraint
    class TestModel(models.Model):
        name = models.CharField(max_length=100)
        value = models.CharField(max_length=100)
        class Meta:
            constraints = [
                models.UniqueConstraint(fields=['name', 'value'], name='test_unique')
            ]
    
    # WHEN: Applying migration that alters max_length
    try:
        # Create migration operation
        operation = AlterField(
            'testapp_testmodel',
            'value',
            models.CharField(max_length=200)
        )
        
        # Apply migration using schema editor
        with connection.schema_editor() as editor:
            operation.database_forwards('testapp', editor, ProjectState(), new_state)
            
        # THEN: No OperationalError is raised
        # Success is indicated by no exception being raised
        assert True
        
    except Exception as e:
        # Fail if any unexpected exception occurs
        pytest.fail(f"Unexpected exception: {str(e)}")
