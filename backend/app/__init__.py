import sys
import os

_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_repo_root = os.path.dirname(_backend_dir)

for _path in [_backend_dir, _repo_root]:
    if _path not in sys.path:
        sys.path.insert(0, _path)
