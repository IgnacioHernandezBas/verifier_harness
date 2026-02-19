# Checklist TODO: Test setup creates correct relationships between models.
# Checklist TODO: get_related_selections returns expected related objects.
# Checklist TODO: setup_joins correctly sets up joins for select_related.
import pytest
from django.db import models
from django.db.models import FilteredRelation

# Create Tournament model with fields: id, name
class Tournament(models.Model):
    name = models.CharField(max_length=100)

# Create Pool model with fields: id, tournament_id (foreign key to Tournament)
class Pool(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)

# Create PoolStyle model with fields: id, pool_id (foreign key to Pool)
class PoolStyle(models.Model):
    pool = models.ForeignKey(Pool, on_delete=models.CASCADE)

def test_claim_c1():
    # Test setup creates correct relationships between models.
    tournament = Tournament.objects.create(name="Test Tournament")
    pool = Pool.objects.create(tournament=tournament)
    pool_style = PoolStyle.objects.create(pool=pool)

    # WHEN: list(PoolStyle.objects.annotate(tournament_pool=FilteredRelation('pool__tournament__pool')).select_related('tournament_pool')) is called
    p = list(
        PoolStyle.objects.annotate(
            tournament_pool=FilteredRelation("pool__tournament__pool"),
        ).select_related("tournament_pool")
    )

    # THEN: The tournament of p[0].pool should be equal to the tournament of p[0].tournament_pool
    assert p[0].pool.tournament == p[0].tournament_pool.tournament

    # Test with no related objects
    pool_style_no_relation = PoolStyle.objects.create(pool=None)
    p_no_relation = list(
        PoolStyle.objects.filter(id=pool_style_no_relation.id).annotate(
            tournament_pool=FilteredRelation("pool__tournament__pool"),
        ).select_related("tournament_pool")
    )
    assert len(p_no_relation) == 1
    assert p_no_relation[0].tournament_pool is None

    # Test with multiple PoolStyle objects
    pool_style2 = PoolStyle.objects.create(pool=pool)
    p_multiple = list(
        PoolStyle.objects.annotate(
            tournament_pool=FilteredRelation("pool__tournament__pool"),
        ).select_related("tournament_pool")
    )
    assert len(p_multiple) == 3
    for ps in p_multiple:
        assert ps.pool.tournament == ps.tournament_pool.tournament

    # Test with null values in relationships
    tournament2 = Tournament.objects.create(name="Test Tournament 2")
    pool2 = Pool.objects.create(tournament=tournament2)
    pool_style_null = PoolStyle.objects.create(pool=pool2)
    pool2.tournament = None
    pool2.save()
    p_null = list(
        PoolStyle.objects.filter(id=pool_style_null.id).annotate(
            tournament_pool=FilteredRelation("pool__tournament__pool"),
        ).select_related("tournament_pool")
    )
    assert len(p_null) == 1
    assert p_null[0].tournament_pool is None
