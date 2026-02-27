# Checklist TODO: Test correctly sets up related objects.
# Checklist TODO: select_related with FilteredRelation returns expected results.
# Checklist TODO: Handles cases with no or multiple related objects.
import pytest
from django.db import models
from django.db.models import FilteredRelation

# Define models for testing
class Tournament(models.Model):
    name = models.CharField(max_length=100)

class Pool(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)

class PoolStyle(models.Model):
    pool = models.ForeignKey(Pool, on_delete=models.CASCADE)

# Test function
def test_claim_c1():
    # Given: A PoolStyle object with a related tournament object
    tournament = Tournament.objects.create(name="Test Tournament")
    pool = Pool.objects.create(tournament=tournament)
    pool_style = PoolStyle.objects.create(pool=pool)

    # When: Calling select_related with a multi-level FilteredRelation
    p = list(
        PoolStyle.objects.annotate(
            tournament_pool=FilteredRelation("pool__tournament__pool"),
        ).select_related("tournament_pool", "tournament_pool__tournament")
    )

    # Then: The related object should be correctly set
    assert p[0].tournament_pool.tournament == p[0].pool.tournament

    # Test with no related objects
    pool_style_no_relation = PoolStyle.objects.create(pool=None)
    p_no_relation = list(
        PoolStyle.objects.filter(id=pool_style_no_relation.id).annotate(
            tournament_pool=FilteredRelation("pool__tournament__pool"),
        ).select_related("tournament_pool", "tournament_pool__tournament")
    )
    assert len(p_no_relation) == 1
    assert p_no_relation[0].tournament_pool is None

    # Test with multiple related objects
    tournament2 = Tournament.objects.create(name="Test Tournament 2")
    pool2 = Pool.objects.create(tournament=tournament2)
    pool_style2 = PoolStyle.objects.create(pool=pool2)
    p_multiple = list(
        PoolStyle.objects.annotate(
            tournament_pool=FilteredRelation("pool__tournament__pool"),
        ).select_related("tournament_pool", "tournament_pool__tournament")
    )
    assert len(p_multiple) == 3  # 3 PoolStyle objects created
    assert p_multiple[1].tournament_pool.tournament == p_multiple[1].pool.tournament
    assert p_multiple[2].tournament_pool.tournament == p_multiple[2].pool.tournament

    # Test with invalid FilteredRelation parameters
    with pytest.raises(FieldError):
        list(
            PoolStyle.objects.annotate(
                invalid_relation=FilteredRelation("invalid_field"),
            ).select_related("invalid_relation")
        )
