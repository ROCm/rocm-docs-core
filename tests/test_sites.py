from __future__ import annotations

from typing import Callable

from pathlib import Path

import pytest
from sphinx.testing.util import SphinxTestApp

import rocm_docs.projects

from .sphinx_fixtures import SITES_BASEFOLDER, TEMPLATE_FOLDER


@pytest.fixture()
def mocked_projects(
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, rocm_docs.projects._Project]:
    projects = {
        "a": rocm_docs.projects._Project("https://example.com/a", [], ""),
        "b": rocm_docs.projects._Project("https://example.com/b", [], ""),
    }
    monkeypatch.setattr(
        "rocm_docs.projects._load_projects",
        lambda *_, **__: projects,
    )
    return projects


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    mark = metafunc.definition.get_closest_marker("for_all_folders")
    if mark is not None and "build_factory" in metafunc.fixturenames:

        def folder_id(p: Path) -> str:
            return str(p.relative_to(mark.args[0]))

        metafunc.parametrize(
            "build_factory",
            (
                x.relative_to(SITES_BASEFOLDER)
                for x in SITES_BASEFOLDER.joinpath(mark.args[0]).iterdir()
            ),
            ids=folder_id,
            indirect=True,
        )


@pytest.mark.for_all_folders("pass")
@pytest.mark.template_folder(TEMPLATE_FOLDER)
@pytest.mark.usefixtures("_no_unexpected_warnings", "mocked_projects")
def test_pass(
    build_factory: Callable[..., SphinxTestApp],
) -> None:
    app = build_factory()
    app.build()
