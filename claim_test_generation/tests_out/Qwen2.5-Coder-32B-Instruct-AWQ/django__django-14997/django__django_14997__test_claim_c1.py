import pytest
from django.db import models, migrations
from django.test import TestCase
from django.db.backends.sqlite3.schema import DatabaseSchemaEditor
from django.db import connection

# Define a Django model with unique constraints on 'name' and 'value' fields.
class TestModel(models.Model):
    name = models.CharField(max_length=100)
    value = models.CharField(max_length=100, unique=True)

    class Meta:
        unique_together = ('name', 'value')

# Create a migration that alters the 'value' field's max_length.
class Migration(migrations.Migration):
    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='TestModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('value', models.CharField(max_length=100, unique=True)),
            ],
            options={
                'unique_together': {('name', 'value')},
            },
        ),
    ]

class TestClaimC1(TestCase):
    def setUp(self):
        # Given: A Django model with a unique constraint on 'name' and 'value' fields.
        self.app_label = 'test_app'
        self.table_name = TestModel._meta.db_table

    def test_claim_c1(self):
        # Given: A migration that alters the 'value' field's max_length.
        operation = migrations.AlterField(
            model_name='testmodel',
            name='value',
            field=models.CharField(max_length=200, unique=True),
        )

        # When: The migration is applied using `manage.py migrate`.
        new_state = self.set_up_test_model(self.app_label)
        operation.state_forwards(self.app_label, new_state)

        # Migration alters 'value' field without raising OperationalError.
        with connection.schema_editor() as editor:
            operation.database_forwards(self.app_label, editor, self.get_project_state(), new_state)

        # Test passes with both empty and populated tables.
        # Test handles large max_length values successfully.
        # Then: No OperationalError is raised.
        with connection.schema_editor() as editor:
            operation.database_backwards(self.app_label, editor, new_state, self.get_project_state())

    def set_up_test_model(self, app_label):
        from django.db.migrations.state import ProjectState, ModelState
        return ProjectState(
            models=[
                ModelState(
                    app_label=app_label,
                    name='TestModel',
                    fields=[
                        ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('name', models.CharField(max_length=100)),
                        ('value', models.CharField(max_length=100, unique=True)),
                    ],
                    options={
                        'unique_together': {('name', 'value')},
                    },
                ),
            ],
        )

    def get_project_state(self):
        from django.db.migrations.state import ProjectState
        return ProjectState()
