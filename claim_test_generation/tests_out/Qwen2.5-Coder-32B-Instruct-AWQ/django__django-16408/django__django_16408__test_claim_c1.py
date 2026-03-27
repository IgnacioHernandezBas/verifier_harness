import pytest
from django.db import models
from django.db.models.functions import FilteredRelation
from django.test import TestCase

# Create a Tournament model with fields id and name
class Tournament(models.Model):
    name = models.CharField(max_length=100)

# Create a Pool model with foreign key to Tournament
class Pool(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)

# Given: A queryset annotated with FilteredRelation('pool__tournament__pool') and select_related('tournament_pool')
# When: Executing the queryset and accessing p[0].tournament_pool.tournament
# Then: The value equals p[0].pool.tournament

@pytest.mark.django_db
def test_claim_c1(tmpdir):
    # Data setup
    t1 = Tournament.objects.create(name="Tournament 1")
    p1 = Pool.objects.create(tournament=t1)
    p2 = Pool.objects.create(tournament=t1)

    # Create a QuerySet with FilteredRelation('pool__tournament__pool') and select_related('tournament_pool')
    queryset = Pool.objects.annotate(
        tournament_pool=FilteredRelation("tournament__pool"),
    ).select_related("tournament_pool", "tournament_pool__tournament")

    # Test passes with expected data setup
    p = list(queryset)
    assert len(p) == 2
    assert p[0].tournament_pool.tournament == p[0].pool.tournament
    assert p[1].tournament_pool.tournament == p[1].pool.tournament

    # Handles cases with no matching records gracefully
    queryset_no_match = Pool.objects.filter(id=-1).annotate(
        tournament_pool=FilteredRelation("tournament__pool"),
    ).select_related("tournament_pool", "tournament_pool__tournament")
    p_no_match = list(queryset_no_match)
    assert len(p_no_match) == 0

    # Correctly sets related objects for multiple pools
    assert p[0].tournament_pool.tournament == t1
    assert p[1].tournament_pool.tournament == t1
