# Checklist TODO: Test must create and apply migrations.
# Checklist TODO: Test must verify no OperationalError is raised.
# Checklist TODO: Test must confirm the unique constraint is applied.
import pytest
from django.db import models, connection
from django.db.migrations.executor import MigrationExecutor
from django.core.management import call_command

# GIVEN: A model with a UniqueConstraint on (name, value) using SQLite backend
class TestModel(models.Model):
    name = models.CharField(max_length=100)
    value = models.CharField(max_length=100)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['name', 'value'], name='unique_name_value')
        ]

# WHEN: Running 'python manage.py migrate' to apply the migrations
def test_claim_c1(tmpdir, monkeypatch, capsys):
    # Create a temporary database file
    db_file = tmpdir.join('test.db')
    monkeypatch.setattr('django.conf.settings.DATABASES', {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': str(db_file),
        }
    })

    # Create the initial migration
    call_command('makemigrations', 'tests', verbosity=0)

    # Apply the initial migration
    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())

    # Alter the field's max_length
    TestModel._meta.get_field('name').max_length = 200
    call_command('makemigrations', 'tests', verbosity=0)

    # Apply the second migration
    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())

    # THEN: No 'sqlite3.OperationalError: the "." operator prohibited in index expressions' exception is raised
    captured = capsys.readouterr()
    assert 'sqlite3.OperationalError: the "." operator prohibited in index expressions' not in captured.err

    # Verify the unique constraint is applied
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA index_list('testmodel')")
        indexes = cursor.fetchall()
        assert any(index[1] == 'unique_name_value' for index in indexes)

    # Verify the table is successfully altered without errors
    with connection.cursor() as cursor:
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='testmodel'")
        table_sql = cursor.fetchone()[0]
        assert 'name VARCHAR(200)' in table_sql
