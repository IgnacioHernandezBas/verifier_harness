# swebench_integration/dataset_loader.py

import json
from pathlib import Path
from typing import Dict, Generator, Optional, List, Union
from datasets import load_dataset

class DatasetLoader:
    """
    Generic dataset loader for code-repair or verification tasks.
    Can load SWE-bench-style JSONs, arbitrary patch datasets, or HuggingFace.
    If it's from HuggingFace (e.g,princeton-nlp/SWE-bench_Lite), it reads the data in memory (streamed from your local Hugging Face cache).
    If it's a local JSON file, it will read it from disk (swbench_integration/data).
    """

    DEFAULT_FIELD_MAP = {
        "repo": "repo",
        "patch": "patch",
        "base_commit": "base_commit",
        "problem_statement": "problem_statement",
    }

    def __init__(
        self,
        source: str,
        split: Optional[str] = None,
        field_map: Optional[Dict[str, str]] = None,
        hf_mode: bool = False,
    ):
        """
        Parameters:
        source: Path to local dataset file or HuggingFace dataset name.
        split: Dataset split (for HuggingFace mode only).
        field_map: Optional mapping of field names (custom dataset schemas).
        hf_mode: Whether to use HuggingFace `load_dataset`.
        """
        self.source = source
        self.split = split
        self.field_map = field_map or self.DEFAULT_FIELD_MAP
        self.hf_mode = hf_mode

        if self.hf_mode:
            self.dataset = load_dataset(self.source, split=self.split or "test")
        else:
            self.dataset_path = Path(self.source)
            if not self.dataset_path.exists():
                raise FileNotFoundError(f"Dataset file not found: {self.dataset_path}")

    def _load_local_json(self) -> List[Dict]:
        with open(self.dataset_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data

    def iter_samples(

        self,
        limit: Optional[int] = None,
        filter_repo: Optional[str] = None,
    ) -> Generator[Dict, None, None]:
        """
        Parameters:
        limit: Optional limit on number of samples to yield.
        filter_repo: Optional substring to filter samples by repository name.

        Objective:
        Reads the dataset,normalizes each entry into a common format, and yields one sample at a time
        {
            'repo': ...,
            'base_commit': ...,
            'patch': ...,
            'problem_statement': ...,
            'metadata': {...}  # all other fields
        }
        """
        if self.hf_mode:
            data_iter = iter(self.dataset)
        else:
            data_iter = iter(self._load_local_json())

        yielded_count = 0
        for raw_sample in data_iter:
            raw_sample = dict(raw_sample)  # Ensure it's a dict (HuggingFace datasets may return DatasetDict)
            if filter_repo and filter_repo not in str(raw_sample.get(self.field_map["repo"], "")):
                continue

            sample = {
                "repo": raw_sample.get(self.field_map["repo"]),
                "base_commit": raw_sample.get(self.field_map.get("base_commit", "base_commit")),
                "patch": raw_sample.get(self.field_map.get("patch", "patch")),
                "problem_statement": raw_sample.get(self.field_map.get("problem_statement", "problem_statement")),
                "metadata": {k: v for k, v in raw_sample.items() if k not in self.field_map.values()},
            }

            yield sample
            yielded_count += 1
            if limit and yielded_count >= limit:
                break

""" 
# Example usage
if __name__ == "__main__":
    # Option 1: Local SWE-bench-style JSON file
    loader = DatasetLoader("data/swebench_sample.json")
    for s in loader.iter_samples(limit=1):
        print(s["repo"], s["metadata"].keys())
        print(s["repo"], s["metadata"].values())

    # Option 2: HuggingFace mode
    # hf_loader = DatasetLoader("princeton-nlp/SWE-bench", hf_mode=True, split="test")
    # for s in hf_loader.iter_samples(limit=1):
    #     print(s["repo"], s["patch"][:80])
"""
if __name__ == "__main__":
    """
    Easy-access command-line interface for quick testing.
    Example command:
    HuggingFace mode -> python swebench_integration/dataset_loader.py --source princeton-nlp/SWE-bench_Lite --huggingface --limit 2 --repo django/django
    Local JSON mode -> python swebench_integration/dataset_loader.py --source swebench_integration/data/swebench_sample.json
    """
    import argparse
    from datasets import load_dataset
    

    parser = argparse.ArgumentParser(description="Interactive DatasetLoader test")

    parser.add_argument(
        "--source",
        type=str,
        default="princeton-nlp/SWE-bench_Lite",
        help="Dataset path or Hugging Face name (e.g., local JSON or HF dataset ID)",
    )
    parser.add_argument(
        "--split",
        type=str,
        default="test",
        help="Dataset split (for Hugging Face mode only)",
    )
    parser.add_argument(
        "--huggingface",
        action="store_true",
        help="Load dataset from Hugging Face Hub instead of local file",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=1,
        help="Number of samples to display",
    )
    parser.add_argument(
        "--repo",
        type=str,
        default=None,
        help="Repository filter (e.g. 'django/django' or 'pandas-dev/pandas')",
    )

    args = parser.parse_args()

    loader = DatasetLoader(
        source=args.source,
        hf_mode=args.huggingface,
        split=args.split,
    )

    print(f"\n Loading dataset from: {args.source}")
    if args.repo:
        print(f" Filtering for repository: {args.repo}")

    for i, s in enumerate(loader.iter_samples(limit=args.limit, filter_repo=args.repo)):
        print(f"\n🔹 Sample {i+1}")
        print(f"Repo: {s['repo']}")
        print(f"Base commit: {s['base_commit']}")
        print(f"Problem: {s['problem_statement'][:200]}...\n")
        print("Patch snippet:\n", s["patch"][:250], "...\n")
        print("Metadata keys:", list(s["metadata"].keys())[:8])