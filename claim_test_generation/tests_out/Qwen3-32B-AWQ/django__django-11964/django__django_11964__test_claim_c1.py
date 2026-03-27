# Checklist TODO: Model field uses TextChoices/IntegerChoices for choices
# Checklist TODO: Field getter returns string value for valid inputs
# Checklist TODO: Test fails if enum type/field type mismatch
import pytest

import importlib
MODULE_PATH = "django.db.models.enums"

def test_claim_c1():
    # GIVEN: A model instance with a CharField or IntegerField with choices pointing to IntegerChoices or TextChoices
    # WHEN: Creating an instance of the model
    # THEN: The value returned by the getter of the field is of type str
    if MODULE_PATH is None:
        pytest.skip('No module path available for this claim.')
    module = importlib.import_module(MODULE_PATH)
    assert hasattr(module, "TextChoices"), "Expected symbol not found"
    # TODO: refine this test manually based on repository context.
