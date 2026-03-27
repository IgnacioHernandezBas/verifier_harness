# Checklist TODO: Test passes with empty input after fitting on strings.
# Checklist TODO: Dtype of result matches dtype of classes_ attribute.
# Checklist TODO: Test handles different data types consistently.
import pytest
import numpy as np
from sklearn.preprocessing import LabelEncoder

def test_claim_c1():
    # Create a LabelEncoder instance.
    le = LabelEncoder()
    
    # Fit the LabelEncoder on a list of string labels, e.g., ['a', 'b'].
    le.fit(['a', 'b'])
    
    # Given: A LabelEncoder instance fitted on string labels (e.g., ['a', 'b'])
    # When: calling .transform([]) on the fitted LabelEncoder
    transformed = le.transform([])
    
    # Then: Returns an empty NumPy array.
    assert len(transformed) == 0
    assert transformed.shape == (0,)
    
    # Then: The dtype of the returned array matches the dtype of the classes_ attribute.
    assert transformed.dtype == le.classes_.dtype
    
    # Test with different data types during fit (e.g., integers).
    le.fit([1, 2])
    transformed = le.transform([])
    assert len(transformed) == 0
    assert transformed.shape == (0,)
    assert transformed.dtype == le.classes_.dtype
    
    # Ensure consistency across multiple fits with different label sets.
    le.fit(['x', 'y', 'z'])
    transformed = le.transform([])
    assert len(transformed) == 0
    assert transformed.shape == (0,)
    assert transformed.dtype == le.classes_.dtype
