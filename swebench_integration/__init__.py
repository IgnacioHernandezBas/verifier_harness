"""SWE-bench dataset integration modules."""

from .dataset_loader import load_swebench_dataset
from .patch_loader import apply_patch
from .patch_runner import run_patch_evaluation
from .results_aggregator import aggregate_results

__all__ = [
    'load_swebench_dataset',
    'apply_patch',
    'run_patch_evaluation',
    'aggregate_results'
]
