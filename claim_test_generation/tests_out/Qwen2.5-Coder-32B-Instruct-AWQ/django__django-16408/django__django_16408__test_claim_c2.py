# Checklist TODO: Test setup creates models without errors.
# Checklist TODO: select_related with FilteredRelation sets tournament_pool correctly.
# Checklist TODO: Edge cases handle invalid or missing data gracefully.
import pytest
from django.db import models
from django.db.models import FilteredRelation

# Test setup creates models without errors.
class Tournament(models.Model):
    name = models.CharField(max_length=100)

class PoolStyle(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    style_name = models.CharField(max_length=100)

@pytest.fixture
def setup_data():
    tournament1 = Tournament.objects.create(name="Tournament 1")
    tournament2 = Tournament.objects.create(name="Tournament 2")
    PoolStyle.objects.create(tournament=tournament1, style_name="Style 1")
    PoolStyle.objects.create(tournament=tournament2, style_name="Style 2")
    PoolStyle.objects.create(tournament=tournament1, style_name="Style 3")
    return tournament1, tournament2

def test_claim_c2(setup_data):
    tournament1, tournament2 = setup_data

    # Given: A PoolStyle object with a related tournament object
    # When: Calling select_related() with a multi-level FilteredRelation
    p = list(
        PoolStyle.objects.annotate(
            tournament_pool=FilteredRelation("tournament__poolstyle"),
        ).select_related("tournament_pool", "tournament_pool__tournament")
    )

    # Then: The tournament_pool attribute should be correctly set
    assert p[0].tournament_pool.tournament == p[0].tournament
    assert p[1].tournament_pool.tournament == p[1].tournament
    assert p[2].tournament_pool.tournament == p[2].tournament

    # Edge case: Test with no related objects
    tournament3 = Tournament.objects.create(name="Tournament 3")
    p_no_related = list(
        PoolStyle.objects.filter(tournament=tournament3).annotate(
            tournament_pool=FilteredRelation("tournament__poolstyle"),
        ).select_related("tournament_pool", "tournament_pool__tournament")
    )
    assert len(p_no_related) == 0

    # Edge case: Test with multiple related objects
    p_multiple = list(
        PoolStyle.objects.filter(tournament=tournament1).annotate(
            tournament_pool=FilteredRelation("tournament__poolstyle"),
        ).select_related("tournament_pool", "tournament_pool__tournament")
    )
    assert len(p_multiple) == 2

    # Edge case: Test with invalid FilteredRelation parameters
    with pytest.raises(FieldError):
        list(
            PoolStyle.objects.annotate(
                invalid_relation=FilteredRelation("nonexistent_field"),
            ).select_related("invalid_relation")
        )
