import pytest
from django.db import models
from django.db.models import FilteredRelation
from django.db.models.sql.compiler import SQLCompiler

# Checklist: Test passes without errors
def test_claim_c1(capsys):
    # Given: A PoolStyle object with a related tournament object
    class PoolStyle(models.Model):
        tournament = models.ForeignKey('Tournament', on_delete=models.CASCADE)

    class Tournament(models.Model):
        pass

    # When: Calling select_related() with a multi-level FilteredRelation
    pool_style = PoolStyle.objects.annotate(
        tournament_pool=FilteredRelation("tournament__pool"),
    ).select_related("tournament_pool", "tournament_pool__tournament")

    # Then: The related object should be correctly set
    assert hasattr(pool_style, 'tournament_pool')
    assert hasattr(pool_style.tournament_pool, 'tournament')

    # Checklist: Related object is correctly set
    assert pool_style.tournament_pool.tournament is not None

    # Checklist: No unexpected output is captured
    captured = capsys.readouterr()
    assert not captured.out
    assert not captured.err

    # Edge case: Empty FilteredRelation
    pool_style_empty = PoolStyle.objects.annotate(
        tournament_pool=FilteredRelation("tournament__pool", lookup="isnull", value=True),
    ).select_related("tournament_pool", "tournament_pool__tournament")
    assert not hasattr(pool_style_empty, 'tournament_pool')

    # Edge case: Invalid FilteredRelation
    with pytest.raises(ValueError):
        PoolStyle.objects.annotate(
            tournament_pool=FilteredRelation("tournament__pool", lookup="invalid"),
        ).select_related("tournament_pool", "tournament_pool__tournament")

    # Edge case: Missing related object
    pool_style_missing = PoolStyle.objects.annotate(
        tournament_pool=FilteredRelation("tournament__pool"),
    ).select_related("tournament_pool", "tournament_pool__tournament")
    assert not hasattr(pool_style_missing, 'tournament_pool')
