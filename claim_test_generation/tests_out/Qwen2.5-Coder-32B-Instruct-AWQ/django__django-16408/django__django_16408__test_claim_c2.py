# Checklist TODO: Test passes on the fixed version.
# Checklist TODO: Test fails on the buggy version.
# Checklist TODO: Test only verifies the behavioral property described in the claim.
import pytest
from django.db import models

# Define the models as per the claim context
class Tournament(models.Model):
    name = models.CharField(max_length=100)

class Pool(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)

class PoolStyle(models.Model):
    pool = models.ForeignKey(Pool, on_delete=models.CASCADE)

# Test function to verify the claim
def test_claim_c2():
    # Given: A PoolStyle object with a related tournament object
    tournament = Tournament.objects.create(name="Test Tournament")
    pool = Pool.objects.create(tournament=tournament)
    pool_style = PoolStyle.objects.create(pool=pool)

    # When: Calling select_related() with a multi-level FilteredRelation
    from django.db.models import FilteredRelation
    p = list(
        PoolStyle.objects.annotate(
            tournament_pool=FilteredRelation("pool__tournament__pool"),
        ).select_related("tournament_pool", "tournament_pool__tournament")
    )

    # Then: The tournament_pool attribute should be correctly set
    assert p[0].tournament_pool.tournament == p[0].pool.tournament

    # Edge case: Test with no related tournament object
    pool_style_no_tournament = PoolStyle.objects.create(pool=Pool.objects.create())
    p_no_tournament = list(
        PoolStyle.objects.filter(id=pool_style_no_tournament.id).annotate(
            tournament_pool=FilteredRelation("pool__tournament__pool"),
        ).select_related("tournament_pool", "tournament_pool__tournament")
    )
    assert p_no_tournament[0].tournament_pool is None

    # Edge case: Test with multiple PoolStyle objects related to the same tournament
    pool_style2 = PoolStyle.objects.create(pool=pool)
    p_multiple = list(
        PoolStyle.objects.filter(pool__tournament=tournament).annotate(
            tournament_pool=FilteredRelation("pool__tournament__pool"),
        ).select_related("tournament_pool", "tournament_pool__tournament")
    )
    assert len(p_multiple) == 2
    assert p_multiple[0].tournament_pool.tournament == tournament
    assert p_multiple[1].tournament_pool.tournament == tournament

    # Edge case: Test with a FilteredRelation that does not match any objects
    p_no_match = list(
        PoolStyle.objects.annotate(
            tournament_pool=FilteredRelation("pool__tournament__pool", condition=models.Q(pool__tournament__name="Nonexistent")),
        ).select_related("tournament_pool", "tournament_pool__tournament")
    )
    assert p_no_match[0].tournament_pool is None
