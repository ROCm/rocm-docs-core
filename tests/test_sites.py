from typing import Any, Callable, Dict, Generator

import shutil
from pathlib import Path

import pytest
from sphinx.testing.path import path as sphinx_test_path
from sphinx.testing.util import SphinxTestApp

pytest_plugins = ["sphinx.testing.fixtures"]

SITES_BASEFOLDER = Path(__file__).parent / "sites"
TEMPLATE_FOLDER = SITES_BASEFOLDER / "templates" / "minimal"


@pytest.fixture()
def with_no_git_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ROCM_DOCS_REMOTE_DETAILS", ",")


@pytest.fixture()
def build_factory(
    request: pytest.FixtureRequest,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    with_no_git_repo: None,  # noqa: ARG001
) -> Generator[Callable[..., SphinxTestApp], None, None]:
    src_folder = request.param

    def make(**kwargs: Dict[Any, Any]) -> SphinxTestApp:
        srcdir = tmp_path.joinpath(src_folder)
        srcdir.parent.mkdir(parents=True, exist_ok=True)

        mark = request.node.get_closest_marker("template_folder")
        if mark is not None:
            shutil.copytree(mark.args[0], srcdir)

        shutil.copytree(
            SITES_BASEFOLDER / src_folder, srcdir, dirs_exist_ok=True
        )
        return make_app(srcdir=sphinx_test_path(srcdir), **kwargs)

    yield make


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
def test_pass(build_factory: Callable[..., SphinxTestApp]) -> None:
    app = build_factory()
    app.build()
