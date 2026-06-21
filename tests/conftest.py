from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def deterministic_specialists_by_default(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("PARLIAMENT_SPECIALIST_BACKEND", "deterministic")
    import parliament.specialists as specialists

    specialists._DEFAULT_BACKEND = None
    yield
    specialists._DEFAULT_BACKEND = None

