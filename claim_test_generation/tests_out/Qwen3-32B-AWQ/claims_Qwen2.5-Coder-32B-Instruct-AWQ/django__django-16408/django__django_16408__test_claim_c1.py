# Checklist TODO: Install required dependencies for Django imports
# Checklist TODO: Verify model relationships are properly configured
# Checklist TODO: Confirm select_related returns matching related objects
import pytest
from django.db.models import FilteredRelation
from django.test import TestCase

# Given: PoolStyle with pool__tournament__pool relationship
# When: query with annotate and select_related
# Then: tournaments match

@pytest.mark.django_db
def test_claim_c1():
    # Setup models and data
    class Tournament(models.Model):
        pass

    class Pool(models.Model):
        tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)

    class PoolStyle(models.Model):
        pool = models.ForeignKey(Pool, on_delete=models.CASCADE)

    # Create test data
    tournament = Tournament.objects.create()
    pool = Pool.objects.create(tournament=tournament)
    style = PoolStyle.objects.create(pool=pool)

    # Execute query
    p = list(
        PoolStyle.objects.annotate(
            tournament_pool=FilteredRelation('pool__tournament__pool')
        ).select_related('tournament_pool')
    )

    # Assert
    assert p[0].pool.tournament == p[0].tournament_pool.tournament
