import copy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import app.main as main  # noqa: E402


@pytest.fixture(autouse=True)
def reset_cache():
    original = copy.deepcopy(main._cache)
    yield
    main._cache.clear()
    main._cache.update(original)
