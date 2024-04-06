import os
import sys


def check_root_path() -> None:
    ROOT = os.path.dirname(__file__)
    root_path = os.path.join(ROOT, "../")
    if root_path not in sys.path:
        sys.path.append(root_path)
