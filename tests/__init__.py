import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Make `core` importable as a top-level package and the mock server as `mock_lemonade`.
sys.path[:0] = [os.path.join(ROOT, "addon", "globalPlugins", "labelade"), os.path.join(ROOT, "tools")]
