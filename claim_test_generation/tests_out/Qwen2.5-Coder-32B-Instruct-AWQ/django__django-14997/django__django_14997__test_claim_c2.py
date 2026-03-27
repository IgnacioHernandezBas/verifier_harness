# Checklist TODO: Test passes on the fixed version.
# Checklist TODO: Test fails on the buggy version.
# Checklist TODO: Constraint enforces uniqueness as expected.
import pytest
from django.db import models
from django.db.migrations import Migration, operations
from django.db import connection
from django.test import TestCase

# Given: Successful migration application after fixing the bug
# When: Inspecting the database schema using SQLite PRAGMA statements
# Then: The 'unique_name_value' constraint exists and correctly enforces uniqueness on (name, value) columns

class TestUniqueConstraint(TestCase):
    def setUp(self):
        # Create a Django model with a UniqueConstraint on (name, value) fields
        class MyModel(models.Model):
            name = models.CharField(max_length=100)
            value = models.CharField(max_length=100)

            class Meta:
                constraints = [
                    models.UniqueConstraint(fields=['name', 'value'], name='unique_name_value')
                ]

        self.model = MyModel

        # Apply migrations to set up the database schema
        migration = Migration('0001_initial', 'test_app')
        migration.operations = [
            operations.CreateModel(
                name='MyModel',
                fields=[
                    ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                    ('name', models.CharField(max_length=100)),
                    ('value', models.CharField(max_length=100)),
                ],
                options={
                    'constraints': [
                        models.UniqueConstraint(fields=['name', 'value'], name='unique_name_value')
                    ],
                },
            ),
        ]
        with connection.schema_editor() as editor:
            migration.apply(editor, None)

    def tearDown(self):
        # Clean up the database schema
        migration = Migration('0001_initial', 'test_app')
        migration.operations = [
            operations.DeleteModel('MyModel'),
        ]
        with connection.schema_editor() as editor:
            migration.unapply(editor, None)

    def test_claim_c2(self):
        # The 'unique_name_value' constraint exists in the database schema
        cursor = connection.cursor()
        cursor.execute(f"PRAGMA index_list({self.model._meta.db_table})")
        indexes = cursor.fetchall()
        index_names = [index[1] for index in indexes]
        assert 'unique_name_value' in index_names

        # The constraint correctly enforces uniqueness on the (name, value) columns
        # Insert unique (name, value) entries and verify they are accepted
        self.model.objects.create(name='test1', value='value1')
        self.model.objects.create(name='test2', value='value2')

        # Insert duplicate (name, value) entries and verify they are rejected
        with pytest.raises(Exception):
            self.model.objects.create(name='test1', value='value1')
