# Checklist TODO: Test shows migration succeeds in SQLite
# Checklist TODO: No implementation-specific exception checks
# Checklist TODO: Verifies core behavior from claim text
import pytest
import sys
import os
from django.core.management import call_command
from django.db import connections
from django.conf import settings

def test_claim_c1(tmp_path, monkeypatch):
    # GIVEN: Temporary test app with model and migration
    test_dir = tmp_path / "test_app"
    test_dir.mkdir()
    
    # Setup Django settings for test
    settings_module = f"tests.settings_{os.getpid()}"
    monkeypatch.setitem(os.environ, "DJANGO_SETTINGS_MODULE", settings_module)
    
    # Create minimal Django settings
    settings_file = test_dir / "settings.py"
    settings_file.write_text("""
from pathlib import Path
import django
BASE_DIR = Path(__file__).parent
SECRET_KEY = 'test'
INSTALLED_APPS = ['test_app']
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
""")
    
    # Create model with unique constraint
    models_file = test_dir / "models.py"
    models_file.write_text("""
from django.db import models
class TestModel(models.Model):
    name = models.CharField(max_length=100)
    value = models.CharField(max_length=100)
    class Meta:
        unique_together = [['name', 'value']]
""")
    
    # Create initial migration
    initial_migration = test_dir / "test_app" / "migrations" / "0001_initial.py"
    initial_migration.parent.mkdir(parents=True, exist_ok=True)
    initial_migration.write_text("""
from django.db import migrations, models
class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name='TestModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('value', models.CharField(max_length=100)),
            ],
        ),
        migrations.AddConstraint(
            model_name='testmodel',
            constraint=models.UniqueConstraint(fields=['name', 'value'], name='unique_name_value'),
        ),
    ]
""")
    
    # Create alter migration
    alter_migration = test_dir / "test_app" / "migrations" / "0002_alter_value.py"
    alter_migration.write_text("""
from django.db import migrations, models
class Migration(migrations.Migration):
    dependencies = [('test_app', '0001_initial')]
    operations = [
        migrations.AlterField(
            model_name='testmodel',
            name='value',
            field=models.CharField(max_length=255),
        ),
    ]
""")
    
    # WHEN: Apply migrations
    try:
        # First create the test app in Django's app registry
        sys.path.append(str(test_dir))
        import test_app
        del sys.path[-1]
        
        # Apply migrations
        call_command('migrate', run_syncdb=True)
        
    except Exception as e:
        # THEN: No OperationalError is raised
        pytest.fail(f"Migration failed with exception: {str(e)}")
    
    # THEN: Verify database connection remains valid
    default_connection = connections['default']
    assert default_connection.is_usable()
    
    # THEN: Verify unique constraint still exists
    with default_connection.cursor() as cursor:
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type = 'index' AND name = 'unique_name_value'
        """)
        assert cursor.fetchone() is not None
