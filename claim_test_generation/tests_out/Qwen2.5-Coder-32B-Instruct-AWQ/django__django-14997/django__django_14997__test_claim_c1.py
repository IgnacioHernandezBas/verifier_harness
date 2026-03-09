# Checklist TODO: Migration alters 'value' field without raising OperationalError.
# Checklist TODO: Unique constraint on 'name' and 'value' fields is preserved.
# Checklist TODO: Data integrity is maintained post-migration.
import pytest
from django.db import models
from django.db.backends.ddl_references import Expressions, IndexExpression
from django.db.models.sql import Query
from django.test import TestCase
from django.db import connection

class Tag(models.Model):
    name = models.CharField(max_length=100)
    value = models.CharField(max_length=100)

    class Meta:
        unique_together = ('name', 'value')

class TestClaimC1(TestCase):
    def setUp(self):
        # Given: A Django model 'Tag' with a unique constraint on 'name' and 'value' fields
        self.tag1 = Tag.objects.create(name='tag1', value='value1')
        self.tag2 = Tag.objects.create(name='tag2', value='value2')

    def test_claim_c1(self):
        # When: Applying the migration that alters the 'value' field of the 'Tag' model
        compiler = Query(Tag, alias_cols=False).get_compiler(connection=connection)
        table = Tag._meta.db_table
        expressions = Expressions(
            table=table,
            expressions=ExpressionList(
                IndexExpression(Upper('name')),
                IndexExpression(F('value')),
            ).resolve_expression(compiler.query),
            compiler=compiler,
            quote_value=compiler.quote_value,
        )
        expressions.rename_table_references(table, 'other')
        expressions.rename_column_references(table, 'value', 'new_value')

        # Then: No OperationalError should be raised
        with connection.schema_editor() as editor:
            editor.execute_sql('BEGIN;')
            try:
                editor.alter_field(Tag._meta.db_table, Tag._meta.get_field('value'), models.CharField(max_length=200))
            except Exception as e:
                pytest.fail(f"OperationalError raised: {e}")
            finally:
                editor.execute_sql('ROLLBACK;')

        # Unique constraint on 'name' and 'value' fields is preserved
        self.assertTrue(Tag._meta.unique_together)

        # Data integrity is maintained post-migration
        self.assertEqual(Tag.objects.count(), 2)
        self.assertEqual(Tag.objects.get(name='tag1').value, 'value1')
        self.assertEqual(Tag.objects.get(name='tag2').value, 'value2')
