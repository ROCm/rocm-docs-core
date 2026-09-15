"""Defines helpers for testing the rocm_docs sphinx extension"""

from __future__ import annotations

import functools
import shutil
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from sphinx.application import Sphinx

from .log_fixtures import ExpectLogFixture

COMMON_DATA_DIR = Path(__file__).parent / "common_data"


@pytest.fixture(autouse=True)
def with_common_data(monkeypatch: pytest.MonkeyPatch) -> None:
    """Point rocm-docs-core at the bundled test copy of rocm-docs-common.

    Data files are read locally from ROCM_DOCS_COMMON_DIR with no remote
    fallback, so every build-exercising test needs this set.
    """
    monkeypatch.setenv("ROCM_DOCS_COMMON_DIR", str(COMMON_DATA_DIR))


@pytest.fixture
def with_no_git_repo(
    monkeypatch: pytest.MonkeyPatch,
    expect_log: ExpectLogFixture,
) -> Iterator[ExpectLogFixture.Validator]:
    """Setup environment to allow testing outside a git repository"""
    monkeypatch.setenv("ROCM_DOCS_REMOTE_DETAILS", ",")

    with expect_log(
        "git.exc.InvalidGitRepositoryError",
        "ERROR",
        "test_external_projects",
    ) as validator:
        yield validator


SITES_BASEFOLDER = Path(__file__).parent / "sites"


def build_sphinx(
    srcdir: Path, outdir: Path, confdir: Path | None = None
) -> None:
    confdir = confdir or srcdir
    doctreedir = outdir / ".doctrees"
    buildername = "html"
    app = Sphinx(srcdir, confdir, outdir, doctreedir, buildername)
    app.build()


@pytest.fixture
def build_factory(
    request: pytest.FixtureRequest,
    tmp_path: Path,
) -> Callable[..., tuple[Path, Path]]:
    """A factory to prepare Sphinx source and output directories"""

    def make(src_folder: Path, /) -> tuple[Path, Path]:
        srcdir = tmp_path.joinpath(src_folder)
        outdir = tmp_path.joinpath(f"{src_folder}_build")
        srcdir.parent.mkdir(parents=True, exist_ok=True)

        mark = request.node.get_closest_marker("template_folder")
        if mark is not None:
            for i, dir in enumerate(mark.args):
                shutil.copytree(dir, srcdir, dirs_exist_ok=(i > 0))

        shutil.copytree(
            SITES_BASEFOLDER / src_folder, srcdir, dirs_exist_ok=True
        )
        return srcdir, outdir

    if hasattr(request, "param"):
        return functools.partial(make, request.param)
    return make


__all__ = ["build_factory", "with_common_data", "with_no_git_repo"]
