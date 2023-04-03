"""Utilities for rocm-docs-core."""
import functools
import os
import re
from pathlib import Path
from typing import Optional, Tuple, Union

import github
from git import Remote, RemoteReference
from git.repo import Repo
from github.GithubException import UnknownObjectException


def get_path_to_docs(
    conf_path: Union[str, os.PathLike, None] = None,
    repo_path: Union[str, os.PathLike, None] = None,
):
    """Get the relative path from the repo root to the docs."""
    if conf_path is None:
        conf_path = Path()
    elif not isinstance(conf_path, Path):
        conf_path = Path(conf_path)
    if repo_path is None:
        repo_path = conf_path
    elif not isinstance(repo_path, Path):
        repo_path = Path(repo_path)
    repo = Repo(repo_path, search_parent_directories=True)
    return os.path.relpath(str(conf_path), repo.working_dir)


@functools.lru_cache
def get_branch(
    repo_path: Union[str, os.PathLike, None] = None,
) -> Tuple[str, str, bool]:
    """Get the branch whose tip is checked out, even if detached.
    May be overridden with the environment variable `ROCM_DOCS_REMOTE_DETAILS`
    """
    if "ROCM_DOCS_REMOTE_DETAILS" in os.environ:
        remote_details = os.environ["ROCM_DOCS_REMOTE_DETAILS"].split(",")
        return (
            remote_details[0],
            remote_details[1],
            remote_details[2].lower() in ["1", "on", "true", "yes"],
        )

    def get_repo_url(remote_url: str) -> str:
        ssh_pattern = re.compile(r"git@(\w+(?:\.\w+)+):(.*)\.git")
        http_pattern = re.compile(r"(https?://.+)\.git")
        remote_url, num_subs = ssh_pattern.subn(
            r"http://\1/\2", remote_url, count=1
        )
        if num_subs > 0:
            return remote_url
        remote_url = http_pattern.sub(r"\1", remote_url, count=1)
        return remote_url

    if repo_path is None:
        repo_path = Path()
    elif not isinstance(repo_path, Path):
        repo_path = Path(repo_path)
    repo = Repo(repo_path, search_parent_directories=True)
    assert not repo.bare
    if os.environ.get("READTHEDOCS", ""):
        gh_token = os.environ.get("TOKEN", "")
        if gh_token:
            gh_inst = github.Github(gh_token)
        else:
            gh_inst = github.Github()
        remote_url = repo.remotes.origin.url
        build_type = os.environ["READTHEDOCS_VERSION_TYPE"]
        if build_type in ("branch", "tag"):
            url = re.sub(
                r"(?:.*://)?(.*\.com)[/:](.*)\.git", r"\1/\2", remote_url
            )
            return url, os.environ["READTHEDOCS_VERSION"], True
        if build_type == "external":
            repo_fqn = re.sub(r".*\.com[/:](.*)\.git", r"\1", remote_url)
            print("Repository URL: " + repo_fqn)
            try:
                pull = gh_inst.get_repo(repo_fqn).get_pull(
                    int(os.environ["READTHEDOCS_VERSION"])
                )
                return pull.head.repo.html_url, pull.head.ref, True
            except UnknownObjectException as err:
                if err.data["message"] == "Not Found":
                    # Possibly a private repository that we're not
                    # authenticated for, fallback
                    url = re.sub(
                        r"(?:.*://)?(.*\.com)[/:](.*)\.git",
                        r"\1/\2",
                        remote_url,
                    )
                    return (
                        url,
                        "external-" + os.environ["READTHEDOCS_VERSION"],
                        False,
                    )
        # if build type is unknown try the usual strategy
    for branch in repo.branches:
        if branch.commit == repo.head.commit:
            tracking = branch.tracking_branch()
            if tracking is not None:
                remote_url = repo.remotes[tracking.remote_name].url
                remote_url = get_repo_url(remote_url)
                return remote_url, tracking.remote_head, True
    for remote in repo.remotes:
        remote: Remote
        for ref in remote.refs:
            ref: RemoteReference
            if ref.commit == repo.head.commit:
                remote_url = get_repo_url(remote.url)
                return remote_url, ref.remote_head, True

    # Fall-back to the current branch or a fallback value if HEAD is detached
    # In this case the repository URL cannot be provided
    branch: str
    try:
        branch = repo.active_branch.name
    except TypeError:
        branch = "branch-not-found"

    return "", branch, False


def format_toc(
    toc_path: Union[str, os.PathLike, None] = None,
    repo_path: Union[str, os.PathLike, None] = None,
    input_name: Optional[str] = None,
    output_name: Optional[str] = None,
):
    """Format the input table of contents with additional information."""
    if toc_path is None:
        toc_path = Path()
    elif not isinstance(toc_path, Path):
        toc_path = Path(toc_path)
    if repo_path is None:
        repo_path = toc_path
    input_name = "./.sphinx/_toc.yml.in" if input_name is None else input_name
    output_name = "./.sphinx/_toc.yml" if output_name is None else output_name
    at_start = True

    url, branch, _ = get_branch(repo_path)
    with open(toc_path / input_name, "r", encoding="utf-8") as toc_in:
        with open(toc_path / output_name, "w", encoding="utf-8") as toc_out:
            for line in toc_in.readlines():
                if line[0] == "#" and at_start:
                    continue
                at_start = False
                toc_out.write(line.format(branch=branch, url=url))


if __name__ == "__main__":
    format_toc()
