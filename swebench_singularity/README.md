# SWE-bench Singularity Module

Dynamic container management system for SWE-bench evaluations.

## Module Structure

```
swebench_singularity/
├── __init__.py              # Package initialization
├── config.py                # Configuration management
├── docker_resolver.py       # Docker image name resolution
├── singularity_builder.py   # Singularity image building
├── cache_manager.py         # Cache management
├── instance_runner.py       # Test execution
├── utils.py                 # Utility functions
└── README.md               # This file
```

## Quick API Reference

### Configuration

```python
from swebench_singularity import Config

# Load default configuration
config = Config()

# Load custom configuration
config = Config("/path/to/config.yaml")

# Get configuration value
cache_dir = config.get("singularity.cache_dir")

# Set configuration value
config.set("parallel.max_workers", 20)
```

### Docker Image Resolution

```python
from swebench_singularity import DockerImageResolver

resolver = DockerImageResolver()

# Parse instance ID
org, repo, version = resolver.parse_instance_id("django__django-12345")
# Returns: ("django", "django", "12345")

# Get repository name
repo_name = resolver.get_repo_short_name("pytest-dev__pytest-7490")
# Returns: "pytest"

# Resolve to Docker images
images = resolver.resolve_docker_image("django__django-12345")
# Returns: [DockerImage(...), DockerImage(...), ...]

# Find available image
image = resolver.find_available_image("django__django-12345")
# Returns: DockerImage or None
```

### Singularity Building

```python
from swebench_singularity import SingularityBuilder

builder = SingularityBuilder()

# Build instance (with caching)
result = builder.build_instance("pytest-dev__pytest-7490")

if result.success:
    print(f"Built: {result.sif_path}")
    print(f"Time: {result.build_time_seconds}s")
    print(f"From cache: {result.from_cache}")
else:
    print(f"Failed: {result.error_message}")

# Build multiple instances
results = builder.build_batch([
    "pytest-dev__pytest-7490",
    "django__django-12345",
    "flask__flask-4992",
])
```

### Cache Management

```python
from swebench_singularity import CacheManager

cache = CacheManager()

# Check if cached
if cache.exists("pytest-dev__pytest-7490"):
    sif_path = cache.get("pytest-dev__pytest-7490")
    print(f"Cached at: {sif_path}")

# List cached entries
entries = cache.list_cached()
for entry in entries:
    print(f"{entry.instance_id}: {entry.size_mb:.1f} MB, {entry.age_days:.1f} days old")

# Get cache statistics
stats = cache.get_cache_stats()
print(f"Total: {stats['total_entries']} entries, {stats['total_size_gb']} GB")

# Clean cache
result = cache.cleanup(max_age_days=30, max_size_gb=50)
print(f"Removed: {result['total_removed']} entries")

# Remove specific instance
cache.remove("pytest-dev__pytest-7490")

# Clear all
cache.clear()
```

### Instance Execution

```python
from swebench_singularity import InstanceRunner

runner = InstanceRunner()

# Run single instance
result = runner.run_swebench_instance(
    instance_id="pytest-dev__pytest-7490",
    predictions_path="my_patch.diff",
    force_rebuild=False,
)

print(f"Success: {result.success}")
print(f"Tests: {result.passed_tests}/{result.total_tests}")
print(f"Time: {result.execution_time_seconds}s")

# Run batch
results = runner.run_batch([
    "pytest-dev__pytest-7490",
    "django__django-12345",
])

for instance_id, result in results.items():
    print(f"{instance_id}: {result.success}")
```

### Utilities

```python
from swebench_singularity.utils import (
    setup_logging,
    format_time,
    format_bytes,
    validate_instance_id,
    parse_instance_list,
)

# Setup logging
setup_logging(level="INFO", log_file="run.log")

# Format time
print(format_time(123.45))  # "2m 3s"

# Format bytes
print(format_bytes(1234567890))  # "1.15 GB"

# Validate instance ID
if validate_instance_id("django__django-12345"):
    print("Valid!")

# Parse instance list from file
instances = parse_instance_list("instances.txt")
```

## Example: Complete Workflow

```python
from swebench_singularity import (
    Config,
    SingularityBuilder,
    InstanceRunner,
    CacheManager,
)

# Configure
config = Config()
config.set("parallel.max_workers", 10)

# Build containers
builder = SingularityBuilder(config)
build_results = builder.build_batch([
    "pytest-dev__pytest-7490",
    "django__django-12345",
])

# Run tests
runner = InstanceRunner(config)
test_results = runner.run_batch([
    "pytest-dev__pytest-7490",
    "django__django-12345",
])

# Analyze results
for instance_id, result in test_results.items():
    if result.success:
        print(f"✓ {instance_id}: {result.passed_tests}/{result.total_tests} passed")
    else:
        print(f"✗ {instance_id}: {result.error_message}")

# Clean cache
cache = CacheManager(config)
cache.cleanup(max_age_days=7)
```

## Integration with Existing Pipeline

```python
# Option 1: Use directly in evaluation pipeline
from swebench_singularity import InstanceRunner

runner = InstanceRunner()
result = runner.run_swebench_instance("pytest-dev__pytest-7490")

# Option 2: Just build containers, use existing execution
from swebench_singularity import SingularityBuilder

builder = SingularityBuilder()
result = builder.build_instance("pytest-dev__pytest-7490")

if result.success:
    # Use result.sif_path with existing execution code
    sif_path = result.sif_path
```

## Error Handling

```python
from swebench_singularity import SingularityBuilder
import logging

logger = logging.getLogger(__name__)

builder = SingularityBuilder()

try:
    result = builder.build_instance("invalid-id")
    if not result.success:
        logger.error(f"Build failed: {result.error_message}")
except ValueError as e:
    logger.error(f"Invalid instance ID: {e}")
except Exception as e:
    logger.error(f"Unexpected error: {e}")
```

## Configuration Options

See `config/swebench_config.yaml` for all options:

- **docker**: Docker registry and image patterns
- **singularity**: Build settings and cache paths
- **execution**: Test execution parameters
- **parallel**: Parallel processing settings
- **cache**: Cache management policies
- **logging**: Logging configuration
- **integration**: Integration with existing pipeline

## Development

### Running Tests

```bash
# Test import
python -c "from swebench_singularity import Config; print('OK')"

# Test configuration
python -c "from swebench_singularity import Config; c = Config(); print(c.to_dict())"

# Test resolver
python -c "from swebench_singularity import DockerImageResolver; r = DockerImageResolver(); print(r.parse_instance_id('pytest-dev__pytest-7490'))"
```

### Adding New Repositories

Edit `config/swebench_config.yaml`:

```yaml
repo_mapping:
  "myorg/myrepo": "myrepo"

docker:
  image_patterns:
    - "aorwall/swe-bench-{repo}:{instance_id}"
    - "my-registry/{repo}:{instance_id}"
```

## See Also

- **Main Documentation**: `Documentation/SWEBENCH_SINGULARITY_RUNNER.md`
- **Quick Start**: `SWEBENCH_SINGULARITY_QUICKSTART.md`
- **Configuration**: `config/swebench_config.yaml`
- **CLI Scripts**: `run_swebench_instance.py`, `run_swebench_batch.py`
