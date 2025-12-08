#!/bin/bash
# Fuzzing Environment Setup Script
# This script sets up the complete fuzzing environment for SWE-bench verification

set -e  # Exit on error

echo "========================================"
echo "SWE-bench Fuzzing Environment Setup"
echo "========================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Step 1: Check Python version
echo "Step 1: Checking Python version..."
PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 9 ]; then
    print_success "Python $PYTHON_VERSION found (requires 3.9+)"
else
    print_error "Python 3.9+ required, found $PYTHON_VERSION"
    exit 1
fi

# Step 2: Check if running on cluster or local
echo ""
echo "Step 2: Detecting environment..."
if command -v singularity &> /dev/null; then
    CONTAINER_RUNTIME="singularity"
    print_success "Singularity detected (HPC cluster mode)"
elif command -v podman &> /dev/null; then
    CONTAINER_RUNTIME="podman"
    print_info "Podman detected (alternative mode - Singularity recommended)"
elif command -v docker &> /dev/null; then
    CONTAINER_RUNTIME="docker"
    print_info "Docker detected (local development mode)"
else
    print_error "No container runtime found. Please install Singularity, Podman, or Docker"
    exit 1
fi

# Step 3: Check conda environment
echo ""
echo "Step 3: Checking conda environment..."
if command -v conda &> /dev/null; then
    print_success "Conda found"

    # Check if environment exists
    if conda env list | grep -q "verifier_env"; then
        print_info "verifier_env already exists"
        read -p "Recreate environment? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            conda env remove -n verifier_env -y
            conda env create -f environment_linux.yml
            print_success "Environment recreated"
        fi
    else
        print_info "Creating verifier_env from environment_linux.yml..."
        conda env create -f environment_linux.yml
        print_success "Environment created"
    fi
else
    print_info "Conda not found, using pip..."
    if [ ! -d "venv" ]; then
        python -m venv venv
        print_success "Virtual environment created"
    fi
    source venv/bin/activate
    pip install -r requirements.txt
    print_success "Dependencies installed via pip"
fi

# Step 4: Build Singularity container (if using Singularity)
echo ""
echo "Step 4: Setting up container..."
if [ "$CONTAINER_RUNTIME" == "singularity" ]; then
    # Check if container already exists
    CONTAINER_PATH="${SCRATCH0:-$HOME}/.containers/singularity/verifier-swebench.sif"

    if [ -f "$CONTAINER_PATH" ]; then
        print_info "Container already exists at $CONTAINER_PATH"
        read -p "Rebuild container? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_info "Building Singularity container (this may take 5-10 minutes)..."
            python test_singularity_build.py
            print_success "Container rebuilt"
        fi
    else
        print_info "Building Singularity container (this may take 5-10 minutes)..."
        python test_singularity_build.py
        print_success "Container built at $CONTAINER_PATH"
    fi
else
    print_info "Skipping Singularity container build (using $CONTAINER_RUNTIME)"
fi

# Step 5: Verify installation
echo ""
echo "Step 5: Verifying installation..."

# Check if key Python modules are importable
python -c "
import sys
try:
    from verifier.static_analyzers import code_quality, syntax_structure
    from verifier.dynamic_analyzers import patch_analyzer, test_patch_singularity
    from swebench_integration import DatasetLoader, PatchLoader
    print('✓ Core modules importable')
except ImportError as e:
    print(f'✗ Import error: {e}')
    sys.exit(1)
"

if [ $? -eq 0 ]; then
    print_success "All core modules verified"
else
    print_error "Module import failed"
    exit 1
fi

# Step 6: Test basic functionality
echo ""
echo "Step 6: Running basic tests..."
if [ -f "test_fuzzing_pipeline.py" ]; then
    print_info "Running fuzzing pipeline test..."
    python test_fuzzing_pipeline.py --quick-test 2>&1 | tail -10 || true
    print_success "Test completed (check output above)"
else
    print_info "Skipping pipeline test (test_fuzzing_pipeline.py not found)"
fi

# Step 7: Setup directories
echo ""
echo "Step 7: Creating output directories..."
mkdir -p results
mkdir -p fuzzing_results
mkdir -p repos_temp
print_success "Output directories created"

# Step 8: Display usage information
echo ""
echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo ""
print_success "Environment: $CONTAINER_RUNTIME"
print_success "Python: $PYTHON_VERSION"
echo ""
echo "Next steps:"
echo "1. Activate environment: conda activate verifier_env"
echo "2. Run single patch test:"
echo "   python scripts/eval_cli.py --instance-id django__django-11001"
echo ""
echo "3. Run batch fuzzing (SLURM):"
echo "   sbatch slurm_jobs/run_fuzzing_single.slurm"
echo ""
echo "4. View documentation:"
echo "   cat COMPLETE_FUZZING_DOCUMENTATION.md"
echo ""
echo "For more help, see: README.md"
echo ""
