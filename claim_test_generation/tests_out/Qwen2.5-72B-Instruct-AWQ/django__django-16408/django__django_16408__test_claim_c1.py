import pytest
from django.db import models
from django.db.models import FilteredRelation

# Create a Tournament model with a related Pool model.
class Tournament(models.Model):
    name = models.CharField(max_length=100)

# Create a Pool model with a related Tournament.
class Pool(models.Model):
    name = models.CharField(max_length=100)
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)

# Create a PoolStyle model with a related Pool model.
class PoolStyle(models.Model):
    name = models.CharField(max_length=100)
    pool = models.ForeignKey(Pool, on_delete=models.CASCADE)

# Test must create necessary models and relationships.
@pytest.fixture
def setup_data():
    tournament = Tournament.objects.create(name="Tournament1")
    pool = Pool.objects.create(name="Pool1", tournament=tournament)
    pool_style = PoolStyle.objects.create(name="Style1", pool=pool)
    return tournament, pool, pool_style

# Test must use select_related and FilteredRelation as described.
def test_claim_c1(setup_data):
    tournament, pool, pool_style = setup_data

    # Annotate PoolStyle with a FilteredRelation to tournament_pool.
    p = list(
        PoolStyle.objects.annotate(
            tournament_pool=FilteredRelation("pool__tournament__pool"),
        ).select_related("tournament_pool")
    )

    # Test must verify the equality of related objects' tournaments.
    assert p[0].tournament_pool.tournament == p[0].pool.tournament
