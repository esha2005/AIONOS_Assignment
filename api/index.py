import os
import sys

# Ensure project root is in sys.path when Vercel runs api/index.py
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.main import app  # noqa: E402
