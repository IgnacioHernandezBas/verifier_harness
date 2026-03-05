# Checklist TODO: Test must create and link PoolStyle and Tournament objects.
# Checklist TODO: Test must use select_related with a multi-level FilteredRelation.
# Checklist TODO: Test must verify the tournament_pool attribute is set correctly.
import pytest
from django.db import models
from django.db.models import FilteredRelation

# Test must create and link PoolStyle and Tournament objects.
class Tournament(models.Model):
    name = models.CharField(max_length=100)

class Pool(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)

class PoolStyle(models.Model):
    pool = models.ForeignKey(Pool, on_delete=models.CASCADE)

@pytest.mark.django_db
def test_claim_c2():
    # Given: A PoolStyle object with a related tournament object
    tournament = Tournament.objects.create(name="Test Tournament")
    pool = Pool.objects.create(tournament=tournament)
    pool_style = PoolStyle.objects.create(pool=pool)

    # When: Calling select_related with a multi-level FilteredRelation
    with pytest.assertNumQueries(2):
        p = list(
            Tournament.objects.filter(id=tournament.id)
            .annotate(
                style=FilteredRelation("pool__another_style"),
            )
            .select_related("style")
        )

    # Then: The tournament_pool attribute should be correctly set
    assert p[0].style.pool.tournament == tournament

    # Test with no related tournament object
    with pytest.assertNumQueries(2):
        p = list(
            Tournament.objects.filter(id=999999)  # Non-existent tournament
            .annotate(
                style=FilteredRelation("pool__another_style"),
            )
            .select_related("style")
        )
    assert not p

    # Test with multiple related tournament objects
    tournament2 = Tournament.objects.create(name="Test Tournament 2")
    pool2 = Pool.objects.create(tournament=tournament2)
    pool_style2 = PoolStyle.objects.create(pool=pool2)

    with pytest.assertNumQueries(2):
        p = list(
            Tournament.objects.filter(id__in=[tournament.id, tournament2.id])
            .annotate(
                style=FilteredRelation("pool__another_style"),
            )
            .select_related("style")
        )
    assert len(p) == 2
    assert p[0].style.pool.tournament == tournament
    assert p[1].style.pool.tournament == tournament2

    # Test with an invalid FilteredRelation
    with pytest.raises(ValueError):
        list(
            Tournament.objects.filter(id=tournament.id)
            .annotate(
                style=FilteredRelation("invalid_relation"),
            )
            .select_related("style")
        )
