# Checklist TODO: Verify tournament_pool exists post-select_related
# Checklist TODO: Confirm correct tournament object is referenced
# Checklist TODO: Ensure multi-level relation traversal works
import pytest
from django.db import models
from django.db.models import FilteredRelation

# Define test models
class Tournament(models.Model):
    name = models.CharField(max_length=100)

class Pool(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    another_style = models.ForeignKey("PoolStyle", on_delete=models.SET_NULL, null=True)

class PoolStyle(models.Model):
    pool_1 = models.ForeignKey(Pool, on_delete=models.SET_NULL, null=True, related_name="style_1")
    pool_2 = models.ForeignKey(Pool, on_delete=models.SET_NULL, null=True, related_name="style_2")

# Test function
def test_claim_c2():
    # Given: Setup models and relationships
    t1 = Tournament.objects.create(name="Test Tournament")
    p1 = Pool.objects.create(tournament=t1)
    ps1 = PoolStyle.objects.create(pool_1=p1)

    # When: Query with multi-level FilteredRelation and select_related
    p = list(
        PoolStyle.objects.annotate(
            tournament_pool=FilteredRelation("pool_1__tournament__pool"),
        ).select_related("tournament_pool", "tournament_pool__tournament")
    )

    # Then: Verify tournament_pool attribute is correctly set
    result = p[0]
    assert hasattr(result, "tournament_pool")
    assert isinstance(result.tournament_pool, Pool)
    assert result.tournament_pool.tournament_id == t1.id
    assert result.tournament_pool.id == p1.id
