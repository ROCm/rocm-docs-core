import os
import re
from typing import Optional, Union
from git import Repo, Remote, RemoteReference
from github import Github
from pathlib import Path


def get_branch(repo_path: Union[str, os.PathLike, None] = None):
    git_url = re.compile(r"git@(\w+(?:\.\w+)+):(.*)\.git")
    if repo_path is None:
        repo_path = Path()
    elif not isinstance(repo_path, Path):
        repo_path = Path(repo_path)
    repo = Repo(repo_path, search_parent_directories=True)
    assert not repo.bare
    if os.environ["READTHEDOCS"]:
        g = Github()
        remote_url = repo.remotes.origin.url
        build_type = os.environ["READTHEDOCS_VERSION_TYPE"]
        if build_type == "branch" or build_type == "tag":
            return remote_url, os.environ["READTHEDOCS_VERSION"]
        if build_type == "external":
            g_repo = g.get_repo(
                re.sub(r".*\.com/(.*)\.git", r"\1", remote_url)
            )
            pr = g_repo.get_pull(os.environ["READTHEDOCS_VERSION"])
            return pr.head.repo.html_url, pr.head.ref
        # if build type is unknown try the usual strategy
    for branch in repo.branches:
        if branch.commit == repo.head.commit:
            tracking = branch.tracking_branch()
            if tracking is not None:
                remote_url = repo.remotes[tracking.remote_name].url
                remote_url = git_url.sub(r"http://\1/\2", remote_url)
                return remote_url, tracking.remote_head
    for remote in repo.remotes:
        remote: Remote
        for ref in remote.refs:
            ref: RemoteReference
            if ref.commit == repo.head.commit:
                remote_url = git_url.sub(r"http://\1/\2", remote.url)
                return remote_url, ref.remote_head
    raise TypeError("Could not find the commit in the git repo.")


def format_toc(
    toc_path: Union[str, os.PathLike, None] = None,
    repo_path: Union[str, os.PathLike, None] = None,
    input_name: Optional[str] = None,
    output_name: Optional[str] = None,
):
    if toc_path is None:
        toc_path = Path()
    elif not isinstance(toc_path, Path):
        toc_path = Path(toc_path)
    if repo_path is None:
        repo_path = toc_path
    input_name = "_toc.yml.in" if input_name is None else input_name
    output_name = "_toc.yml" if output_name is None else output_name
    at_start = True

    url, branch = get_branch(repo_path)
    with open(toc_path / input_name, "r", encoding="utf-8") as input:
        with open(toc_path / output_name, "w", encoding="utf-8") as output:
            for line in input.readlines():
                if line[0] == "#" and at_start:
                    continue
                at_start = False
                output.write(line.format(branch=branch, url=url))
    return url, branch


if __name__ == "__main__":
    format_toc()
