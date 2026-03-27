# Checklist TODO: Verify fit_predict and predict return identical labels
# Checklist TODO: Confirm test uses n_init=5 as failure trace indicates
# Checklist TODO: Ensure data generation uses reproducible random state
import pytest
import numpy as np
from sklearn.mixture import GaussianMixture
from sklearn.datasets import make_blobs
from numpy.testing import assert_array_equal

def test_claim_c1():
    # Given: Generate synthetic data with 3 clusters and 100 samples
    X, _ = make_blobs(n_samples=100, centers=3, random_state=42)
    # Given: Initialize GaussianMixture with n_init=5 and random_state=42
    gm = GaussianMixture(n_components=3, n_init=5, random_state=42)
    # When: Fit and predict using fit_predict
    y_pred1 = gm.fit_predict(X)
    # When: Predict using predict on same data
    y_pred2 = gm.predict(X)
    # Then: Verify model has converged
    assert gm.converged_
    # Then: Verify fit_predict and predict outputs are element-wise equal
    assert_array_equal(y_pred1, y_pred2)
