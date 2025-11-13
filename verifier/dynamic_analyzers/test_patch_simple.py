#!/usr/bin/env python3
"""
Simple standalone test for Podman-based test execution.
This doesn't require the SWE-bench dataset - just tests basic functionality.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path


def build_podman_image(python_version: str = "3.11", timeout: int = 600) -> str:
    """Build or reuse a Podman image for testing."""
    image_name = f"verifier-swebench:python-{python_version}"

    # Check if image already exists
    try:
        check_cmd = ["podman", "image", "exists", image_name]
        result = subprocess.run(check_cmd, capture_output=True, timeout=10)
        if result.returncode == 0:
            print(f"✅ Image {image_name} already exists, skipping build.")
            return image_name
    except Exception as e:
        print(f"⚠️  Warning: could not check for existing image: {e}")

    dockerfile = f"""
    FROM python:{python_version}-slim

    RUN apt-get update \\
        && apt-get install -y --no-install-recommends \\
            git build-essential libssl-dev libffi-dev python3-dev curl \\
        && rm -rf /var/lib/apt/lists/*

    WORKDIR /workspace

    RUN pip install --no-cache-dir --upgrade pip setuptools wheel \\
        && pip install --no-cache-dir pytest pytest-xdist pytest-timeout hypothesis coverage

    CMD ["bash"]
    """.strip() + "\n"

    local_tmpdir = Path("/tmp") / f"podman_build_{os.getpid()}"
    local_tmpdir.mkdir(parents=True, exist_ok=True)

    try:
        dockerfile_path = local_tmpdir / "Dockerfile"
        dockerfile_path.write_text(dockerfile, encoding="utf-8")

        cmd = ["podman", "build", "-t", image_name, str(local_tmpdir)]
        print(f"📦 Building Podman image: {' '.join(cmd)}")

        build_env = os.environ.copy()
        build_env["TMPDIR"] = "/tmp"

        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=build_env)

        if proc.returncode != 0:
            raise RuntimeError(
                f"Failed to build Podman image:\n"
                f"EXIT: {proc.returncode}\n\nSTDOUT:\n{proc.stdout}\n\nSTDERR:\n{proc.stderr}"
            )
        else:
            print(f"✅ Podman image {image_name} built successfully.")

    finally:
        if local_tmpdir.exists():
            shutil.rmtree(local_tmpdir, ignore_errors=True)

    return image_name


def test_basic_functionality():
    """Test basic Podman image building and execution."""
    print("="*80)
    print("Testing basic Podman functionality")
    print("="*80)

    # Test 1: Build image
    print("\n[Test 1] Building Podman image...")
    try:
        image_name = build_podman_image(python_version="3.11", timeout=600)
        print(f"✅ Successfully built image: {image_name}")
    except Exception as e:
        print(f"❌ Failed to build image: {e}")
        return False

    # Test 2: Run simple command in container
    print("\n[Test 2] Testing container execution...")
    try:
        import subprocess
        result = subprocess.run(
            ["podman", "run", "--rm", image_name, "python", "-c", "print('Hello from container')"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and "Hello from container" in result.stdout:
            print(f"✅ Container execution works")
            print(f"   Output: {result.stdout.strip()}")
        else:
            print(f"❌ Container execution failed")
            print(f"   stdout: {result.stdout}")
            print(f"   stderr: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Container test failed: {e}")
        return False

    # Test 3: Check pytest is installed
    print("\n[Test 3] Checking pytest installation...")
    try:
        result = subprocess.run(
            ["podman", "run", "--rm", image_name, "pytest", "--version"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            print(f"✅ Pytest is installed")
            print(f"   {result.stdout.strip()}")
        else:
            print(f"❌ Pytest check failed")
            return False
    except Exception as e:
        print(f"❌ Pytest check failed: {e}")
        return False

    print("\n" + "="*80)
    print("✅ All basic tests passed!")
    print("="*80)
    return True


if __name__ == "__main__":
    success = test_basic_functionality()
    sys.exit(0 if success else 1)
