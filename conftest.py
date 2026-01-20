"""
Root conftest.py - Sets up Python paths for all tests.
This file is loaded before any test modules, ensuring paths are correct.
"""
import sys
from pathlib import Path

# Get project root (this file's directory)
PROJECT_ROOT = Path(__file__).parent

# Add module paths
backend_src = PROJECT_ROOT / "backend" / "src"
shared_dir = PROJECT_ROOT / "shared"
worker_src = PROJECT_ROOT / "worker" / "src"

# Add to sys.path if not already present
if str(backend_src) not in sys.path:
    sys.path.insert(0, str(backend_src))

if str(shared_dir) not in sys.path:
    sys.path.insert(0, str(shared_dir))

if str(worker_src) not in sys.path and worker_src.exists():
    sys.path.insert(0, str(worker_src))
