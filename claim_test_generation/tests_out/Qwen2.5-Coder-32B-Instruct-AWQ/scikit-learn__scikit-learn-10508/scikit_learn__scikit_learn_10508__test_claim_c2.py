# Checklist TODO: Test passes without raising TypeError
# Checklist TODO: Transform output is an empty array
# Checklist TODO: Output array dtype matches fitted classes dtype
import pytest
from sklearn.preprocessing import LabelEncoder

def test_claim_c2():
    # Given: A LabelEncoder instance fitted on string labels (e.g., ['a', 'b'])
    le = LabelEncoder()
    le.fit(['a', 'b'])

    # When: calling .transform([]) on the fitted LabelEncoder
    transformed = le.transform([])

    # Then: does not raise a TypeError
    # Assert that no TypeError is raised
    assert isinstance(transformed, np.ndarray)

    # Then: returns an empty numpy array
    # Assert that the returned array is empty
    assert transformed.size == 0

    # Then: returned array dtype matches the dtype of the fitted classes
    # Assert that the dtype of the returned array matches the dtype of the fitted classes
    assert transformed.dtype == le.classes_.dtype
