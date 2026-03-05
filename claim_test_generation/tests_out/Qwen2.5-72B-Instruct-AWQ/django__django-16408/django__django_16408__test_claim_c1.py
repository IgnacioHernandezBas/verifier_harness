import pytest
from django.db import models
from django.db.models import FilteredRelation

# Test must create and use a PoolStyle and Tournament model.
class Tournament(models.Model):
    name = models.CharField(max_length=100)

class Pool(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)

class PoolStyle(models.Model):
    pool = models.ForeignKey(Pool, on_delete=models.CASCADE)
    another_pool = models.ForeignKey(Pool, on_delete=models.CASCADE, related_name='another_style')

# Test must apply a multi-level FilteredRelation.
@pytest.mark.django_db
def test_claim_c1():
    # Create instances of PoolStyle and Tournament with a relationship.
    tournament = Tournament.objects.create(name="Tournament 1")
    pool1 = Pool.objects.create(tournament=tournament)
    pool2 = Pool.objects.create(tournament=tournament)
    pool_style = PoolStyle.objects.create(pool=pool1, another_pool=pool2)

    # Apply a multi-level FilteredRelation to the PoolStyle queryset.
    with pytest.assert_num_queries(2):
        p = list(
            Tournament.objects.filter(id=tournament.id)
            .annotate(
                style=FilteredRelation("pool__another_style"),
            )
            .select_related("style")
        )

    # Test must verify the related object is correctly set.
    assert p[0].style.another_pool == pool2

    # Edge cases
    # Test with no related objects.
    with pytest.assert_num_queries(1):
        p = list(
            Tournament.objects.filter(id=tournament.id)
            .annotate(
                style=FilteredRelation("pool__another_style"),
            )
            .select_related("style")
        )
        assert not p[0].style

    # Test with an invalid FilteredRelation.
    with pytest.raises(models.FieldError):
        list(
            Tournament.objects.filter(id=tournament.id)
            .annotate(
                style=FilteredRelation("invalid_field"),
            )
            .select_related("style")
        )

    # Test with a non-existent related field.
    with pytest.raises(models.FieldError):
        list(
            Tournament.objects.filter(id=tournament.id)
            .annotate(
                style=FilteredRelation("pool__non_existent_field"),
            )
            .select_related("style")
        )
