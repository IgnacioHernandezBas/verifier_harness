# Checklist TODO: Test setup creates required models and relationships.
# Checklist TODO: Queryset uses FilteredRelation and select_related as specified.
# Checklist TODO: Result of accessing related objects matches the claim.
import pytest
from django.db import models
from django.test import TestCase

# Test setup creates required models and relationships.
class Tournament(models.Model):
    name = models.CharField(max_length=100)
    pool = models.ForeignKey('self', on_delete=models.CASCADE, null=True, related_name='tournaments')

class Pool(models.Model):
    name = models.CharField(max_length=100)
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='pools')

# Queryset uses FilteredRelation and select_related as specified.
@pytest.mark.django_db
def test_claim_c1():
    # Given: A queryset annotated with FilteredRelation('pool__tournament__pool') and select_related('tournament_pool')
    tournament = Tournament.objects.create(name="T1")
    pool = Pool.objects.create(name="P1", tournament=tournament)
    tournament.pool = pool
    tournament.save()

    # When: Executing the queryset and accessing p[0].tournament_pool.tournament
    p = list(
        Pool.objects.annotate(
            tournament_pool=models.FilteredRelation("pool__tournament__pool"),
        ).select_related("tournament_pool", "tournament_pool__tournament")
    )

    # Then: The value equals p[0].pool.tournament
    assert p[0].tournament_pool.tournament == p[0].tournament

# Edge cases
@pytest.mark.django_db
def test_claim_c1_empty_queryset():
    # Given: An empty queryset
    p = list(
        Pool.objects.annotate(
            tournament_pool=models.FilteredRelation("pool__tournament__pool"),
        ).select_related("tournament_pool", "tournament_pool__tournament")
    )

    # Then: The queryset is empty
    assert len(p) == 0

@pytest.mark.django_db
def test_claim_c1_no_related_objects():
    # Given: No related objects available
    tournament = Tournament.objects.create(name="T1")
    pool = Pool.objects.create(name="P1", tournament=None)

    p = list(
        Pool.objects.annotate(
            tournament_pool=models.FilteredRelation("pool__tournament__pool"),
        ).select_related("tournament_pool", "tournament_pool__tournament")
    )

    # Then: The related object is None
    assert p[0].tournament_pool is None

@pytest.mark.django_db
def test_claim_c1_multiple_levels():
    # Given: Multiple levels of relationships beyond two
    tournament1 = Tournament.objects.create(name="T1")
    pool1 = Pool.objects.create(name="P1", tournament=tournament1)
    tournament2 = Tournament.objects.create(name="T2", pool=pool1)
    pool2 = Pool.objects.create(name="P2", tournament=tournament2)

    p = list(
        Pool.objects.annotate(
            tournament_pool=models.FilteredRelation("pool__tournament__pool"),
        ).select_related("tournament_pool", "tournament_pool__tournament")
    )

    # Then: The value equals p[0].pool.tournament
    assert p[0].tournament_pool.tournament == p[0].tournament
    assert p[1].tournament_pool.tournament == p[1].tournament
