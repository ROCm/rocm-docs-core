"""Defines helpers for testing the rocm_docs sphinx extension"""

from __future__ import annotations

from typing import Any

import functools
import shutil
from collections.abc import Callable, Iterator
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
        "",
        "",
        "",
    ) as validator:
        yield validator


SITES_BASEFOLDER = Path(__file__).parent / "sites"


@pytest.fixture()
def build_factory(
    request: pytest.FixtureRequest,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    with_no_git_repo: ExpectLogFixture.Validator,  # noqa: ARG001,
) -> Callable[..., SphinxTestApp]:
    """A factory to make Sphinx test applications"""

    def make(src_folder: Path, /, **kwargs: dict[Any, Any]) -> SphinxTestApp:
        srcdir = tmp_path.joinpath(src_folder)
        srcdir.parent.mkdir(parents=True, exist_ok=True)

        mark = request.node.get_closest_marker("template_folder")
        if mark is not None:
            for i, dir in enumerate(mark.args):
                shutil.copytree(dir, srcdir, dirs_exist_ok=(i > 0))

        shutil.copytree(
            SITES_BASEFOLDER / src_folder, srcdir, dirs_exist_ok=True
        )
        return make_app(srcdir=sphinx_test_path(srcdir), **kwargs)

    if hasattr(request, "param"):
        return functools.partial(make, request.param)
    return make


__all__ = ["with_no_git_repo", "build_factory"]
