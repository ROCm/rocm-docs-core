"""Defines helpers for testing the rocm_docs sphinx extension"""

from typing import Any, Callable, Dict, Generator, Iterable, Set

import dataclasses
import functools
import logging
import shutil
from pathlib import Path

import pytest
from sphinx.testing.path import path as sphinx_test_path
from sphinx.testing.util import SphinxTestApp

from .logging import AddLogHandlerFixture


@dataclasses.dataclass
class WithNoGitRepoFixture:
    """Type return from with_no_git_repo fixture"""

    _expected_logs: Set[logging.LogRecord]
    log_not_found_ok: bool = False

    def validate_logs(self, records: Iterable[logging.LogRecord]) -> None:
        """Validate that a warning is logged for not being in a repo"""
        for record in records:
            if (
                record.getMessage()
                == "Not in a Git Directory, disabling repository buttons"
            ):
                self._expected_logs.add(record)
                return
        if self.log_not_found_ok:
            return

        pytest.fail("Did not find git warning log")


@pytest.fixture()
def with_no_git_repo(
    monkeypatch: pytest.MonkeyPatch,
    expected_logs: Set[logging.LogRecord],
    add_log_handler: AddLogHandlerFixture,
) -> WithNoGitRepoFixture:
    """Setup environment to allow testing outside a git repository"""
    monkeypatch.setenv("ROCM_DOCS_REMOTE_DETAILS", ",")

    fixt = WithNoGitRepoFixture(expected_logs)
    add_log_handler(fixt.validate_logs)
    return fixt


SITES_BASEFOLDER = Path(__file__).parent / "sites"
TEMPLATE_FOLDER = SITES_BASEFOLDER / "templates" / "minimal"


@pytest.fixture()
def build_factory(
    request: pytest.FixtureRequest,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    with_no_git_repo: WithNoGitRepoFixture,  # noqa: ARG001,
) -> Generator[Callable[..., SphinxTestApp], None, None]:
    """A factory to make Sphinx test applications"""

    def make(src_folder: Path, /, **kwargs: Dict[Any, Any]) -> SphinxTestApp:
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
