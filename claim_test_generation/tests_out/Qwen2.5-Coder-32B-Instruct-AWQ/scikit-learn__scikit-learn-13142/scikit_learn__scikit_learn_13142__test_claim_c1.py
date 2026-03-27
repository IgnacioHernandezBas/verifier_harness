# Checklist TODO: Test passes with n_init > 1.
# Checklist TODO: Output arrays from fit_predict and predict are equal.
# Checklist TODO: Test handles edge cases gracefully.
import pytest
import numpy as np
from sklearn.mixture import GaussianMixture

def test_claim_c1():
    # Given: A GaussianMixture model with n_init>1 and converged fit
    X = np.random.RandomState(0).randn(1000, 5)
    gm = GaussianMixture(n_components=5, n_init=5, random_state=0)

    # When: Calling fit_predict(X) and随后 calling predict(X) on the same input data
    y_pred1 = gm.fit_predict(X)
    y_pred2 = gm.predict(X)

    # Then: The output arrays from both methods should be element-wise equal
    assert np.array_equal(y_pred1, y_pred2), "fit_predict and predict return the same labels for the same input"

    # Edge case: Test with a very small dataset
    X_small = np.random.RandomState(0).randn(5, 5)
    gm_small = GaussianMixture(n_components=2, n_init=5, random_state=0)
    y_pred1_small = gm_small.fit_predict(X_small)
    y_pred2_small = gm_small.predict(X_small)
    assert np.array_equal(y_pred1_small, y_pred2_small), "fit_predict and predict return the same labels for a small dataset"

    # Edge case: Test with a dataset that has only one feature
    X_one_feature = np.random.RandomState(0).randn(1000, 1)
    gm_one_feature = GaussianMixture(n_components=3, n_init=5, random_state=0)
    y_pred1_one_feature = gm_one_feature.fit_predict(X_one_feature)
    y_pred2_one_feature = gm_one_feature.predict(X_one_feature)
    assert np.array_equal(y_pred1_one_feature, y_pred2_one_feature), "fit_predict and predict return the same labels for a dataset with one feature"

    # Edge case: Test with a dataset that has a large number of samples
    X_large = np.random.RandomState(0).randn(10000, 5)
    gm_large = GaussianMixture(n_components=5, n_init=5, random_state=0)
    y_pred1_large = gm_large.fit_predict(X_large)
    y_pred2_large = gm_large.predict(X_large)
    assert np.array_equal(y_pred1_large, y_pred2_large), "fit_predict and predict return the same labels for a large dataset"
