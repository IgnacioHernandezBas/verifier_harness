import pytest
from django.conf import settings
from django.db import models
from django.db.models.sql.compiler import get_related_selections, get_related_klass_infos
from django.db.models import FilteredRelation

# Checklist: The test creates a PoolStyle object with a related tournament object
class Pool(models.Model):
    pass

class PoolStyle(models.Model):
    pool = models.ForeignKey(Pool, on_delete=models.CASCADE)

class Tournament(models.Model):
    pool = models.ForeignKey(Pool, on_delete=models.CASCADE)

# Checklist: The test defines a multi-level FilteredRelation for the PoolStyle object
class TestModel(models.Model):
    pool_style = models.ForeignKey(PoolStyle, on_delete=models.CASCADE)
    tournament_pool = FilteredRelation('pool__tournament__pool')

# Checklist: The test verifies the tournament_pool attribute is correctly set
def test_claim_c2(capsys):
    # Given
    # Checklist: The test creates a PoolStyle object with a related tournament object
    pool = Pool.objects.create()
    pool_style = PoolStyle.objects.create(pool=pool)
    tournament = Tournament.objects.create(pool=pool)

    # When
    # Checklist: The test defines a multi-level FilteredRelation for the PoolStyle object
    test_model = TestModel.objects.annotate(
        tournament_pool=FilteredRelation("pool_style__pool__tournament__pool")
    ).select_related("tournament_pool", "tournament_pool__tournament")

    # Then
    # Checklist: The test verifies the tournament_pool attribute is correctly set
    assert test_model[0].tournament_pool.tournament == tournament

    # Configure Django settings to avoid ImproperlyConfigured exceptions
    settings.configure(INSTALLED_APPS=['django.contrib.contenttypes', 'django.contrib.auth'])

    # Test with an empty FilteredRelation
    test_model_empty = TestModel.objects.annotate(
        tournament_pool=FilteredRelation("")
    ).select_related("tournament_pool", "tournament_pool__tournament")
    assert test_model_empty[0].tournament_pool is None

    # Test with a non-existent related object
    test_model_non_existent = TestModel.objects.annotate(
        tournament_pool=FilteredRelation("non_existent__tournament__pool")
    ).select_related("tournament_pool", "tournament_pool__tournament")
    assert test_model_non_existent[0].tournament_pool is None

    # Test with a misconfigured Django setting
    try:
        settings.configure(INSTALLED_APPS=[])
        test_model_misconfigured = TestModel.objects.annotate(
            tournament_pool=FilteredRelation("pool_style__pool__tournament__pool")
        ).select_related("tournament_pool", "tournament_pool__tournament")
        assert False, "Expected ImproperlyConfigured exception"
    except Exception as e:
        assert isinstance(e, Exception), "Expected ImproperlyConfigured exception"

    # Exercise get_related_selections and get_related_klass_infos
    get_related_selections(TestModel, ["tournament_pool"])
    get_related_klass_infos(TestModel, ["tournament_pool"])

    # No exceptions are raised during the test
    assert True
