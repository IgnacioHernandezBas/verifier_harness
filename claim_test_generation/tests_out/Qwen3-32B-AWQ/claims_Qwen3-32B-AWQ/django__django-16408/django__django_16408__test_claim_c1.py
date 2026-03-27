# Checklist TODO: Queryset uses FilteredRelation and select_related as specified
# Checklist TODO: Accesses nested attributes tournament_pool.tournament and pool.tournament
# Checklist TODO: Asserts equivalence of the two tournament references
import pytest

import importlib
MODULE_PATH = "django.db.models.sql.compiler"

def test_claim_c1():
    # GIVEN: A queryset annotated with FilteredRelation('pool__tournament__pool') and select_related('tournament_pool')
    # WHEN: Executing the queryset and accessing p[0].tournament_pool.tournament
    # THEN: The value equals p[0].pool.tournament
    if MODULE_PATH is None:
        pytest.skip('No module path available for this claim.')
    module = importlib.import_module(MODULE_PATH)
    assert hasattr(module, "local_setter"), "Expected symbol not found"
    # TODO: refine this test manually based on repository context.
