# Checklist TODO: LabelEncoder returns an empty array when transforming an empty list.
# Checklist TODO: The returned array has dtype int64.
# Checklist TODO: Test passes with various fitting inputs.
import pytest
from sklearn.preprocessing import LabelEncoder

def test_claim_c2():
    # Given: LabelEncoder is fitted with a list of strings.
    le = LabelEncoder()
    le.fit(["apple", "banana", "apple", "banana", "banana"])
    
    # When: transform is called with an empty list.
    transformed = le.transform([])
    
    # Then: The result of transform is an empty array.
    assert len(transformed) == 0, "The result of transform is not an empty array."
    
    # Then: The dtype of the result is int64.
    assert transformed.dtype == 'int64', "The dtype of the result is not int64."
    
    # Edge case: Transform with an empty list after fitting with a single string.
    le_single = LabelEncoder()
    le_single.fit(["apple"])
    transformed_single = le_single.transform([])
    assert len(transformed_single) == 0, "The result of transform with a single string is not an empty array."
    assert transformed_single.dtype == 'int64', "The dtype of the result with a single string is not int64."
    
    # Edge case: Transform with an empty list after fitting with duplicate strings.
    le_duplicate = LabelEncoder()
    le_duplicate.fit(["apple", "apple", "banana", "banana"])
    transformed_duplicate = le_duplicate.transform([])
    assert len(transformed_duplicate) == 0, "The result of transform with duplicate strings is not an empty array."
    assert transformed_duplicate.dtype == 'int64', "The dtype of the result with duplicate strings is not int64."
