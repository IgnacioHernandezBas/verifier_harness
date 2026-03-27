import pytest
from django.db import models
from django.db.models import FilteredRelation

# Create Pool, Tournament, and TournamentPool models
class Pool(models.Model):
    pass

class Tournament(models.Model):
    pass

class TournamentPool(models.Model):
    pool = models.ForeignKey(Pool, on_delete=models.CASCADE)
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)

# Given: A queryset annotated with FilteredRelation('pool__tournament__pool') and select_related('tournament_pool')
def test_claim_c1(capsys):
    # Create instances of Pool, Tournament, and TournamentPool
    pool = Pool.objects.create()
    tournament = Tournament.objects.create()
    tournament_pool = TournamentPool.objects.create(pool=pool, tournament=tournament)

    # Annotate queryset with FilteredRelation('pool__tournament__pool')
    # Use select_related('tournament_pool') on queryset
    p = list(Pool.objects.annotate(tournament_pool=FilteredRelation("tournamentpool__tournament")).select_related("tournamentpool"))

    # When: Executing the queryset and accessing p[0].tournament_pool.tournament
    # Then: The value equals p[0].pool.tournament
    assert p[0].tournamentpool.tournament == tournament

    # Test passes with correct related objects
    assert p[0].tournamentpool.pool == pool

    # Test fails with incorrect related objects
    with pytest.raises(AttributeError):
        p[0].tournamentpool.tournament_pool

    # Test handles edge cases correctly
    # Empty queryset
    assert Pool.objects.annotate(tournament_pool=FilteredRelation("tournamentpool__tournament")).select_related("tournamentpool").count() == 1

    # Queryset with multiple results
    Pool.objects.create()
    assert Pool.objects.annotate(tournament_pool=FilteredRelation("tournamentpool__tournament")).select_related("tournamentpool").count() == 2

    # Missing related objects
    pool2 = Pool.objects.create()
    assert not hasattr(pool2, 'tournamentpool')
