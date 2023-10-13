from typing import Callable

from pathlib import Path

import pytest
from sphinx.testing.util import SphinxTestApp

import rocm_docs.projects

from .sphinx import SITES_BASEFOLDER, TEMPLATE_FOLDER


@pytest.fixture()
def mocked_projects(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "rocm_docs.projects._load_projects",
        lambda *_, **__: {
            "a": rocm_docs.projects._Project("https://example.com/a", [], ""),
            "b": rocm_docs.projects._Project("https://example.com/b", [], ""),
        },
    )


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    mark = metafunc.definition.get_closest_marker("for_all_folders")
    if mark is not None and "build_factory" in metafunc.fixturenames:

        def folder_id(p: Path) -> str:
            return str(p.relative_to(mark.args[0]))

        metafunc.parametrize(
            "build_factory",
            map(
                lambda x: x.relative_to(SITES_BASEFOLDER),
                SITES_BASEFOLDER.joinpath(mark.args[0]).iterdir(),
            ),
            ids=folder_id,
            indirect=True,
        )


@pytest.mark.for_all_folders("pass")
@pytest.mark.template_folder(TEMPLATE_FOLDER)
def test_pass(
    mocked_projects: None,  # noqa: ARG001
    build_factory: Callable[..., SphinxTestApp],
    no_unexpected_logs: None,  # noqa: ARG001
) -> None:
    app = build_factory()
    app.build()
