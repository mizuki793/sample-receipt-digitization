import pytest
from unittest.mock import AsyncMock, MagicMock

import main


pytest_plugins = ('pytest_asyncio',)


@pytest.fixture(autouse=True)
def disable_app_startup(monkeypatch):
    monkeypatch.setattr(main, "init_mongo_client", MagicMock())
    monkeypatch.setattr(main, "init_database", MagicMock())
    monkeypatch.setattr(main, "close_mongo_client", MagicMock())
    yield
