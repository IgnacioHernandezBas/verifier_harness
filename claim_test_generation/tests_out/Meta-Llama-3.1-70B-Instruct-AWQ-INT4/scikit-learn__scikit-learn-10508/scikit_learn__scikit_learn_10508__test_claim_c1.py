import pytest
from sklearn.preprocessing import LabelEncoder
import numpy as np

def test_claim_c1(capsys):
    # Given: LabelEncoder is fit with a list of integers or strings
    # When: LabelEncoder.transform is called with an empty list
    # Then: returns empty outputs (empty sequences OR arrays with size==0)

    # Test passes with integer inputs
    le_int = LabelEncoder()
    le_int.fit([1, 2, 1, 2, 2])
    empty_list = []
    transformed_int = le_int.transform(empty_list)
    assert len(transformed_int) == 0

    # Test passes with string inputs
    le_str = LabelEncoder()
    le_str.fit(["1", "2", "1", "2", "2"])
    transformed_str = le_str.transform(empty_list)
    assert len(transformed_str) == 0

    # No TypeError is raised during transformation
    with pytest.raises(TypeError):
        le_int.transform(None)
    with pytest.raises(TypeError):
        le_int.transform("not a list")
    with pytest.raises(TypeError):
        le_int.transform([1, 2, [3, 4]])
