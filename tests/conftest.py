import os
import pathlib
import tempfile

_tmp_db = pathlib.Path(tempfile.mkdtemp(prefix="kf_test_")) / "test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp_db}"
os.environ.setdefault("OPENROUTER_API_KEY", "")

import pytest

from app.db import init_db
from app.faq_search import refresh_index
from seed_data import seed


@pytest.fixture(scope="session", autouse=True)
def _seeded_db():
    init_db()
    seed()
    refresh_index()
    yield
