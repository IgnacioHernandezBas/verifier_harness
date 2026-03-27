import pytest
import numpy as np
from sklearn.mixture import GaussianMixture

# Checklist
# Test passes with default parameters
# Test passes with varying n_init values
# Test fails with n_init = 1

def test_claim_c1(capsys):
    # Given: A GaussianMixture model with n_init>1 and converged fit
    # When: Calling fit_predict(X) and随后 calling predict(X) on the same input data
    # Then: The output arrays from both methods should be element-wise equal

    # Data setup
    # Create a GaussianMixture model with n_init > 1
    gm = GaussianMixture(n_components=5, n_init=10, random_state=0)
    
    # Generate random input data X
    X = np.random.RandomState(0).randn(1000, 5)
    
    # Fit the model using fit_predict(X)
    y_pred1 = gm.fit_predict(X)
    
    # Predict cluster labels using predict(X)
    y_pred2 = gm.predict(X)
    
    # Assertions
    # Output arrays from fit_predict and predict are element-wise equal
    assert np.array_equal(y_pred1, y_pred2)
    
    # Edge cases
    # n_init = 1
    gm_single_init = GaussianMixture(n_components=5, n_init=1, random_state=0)
    y_pred_single_init = gm_single_init.fit_predict(X)
    assert not np.array_equal(y_pred1, y_pred_single_init)
    
    # Input data X is empty
    X_empty = np.array([])
    with pytest.raises(ValueError):
        gm.fit_predict(X_empty)
    
    # Model fails to converge
    # This case is not explicitly tested as it is not clear how to force the model to fail convergence.
    # However, the test should pass if the model converges, which is the expected behavior.
