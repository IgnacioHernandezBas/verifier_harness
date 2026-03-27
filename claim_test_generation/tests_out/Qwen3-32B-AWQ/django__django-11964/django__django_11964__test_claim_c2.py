# Checklist TODO: Model fields use TextChoices/IntegerChoices for choices
# Checklist TODO: __str__() returns enum value, not label
# Checklist TODO: Test verifies value equality, not implementation details
import pytest
from django.db.models import enums

def test_claim_c2():
    # Define TextChoices and IntegerChoices enums
    class Color(enums.TextChoices):
        RED = 'R', 'Red'
        BLUE = 'B', 'Blue'

    class Number(enums.IntegerChoices):
        ONE = 1, 'One'
        TWO = 2, 'Two'

    # GIVEN: Model fields use TextChoices/IntegerChoices for choices
    # WHEN: Invoking __str__(...) on the field value
    # THEN: The value returned by the getter is equal to the value property of the enum value
    for member in Color:
        # Check that str(enum_member) == enum_member.value
        assert str(member) == member.value
    for member in Number:
        # Check that str(enum_member) == str(enum_member.value)
        assert str(member) == str(member.value)
