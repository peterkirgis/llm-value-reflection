import sys
from pathlib import Path

# Make recode/src importable from the tests.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
