from __future__ import annotations

from typing import Callable

from pathlib import Path

import pytest
from sphinx.testing.util import SphinxTestApp

from .log_fixtures import ExpectLogFixture
from .sphinx_fixtures import SITES_BASEFOLDER

TEMPLATE_FOLDER = SITES_BASEFOLDER / "templates"


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
@pytest.mark.template_folder(TEMPLATE_FOLDER / "minimal")
@pytest.mark.usefixtures("_no_unexpected_warnings", "mocked_projects")
def test_e2e_pass(
    build_factory: Callable[..., SphinxTestApp],
) -> None:
    app = build_factory()
    app.build()


@pytest.mark.for_all_folders("doxygen")
@pytest.mark.template_folder(
    TEMPLATE_FOLDER / "minimal", TEMPLATE_FOLDER / "doxygen"
)
@pytest.mark.usefixtures("_no_unexpected_warnings", "mocked_projects")
def test_e2e_doxygen(
    build_factory: Callable[..., SphinxTestApp], expect_log: ExpectLogFixture
) -> None:
    app: SphinxTestApp
    with expect_log(
        "sphinx.sphinx.util.docutils",
        "WARNING",
        "toctree directive not expected with external-toc [etoc.toctree]",
        required=False,
        capture_all=True,
    ):
        app = build_factory()
        app.build()

    expected_tagfile = Path(app.outdir, "tagfile.xml")
    assert expected_tagfile.is_file()
