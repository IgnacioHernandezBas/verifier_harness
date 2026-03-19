import pytest
import numpy as np
from sklearn.datasets import make_blobs
from sklearn.mixture import GaussianMixture

def test_claim_c1():
    # Given: Generate synthetic data and model with n_init>1
    X, _ = make_blobs(n_samples=100, n_features=2, centers=3, random_state=42)
    gm = GaussianMixture(n_components=3, n_init=5, random_state=42)
    
    # When: Fit and predict
    y_pred1 = gm.fit_predict(X)
    
    # Then: Check convergence and output equality
    assert gm.converged_
    y_pred2 = gm.predict(X)
    assert np.array_equal(y_pred1, y_pred2)

    # Checklist items as comments
    # Model uses n_init>1
    # fit_predict() and predict() outputs match
    # Test validates post-convergence state
