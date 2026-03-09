# Checklist TODO: Test passes on the fixed version.
# Checklist TODO: Test fails on the buggy version.
# Checklist TODO: Test only verifies the behavioral claim.
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
def test_claim_c1():
    # Given: Create instances of Tournament, Pool, and PoolStyle
    tournament = Tournament.objects.create(name="Test Tournament")
    pool = Pool.objects.create(tournament=tournament)
    pool_style = PoolStyle.objects.create(pool=pool)

    # When: Annotate and query PoolStyle with select_related to include tournament_pool
    from django.db.models import FilteredRelation
    p = list(
        PoolStyle.objects.annotate(
            tournament_pool=FilteredRelation('pool__tournament__pool'),
        ).select_related('tournament_pool', 'tournament_pool__tournament')
    )

    # Then: The tournament of p[0].pool should be equal to the tournament of p[0].tournament_pool
    assert p[0].tournament_pool.tournament == p[0].pool.tournament
