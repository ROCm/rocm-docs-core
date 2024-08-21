"""Defines fixtures for interacting with projects.py"""

from __future__ import annotations

from collections.abc import Callable

import pytest

import rocm_docs.projects


@pytest.fixture
def mock_projects(
    monkeypatch: pytest.MonkeyPatch,
) -> Callable[[dict[str, rocm_docs.projects._Project]], None]:
    """Mock the list of projects loaded by projects.py"""

    def do_mock(projects: dict[str, rocm_docs.projects._Project]) -> None:
        monkeypatch.setattr(
            "rocm_docs.projects._load_projects",
            lambda *_, **__: projects,
        )

    return do_mock


@pytest.fixture
def mocked_projects(
    mock_projects: Callable[[dict[str, rocm_docs.projects._Project]], None],
) -> dict[str, rocm_docs.projects._Project]:
    """Standard mocked projects for tests"""
    projects = {
        "a": rocm_docs.projects._Project(
            "https://example.com/a", [], "", ".doxygen/docBin/html"
        ),
        "b": rocm_docs.projects._Project("https://example.com/b", [], ""),
    }
    mock_projects(projects)
    return projects
