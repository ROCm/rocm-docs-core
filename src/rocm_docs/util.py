"""Utilities for rocm-docs-core."""

from __future__ import annotations

from typing import Any

import enum
import functools
import os
import re
from pathlib import Path

import github
from git.exc import InvalidGitRepositoryError
from git.repo import Repo
from github.GithubException import UnknownObjectException


class VersionType(enum.Enum):
    """Describes how recent a version is (i.e. latest rc, or an older release)"""

    DEVELOPMENT = enum.auto()
    LATEST_RELEASE = enum.auto()
    OLD_RELEASE = enum.auto()
    RELEASE_CANDIDATE = enum.auto()


def get_path_to_docs(
    conf_path: str | os.PathLike[Any] | None = None,
    repo_path: str | os.PathLike[Any] | None = None,
) -> str:
    """Get the relative path from the repo root to the docs."""
    if conf_path is None:
        conf_path = Path()
    elif not isinstance(conf_path, Path):
        conf_path = Path(conf_path)
    if repo_path is None:
        repo_path = conf_path
    elif not isinstance(repo_path, Path):
        repo_path = Path(repo_path)
    repo = Repo(path=repo_path, search_parent_directories=True)
    return os.path.relpath(str(conf_path), repo.working_dir)


@functools.lru_cache
def get_branch(
    repo_path: str | os.PathLike[Any] | None = None,
) -> tuple[str, str]:
    """Get the branch whose tip is checked out, even if detached.

    May be overridden with the environment variable `ROCM_DOCS_REMOTE_DETAILS`.
    """
    if "ROCM_DOCS_REMOTE_DETAILS" in os.environ:
        remote_details = os.environ["ROCM_DOCS_REMOTE_DETAILS"].split(",")
        return (remote_details[0], remote_details[1])

    def get_repo_url(remote_url: str) -> str:
        ssh_pattern = re.compile(r"git@(\w+(?:\.\w+)+):(.*)\.git")
        http_pattern = re.compile(r"(https?://.+)\.git")
        remote_url, num_subs = ssh_pattern.subn(
            r"http://\1/\2", remote_url, count=1
        )
        if num_subs > 0:
            return remote_url
        return http_pattern.sub(r"\1", remote_url, count=1)

    if os.environ.get("READTHEDOCS", ""):
        remote_url = os.environ.get("READTHEDOCS_GIT_CLONE_URL", "")
        url = get_repo_url(remote_url)
        build_type = os.environ["READTHEDOCS_VERSION_TYPE"]
        match = re.match(r"(?:.*://)?.*\.(com|io)[/:](.*)\.git", remote_url)
        assert match is not None
        repo_fqn: str = match[1]
        if build_type in ("branch", "tag"):
            return url, os.environ["READTHEDOCS_VERSION"]
        if build_type == "external":
            gh_inst = github.Github(os.environ.get("TOKEN", None))
            print("Repository URL: " + repo_fqn)
            try:
                pull = gh_inst.get_repo(repo_fqn).get_pull(
                    int(os.environ["READTHEDOCS_VERSION"])
                )
                return url, pull.head.ref
            except UnknownObjectException as err:
                if err.data["message"] == "Not Found":
                    # Possibly a private repository that we're not
                    # authenticated for, fallback
                    return (
                        url,
                        "external-" + os.environ["READTHEDOCS_VERSION"],
                    )
        # if build type is unknown try the usual strategy

    if repo_path is None:
        repo_path = Path()
    elif not isinstance(repo_path, Path):
        repo_path = Path(repo_path)
    repo = Repo(repo_path, search_parent_directories=True)
    assert not repo.bare
    for head in repo.heads:
        if head.commit == repo.head.commit:
            tracking = head.tracking_branch()
            if tracking is not None:
                remote_url = repo.remotes[tracking.remote_name].url
                remote_url = get_repo_url(remote_url)
                return remote_url, tracking.remote_head
    for remote in repo.remotes:
        for ref in remote.refs:
            if ref.commit == repo.head.commit:
                remote_url = get_repo_url(remote.url)
                return remote_url, ref.remote_head

    # Fall-back to the current branch or a fallback value if HEAD is detached
    # In this case the repository URL cannot be provided
    try:
        branch = repo.active_branch.name
    except TypeError:
        branch = "branch-not-found"

    return "", branch


__all__ = [
    "InvalidGitRepositoryError",
    "VersionType",
    "get_branch",
    "get_path_to_docs",
]
