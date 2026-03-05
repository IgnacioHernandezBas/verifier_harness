# Checklist TODO: Test transform with empty input after fitting integers.
# Checklist TODO: Test transform with empty input after fitting strings.
# Checklist TODO: Ensure empty array is returned in both cases.
import pytest
from sklearn.preprocessing import LabelEncoder

def test_claim_c1():
    # Test transform with empty input after fitting integers.
    # Given: LabelEncoder is fit with a list of integers [1, 2]
    le_integers = LabelEncoder()
    le_integers.fit([1, 2])
    # When: LabelEncoder.transform is called with an empty list
    transformed_integers = le_integers.transform([])
    # Then: Ensure empty array is returned
    assert transformed_integers.size == 0

    # Test transform with empty input after fitting strings.
    # Given: LabelEncoder is fit with a list of strings ['a', 'b']
    le_strings = LabelEncoder()
    le_strings.fit(['a', 'b'])
    # When: LabelEncoder.transform is called with an empty list
    transformed_strings = le_strings.transform([])
    # Then: Ensure empty array is returned
    assert transformed_strings.size == 0
