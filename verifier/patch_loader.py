import os
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any


class PatchApplicationError(Exception):
    """Raised when patch application fails."""
    pass


class PatchLoader:
    """
    Handles cloning repositories and applying SWE-bench patches.
    Works with samples from DatasetLoader.
    """

    def __init__(self, sample: Dict[str, Any], branch: str = "main"):
        """
        Parameters
        ----------
        sample : dict
            One record from the DatasetLoader (must include 'repo', 'patch', 'base_commit').
        branch : str, optional
            Branch to checkout if base_commit not provided.
        """
        self.repo_name = sample["repo"]
        self.patch_str = sample["patch"]
        self.base_commit = sample.get("base_commit")
        self.branch = branch
        self.repo_path: Path | None = None

        # GitHub URL pattern (works for public SWE-bench repos)
        self.base_repo_url = f"https://github.com/{self.repo_name}.git"

    # -----------------------------------------------------
    def clone_repository(self) -> Path:
        """
        Step 1: Clone the base repository into a temporary folder.
        Checkout base_commit if provided.
        """
        temp_dir = Path(tempfile.mkdtemp(prefix=f"{self.repo_name.replace('/', '__')}_"))
        print(f"[+] Cloning {self.repo_name} into {temp_dir} ...")

        # Clone
        subprocess.run(
            ["git", "clone", "--depth", "1", "-b", self.branch, self.base_repo_url, str(temp_dir)],
            check=True,
            capture_output=True,
        )

        # Checkout the specified commit if provided
        if self.base_commit:
            subprocess.run(
                ["git", "fetch", "--depth", "1", "origin", self.base_commit],
                cwd=temp_dir,
                check=False,
                capture_output=True,
            )
            subprocess.run(
                ["git", "checkout", self.base_commit],
                cwd=temp_dir,
                check=True,
                capture_output=True,
            )

        self.repo_path = temp_dir
        return temp_dir

    # -----------------------------------------------------
    def apply_patch(self) -> Dict[str, Any]:
        """
        Step 2: Apply the unified diff patch to the cloned repo using git apply.
        """
        if not self.repo_path:
            raise RuntimeError("Repository not cloned yet. Call clone_repository() first.")

        patch_path = self.repo_path / "temp.patch"
        patch_path.write_text(self.patch_str)

        try:
            subprocess.run(
                ["git", "apply", "--whitespace=fix", str(patch_path)],
                cwd=self.repo_path,
                check=True,
                capture_output=True,
            )
            applied = True
            log = "Patch applied successfully."
        except subprocess.CalledProcessError as e:
            applied = False
            log = e.stderr.decode(errors="ignore") if e.stderr else str(e)
            raise PatchApplicationError(f"Patch failed: {log}")
        finally:
            patch_path.unlink(missing_ok=True)

        return {
            "repo_path": str(self.repo_path),
            "applied": applied,
            "log": log,
        }

    # -----------------------------------------------------
    def load_and_apply(self) -> Dict[str, Any]:
        """
        Step 3: Clone and apply in one call.
        """
        self.clone_repository()
        return self.apply_patch()


# -----------------------------------------------------
if __name__ == "__main__":
    # Example: quick test with a SWE-bench-like record
    sample = {
        "repo": "psf/requests",
        "base_commit": None,
        "patch": """diff --git a/README.md b/README.md
index 1111111..2222222 100644
--- a/README.md
+++ b/README.md
@@ -1,3 +1,4 @@
 # Requests
+Patched line example
 """,
    }

    loader = PatchLoader(sample)
    result = loader.load_and_apply()
    print(result)
