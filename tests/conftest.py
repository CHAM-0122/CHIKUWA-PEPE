from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import Settings
from app.main import create_app


@pytest.fixture()
def client(tmp_path: Path):
    db_path = tmp_path / "test.db"
    upload_dir = tmp_path / "uploads"
    settings = Settings(
        app_env="test",
        database_url=f"sqlite:///{db_path}",
        upload_dir=str(upload_dir),
        secret_key="test-secret",
    )
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client
