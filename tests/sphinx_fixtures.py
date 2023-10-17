"""Defines helpers for testing the rocm_docs sphinx extension"""

from __future__ import annotations

from typing import Any, Callable, Generator, Iterator

import functools
import shutil
from pathlib import Path

import pytest
from sphinx.testing.path import path as sphinx_test_path
from sphinx.testing.util import SphinxTestApp

from .log_fixtures import ExpectLogFixture


@pytest.fixture()
def with_no_git_repo(
    monkeypatch: pytest.MonkeyPatch,
    expect_log: ExpectLogFixture,
) -> Iterator[ExpectLogFixture.Validator]:
    """Setup environment to allow testing outside a git repository"""
    monkeypatch.setenv("ROCM_DOCS_REMOTE_DETAILS", ",")

    with expect_log(
        "sphinx.rocm_docs.theme",
        "WARNING",
        "Not in a Git Directory, disabling repository buttons",
    ) as validator:
        yield validator


SITES_BASEFOLDER = Path(__file__).parent / "sites"
TEMPLATE_FOLDER = SITES_BASEFOLDER / "templates" / "minimal"


@pytest.fixture()
def build_factory(
    request: pytest.FixtureRequest,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    with_no_git_repo: ExpectLogFixture.Validator,  # noqa: ARG001,
) -> Generator[Callable[..., SphinxTestApp], None, None]:
    """A factory to make Sphinx test applications"""

    def make(src_folder: Path, /, **kwargs: dict[Any, Any]) -> SphinxTestApp:
        srcdir = tmp_path.joinpath(src_folder)
        srcdir.parent.mkdir(parents=True, exist_ok=True)

        mark = request.node.get_closest_marker("template_folder")
        if mark is not None:
            shutil.copytree(mark.args[0], srcdir)

        shutil.copytree(
            SITES_BASEFOLDER / src_folder, srcdir, dirs_exist_ok=True
        )
        return make_app(srcdir=sphinx_test_path(srcdir), **kwargs)

    if hasattr(request, "param"):
        yield functools.partial(make, request.param)
    else:
        yield make


__all__ = ["with_no_git_repo", "build_factory"]
