# Checklist TODO: Verifies related object is accessible after select_related()
# Checklist TODO: Tests multi-level FilteredRelation resolves correctly
# Checklist TODO: Confirms no additional queries for related object access
import pytest
from django.db import models
from django.db.models import FilteredRelation
from django.test import TestCase

# Given: A PoolStyle object with a related tournament object
# When: Calling select_related() with a multi-level FilteredRelation
# Then: The related object should be correctly set

@pytest.mark.django_db
def test_claim_c1():
    # Setup models
    class Tournament(models.Model):
        name = models.CharField(max_length=100)

    class Pool(models.Model):
        tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
        another_style = models.ForeignKey("PoolStyle", on_delete=models.SET_NULL, null=True)

    class PoolStyle(models.Model):
        pass

    # Create test data
    t = Tournament.objects.create(name="Test Tournament")
    p1 = Pool.objects.create(tournament=t)
    p2 = Pool.objects.create(tournament=t, another_style=PoolStyle.objects.create())
    t.pool_set.add(p1, p2)

    # Apply select_related() with multi-level FilteredRelation
    with TestCase().assertNumQueries(2):
        results = PoolStyle.objects.annotate(
            tournament_pool=FilteredRelation("pool__tournament__pool"),
        ).select_related("tournament_pool", "tournament_pool__tournament")

    # Assert related object is correctly set
    obj = results[0]
    assert isinstance(obj.tournament_pool, Pool)
    assert obj.tournament_pool.tournament_id == t.id
    assert obj.tournament_pool.tournament.name == "Test Tournament"
