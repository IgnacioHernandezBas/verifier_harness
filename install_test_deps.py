#!/usr/bin/env python3
"""
Install test dependencies in Singularity container using --writable-tmpfs
This allows installing pytest, hypothesis, etc. without modifying the base container.
"""

import subprocess
from pathlib import Path

def install_test_dependencies(container_path: str, repo_path: Path) -> dict:
    """
    Install pytest, hypothesis, and other test dependencies in container.
    
    Uses --writable-tmpfs to create a temporary writable overlay.
    Packages are installed to a bind-mounted directory that persists.
    
    Args:
        container_path: Path to .sif container
        repo_path: Path to repository on host
        
    Returns:
        dict with installation results
    """
    
    # Create persistent pip install directory
    pip_base = Path("/fs/nexus-scratch/ihbas/.local/pip_packages")
    pip_base.mkdir(parents=True, exist_ok=True)
    
    # Install test dependencies
    install_cmd = [
        "singularity", "exec",
        "--writable-tmpfs",  # Allow writes to container filesystem
        "--bind", f"{repo_path}:/workspace",
        "--bind", f"{pip_base}:/pip_install_base",
        "--pwd", "/workspace",
        "--env", "PYTHONUSERBASE=/pip_install_base",
        container_path,
        "pip", "install", "--user", 
        "pytest>=6.0",
        "hypothesis>=6.0", 
        "coverage>=5.0",
        "pytest-cov>=2.0"
    ]
    
    print("Installing test dependencies (pytest, hypothesis, coverage)...")
    print(f"  Container: {container_path}")
    print(f"  Install location: {pip_base}")
    
    result = subprocess.run(
        install_cmd,
        capture_output=True,
        text=True,
        timeout=300  # 5 minutes
    )
    
    return {
        "success": result.returncode == 0,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "pip_base": str(pip_base)
    }

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: install_test_deps.py <container_path> <repo_path>")
        sys.exit(1)
    
    result = install_test_dependencies(sys.argv[1], Path(sys.argv[2]))
    
    if result["success"]:
        print("\n✓ Test dependencies installed successfully!")
        print(f"  Location: {result['pip_base']}")
    else:
        print("\n✗ Installation failed!")
        print(result["stderr"])
        sys.exit(1)
