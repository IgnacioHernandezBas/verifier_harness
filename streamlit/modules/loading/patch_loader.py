import os
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any

import stat

def on_rm_error(func, path, exc_info):
    """
    Error handler for shutil.rmtree to remove read-only files.
    """
    os.chmod(path, stat.S_IWRITE)  # Make file writable
    func(path)


class PatchApplicationError(Exception):
    """Raised when patch application fails."""
    pass


class PatchLoader:
    """
    Handles cloning repositories and applying SWE-bench patches.
    Works with samples from DatasetLoader.
    """

    def __init__(self, sample: Dict[str, Any], branch: str = "main",
                 repos_root: str | Path | None = "./data/repos_temp"):
        """
        Parameters
        ----------
        sample : dict
            One record from the DatasetLoader (must include 'repo', 'patch', 'base_commit').
        branch : str, optional
            Branch to checkout if base_commit not provided.
        repos_root : str or Path, optional
            Root directory to store cloned repositories. Defaults to 'repos_temp'.
        """
        self.repo_name = sample["repo"]
        self.patch_str = sample["patch"]
        self.base_commit = sample.get("base_commit")
        self.branch = branch
        self.repo_path: Path | None = None

        # Root directory for repos
        self.repos_root: Path | None = Path(repos_root).resolve() if repos_root else None

        # GitHub URL
        self.base_repo_url = f"https://github.com/{self.repo_name}.git"

    # -----------------------------------------------------
    def clone_repository(self) -> Path:
        """Step 1 – Clone base repo and checkout commit."""
        if self.repos_root:
            self.repos_root.mkdir(parents=True, exist_ok=True)
            temp_dir = self.repos_root / self.repo_name.replace("/", "__")
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            temp_dir.mkdir(parents=True, exist_ok=True)
        else:
            temp_dir = Path(tempfile.mkdtemp(prefix=f"{self.repo_name.replace('/', '__')}_"))

        print(f"[+] Cloning {self.repo_name} into {temp_dir} ...")

        subprocess.run(
            ["git", "clone", "--depth", "1", "-b", self.branch,
             self.base_repo_url, str(temp_dir)],
            check=True, capture_output=True,
        )

        if self.base_commit:
            subprocess.run(
                ["git", "fetch", "--depth", "1", "origin", self.base_commit],
                cwd=temp_dir, check=False, capture_output=True,
            )
            subprocess.run(
                ["git", "checkout", self.base_commit],
                cwd=temp_dir, check=True, capture_output=True,
            )

        self.repo_path = temp_dir
        return temp_dir

    # -----------------------------------------------------
    def apply_patch(self) -> Dict[str, Any]:
        """Step 2 – Apply unified diff patch to repo."""
        if not self.repo_path:
            raise RuntimeError("Repository not cloned yet. Call clone_repository() first.")

        patch_path = self.repo_path / "temp.patch"
        patch_path.write_text(self.patch_str)

        try:
            subprocess.run(
                ["git", "apply", "--whitespace=fix", str(patch_path)],
                cwd=self.repo_path, check=True, capture_output=True,
            )
            applied, log = True, "Patch applied successfully."
        except subprocess.CalledProcessError as e:
            applied, log = False, e.stderr.decode(errors="ignore") if e.stderr else str(e)
            raise PatchApplicationError(f"Patch failed: {log}")
        finally:
            patch_path.unlink(missing_ok=True)

        return {"repo_path": str(self.repo_path), "applied": applied, "log": log}

    # -----------------------------------------------------
    def load_and_apply(self) -> Dict[str, Any]:
        """Step 3 – Clone and apply in one call."""
        self.clone_repository()
        return self.apply_patch()
    
    def cleanup_old_repos(self, repos_root: str | Path | None = None) -> None:
        """
        Remove all cloned repositories under the specified root (or self.repos_root if None).
        """
        root = Path(repos_root or self.repos_root or "repos_temp").resolve()

        if not root.exists():
            print(f"⚠️ Cleanup skipped: {root} does not exist.")
            return

        if any(root.parts[-1] in dangerous for dangerous in ["", "C:", "Users", "Desktop", "OneDrive"]):
            # Safety guard against accidental top-level deletion
            raise ValueError(f"Refusing to delete suspicious directory: {root}")

        print(f"Removing all repos in {root}")
        shutil.rmtree(root, onerror=on_rm_error)
