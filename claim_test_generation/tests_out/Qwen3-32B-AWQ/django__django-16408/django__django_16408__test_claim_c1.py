# Checklist TODO: Test verifies multi-level FilteredRelation resolves correctly
# Checklist TODO: Uses select_related on annotated relation
# Checklist TODO: Asserts related object equality without implementation details
import pytest
from django.db import models
from django.db.models import FilteredRelation

def test_claim_c1():
    # Given: Models with cyclic relationships
    class Tournament(models.Model):
        pass

    class Pool(models.Model):
        tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
        another_style = models.ForeignKey('PoolStyle', on_delete=models.CASCADE, related_name='another_pool')

    class PoolStyle(models.Model):
        pool = models.ForeignKey(Pool, on_delete=models.CASCADE)

    # Setup test data
    t1 = Tournament.objects.create()
    p1 = Pool.objects.create(tournament=t1)
    ps1 = PoolStyle.objects.create(pool=p1)
    p1.another_style = ps1
    p1.save()

    # When: Query with FilteredRelation and select_related
    queryset = PoolStyle.objects.annotate(
        tournament_pool=FilteredRelation("pool__tournament__pool")
    ).select_related("tournament_pool", "tournament_pool__tournament")
    p = list(queryset)

    # Then: Assert related object equality
    assert p[0].tournament_pool.tournament == p[0].pool.tournament
