"""Shared pytest fixtures for ETL tests."""
import sys
from pathlib import Path

# Ensure project root is on sys.path
ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
