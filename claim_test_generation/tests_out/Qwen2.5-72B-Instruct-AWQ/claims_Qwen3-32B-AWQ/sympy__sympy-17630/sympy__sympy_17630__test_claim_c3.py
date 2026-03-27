# Checklist TODO: Test must create a BlockMatrix with ZeroMatrix blocks.
# Checklist TODO: Test must verify the result of _blockmul contains only ZeroMatrix instances.
# Checklist TODO: Test must ensure no scalar Zero instances are present in the result.
import pytest
from sympy.matrices.expressions import MatrixSymbol, ZeroMatrix, BlockMatrix
from sympy.matrices.expressions.blockmatrix import block_collapse

def test_claim_c3(monkeypatch):
    # GIVEN: A BlockMatrix containing ZeroMatrix blocks
    a = MatrixSymbol("a", 2, 2)
    z = ZeroMatrix(2, 2)
    b = BlockMatrix([[a, z], [z, z]])

    # WHEN: Performing b._blockmul(b)
    result = b._blockmul(b)

    # THEN: The resulting BlockMatrix's blocks contain ZeroMatrix instances, not scalar Zero
    assert isinstance(result.blocks[0, 0], MatrixSymbol)  # a**2 is a MatrixSymbol
    assert isinstance(result.blocks[0, 1], ZeroMatrix)  # z
    assert isinstance(result.blocks[1, 0], ZeroMatrix)  # z
    assert isinstance(result.blocks[1, 1], ZeroMatrix)  # z

    # Edge cases
    # Test with a BlockMatrix that contains only ZeroMatrix blocks
    b_only_zeros = BlockMatrix([[z, z], [z, z]])
    result_only_zeros = b_only_zeros._blockmul(b_only_zeros)
    assert all(isinstance(block, ZeroMatrix) for block in result_only_zeros.blocks.flatten())

    # Test with a BlockMatrix that has no ZeroMatrix blocks
    b_no_zeros = BlockMatrix([[a, a], [a, a]])
    result_no_zeros = b_no_zeros._blockmul(b_no_zeros)
    assert all(isinstance(block, MatrixSymbol) for block in result_no_zeros.blocks.flatten())

    # Test with a BlockMatrix of different dimensions
    c = MatrixSymbol("c", 3, 3)
    d = ZeroMatrix(3, 3)
    b_diff_dims = BlockMatrix([[c, d], [d, d]])
    result_diff_dims = b_diff_dims._blockmul(b_diff_dims)
    assert isinstance(result_diff_dims.blocks[0, 0], MatrixSymbol)  # c**2 is a MatrixSymbol
    assert isinstance(result_diff_dims.blocks[0, 1], ZeroMatrix)  # d
    assert isinstance(result_diff_dims.blocks[1, 0], ZeroMatrix)  # d
    assert isinstance(result_diff_dims.blocks[1, 1], ZeroMatrix)  # d

    # Ensure no scalar Zero instances are present in the result
    assert not any(isinstance(block, type(S.Zero)) for block in result.blocks.flatten())
    assert not any(isinstance(block, type(S.Zero)) for block in result_only_zeros.blocks.flatten())
    assert not any(isinstance(block, type(S.Zero)) for block in result_no_zeros.blocks.flatten())
    assert not any(isinstance(block, type(S.Zero)) for block in result_diff_dims.blocks.flatten())

    # BlockMatrix multiplication does not raise exceptions
    assert not pytest.raises(Exception, lambda: b._blockmul(b))
    assert not pytest.raises(Exception, lambda: b_only_zeros._blockmul(b_only_zeros))
    assert not pytest.raises(Exception, lambda: b_no_zeros._blockmul(b_no_zeros))
    assert not pytest.raises(Exception, lambda: b_diff_dims._blockmul(b_diff_dims))
