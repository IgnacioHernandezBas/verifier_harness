# Checklist TODO: Test uses SQLite backend exclusively
# Checklist TODO: Verifies migration completes without prohibited operator error
# Checklist TODO: Captures process output to detect error messages
import pytest
import os
from django.db import models, connection
from django.db.models import UniqueConstraint

def test_claim_c1(tmpdir, monkeypatch, capsys):
    # GIVEN: Configure settings to use SQLite
    settings_path = tmpdir.join("test_settings.py")
    settings_path.write_text(
        """from django.conf.global_settings import *
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}
INSTALLED_APPS = ['test_app']
""",
        encoding="utf-8"
    )
    monkeypatch.setenv("DJANGO_SETTINGS_MODULE", "test_settings")

    # WHEN: Create model with UniqueConstraint and alter field
    class TestModel(models.Model):
        name = models.CharField(max_length=100)
        value = models.CharField(max_length=100)
        class Meta:
            constraints = [UniqueConstraint(fields=["name", "value"], name="test_constraint")]

    # Create initial table with constraints
    with connection.schema_editor() as editor:
        editor.create_model(TestModel)

    # Alter field's max_length (migration-like operation)
    new_field = models.CharField(max_length=200)
    with connection.schema_editor() as editor:
        editor.alter_field(TestModel, TestModel._meta.get_field("name"), new_field, strict=True)

    # THEN: No OperationalError raised
    captured = capsys.readouterr()
    assert "OperationalError" not in captured.out
    assert "the \".\" operator prohibited" not in captured.out
