# Checklist TODO: Test must create a GaussianMixture instance with n_init=5.
# Checklist TODO: Test must generate a random dataset and fit the model.
# Checklist TODO: Test must compare the outputs of fit_predict and predict.
import pytest
import numpy as np
from sklearn.mixture import GaussianMixture

def test_claim_c1():
    # GIVEN: A GaussianMixture model with n_init>1 and converged fit
    # Create a GaussianMixture instance with n_init=5
    gm = GaussianMixture(n_components=5, n_init=5, random_state=0)
    
    # Generate a random dataset X for testing
    X = np.random.RandomState(0).randn(1000, 5)
    
    # WHEN: Calling fit_predict(X) and subsequently calling predict(X) on the same input data
    y_pred1 = gm.fit_predict(X)
    y_pred2 = gm.predict(X)
    
    # THEN: The output arrays from both methods should be element-wise equal
    assert np.array_equal(y_pred1, y_pred2)
