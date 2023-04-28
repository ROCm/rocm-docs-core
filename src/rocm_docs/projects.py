"""Handle external projects (remote loading of intersphinx_mapping from file,
templating projects in toc.yml)"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import fastjsonschema  # type: ignore[import]
import github
import sphinx.util.logging
import yaml
from pydata_sphinx_theme.utils import config_provided_by_user  # type: ignore[import]
from sphinx.application import Sphinx
from sphinx.config import Config

import rocm_docs.formatting as formatting
import rocm_docs.util as util

if sys.version_info < (3, 9):
    # importlib.resources either doesn't exist or lacks the files()
    # function, so use the PyPI version:
    import importlib_resources
    import importlib_resources.abc as importlib_abc
else:
    # importlib.resources has files(), so use that:
    import importlib.resources as importlib_resources

    if sys.version_info < (3, 11):
        import importlib.abc as importlib_abc
    else:
        import importlib.resources.abc as importlib_abc

Traversable = importlib_abc.Traversable

Inventory = Union[str, None, Tuple[Union[str, None], ...]]
ProjectMapping = Tuple[str, Inventory]

DEFAULT_INTERSPHINX_REPOSITORY = "RadeonOpenCompute/rocm-docs-core"
DEFAULT_INTERSPHINX_BRANCH = "develop"

logger = sphinx.util.logging.getLogger(__name__)


class InvalidMappingFile(RuntimeError):
    pass


def _format_mapping(
    mapping_yaml: Union[str, Traversable], version: str
) -> Dict[str, ProjectMapping]:
    base = importlib_resources.files("rocm_docs") / "data"
    schema_file = base / "projects.schema.json"

    schema = json.load(schema_file.open(encoding="utf-8"))
    contents = yaml.safe_load(
        mapping_yaml
        if isinstance(mapping_yaml, str)
        else mapping_yaml.open(encoding="utf-8")
    )

    ProjectItem = Union[str, None, List[Union[str, None]]]
    Project = Union[str, Dict[str, ProjectItem]]
    data: Dict[str, Union[int, Dict[str, Project]]]
    try:
        data = fastjsonschema.validate(schema, contents)
    except fastjsonschema.exceptions.JsonSchemaException as err:
        raise InvalidMappingFile(
            f"Mapping file is invalid: {err.message}."
        ) from err

    def format_item(item: Union[str, None]) -> Union[str, None]:
        if isinstance(item, str):
            return item.replace("${version}", version)
        return item

    def get_target(project: Project) -> ProjectMapping:
        if isinstance(project, str):
            return (project.replace("${version}", version), None)

        assert isinstance(project["target"], str)
        target: str = project["target"].replace("${version}", version)

        inventory: ProjectItem = project["inventory"]
        if isinstance(inventory, list):
            return (target, tuple(map(format_item, inventory)))

        return (target, format_item(inventory))

    assert isinstance(data["projects"], dict)
    return {key: get_target(value) for key, value in data["projects"].items()}


class FailedToFetchMappingFile(RuntimeError):
    pass


def _fetch_mapping(
    remote_repository: str,
    remote_branch: str,
    mapping_file_loc: str,
    remote_filepath: str,
) -> str:
    try:
        gh = github.Github(os.environ.get("TOKEN"))
        repo = gh.get_repo(remote_repository)
        contents = repo.get_contents(remote_filepath, remote_branch)
        if isinstance(contents, list):
            raise FailedToFetchMappingFile("Expected a file not a directory!")

        return contents.decoded_content.decode("utf-8")
    except github.GithubException as err:
        assert isinstance(err.data["message"], str)
        message: str = err.data["message"]
        raise FailedToFetchMappingFile(
            "failed to read remote mappings from "
            f"{remote_repository}:{remote_filepath} "
            f"on branch={remote_branch}, API returned {err.status}: {message}.",
        ) from err


def _load_mapping(repo_path: Path) -> Dict[str, ProjectMapping]:
    mapping_file_loc = "data/projects.yaml"

    _, branch, __ = util.get_branch(repo_path)
    mapping: Optional[Dict[str, ProjectMapping]] = None
    if "SKIP_INTERSPHINX_REMOTE" not in os.environ:
        try:
            remote_repository = os.environ.get(
                "INTERSPHINX_REPOSITORY", DEFAULT_INTERSPHINX_REPOSITORY
            )
            remote_branch = os.environ.get(
                "INTERSPHINX_BRANCH", DEFAULT_INTERSPHINX_BRANCH
            )
            remote_filepath = "src/rocm_docs/" + mapping_file_loc
            mapping = _format_mapping(
                _fetch_mapping(
                    remote_repository,
                    remote_branch,
                    mapping_file_loc,
                    remote_filepath,
                ),
                branch,
            )
        except (FailedToFetchMappingFile, InvalidMappingFile) as err:
            logger.warning(
                f"Failed to use remote mapping: {err} "
                "Falling back to bundled mapping."
            )

    if mapping is None:
        mapping = _format_mapping(
            importlib_resources.files("rocm_docs") / mapping_file_loc, branch
        )

    return mapping


def _get_context(
    repo_path: Path, mapping: Dict[str, ProjectMapping]
) -> Dict[str, Any]:
    url, branch, __ = util.get_branch(repo_path)
    return {
        "url": url,
        "branch": branch,
        "projects": {k: v[0].rstrip("/") for k, v in mapping.items()},
    }


def _update_config(app: Sphinx, _: Config) -> None:
    if not config_provided_by_user(app, "intersphinx_disabled_domains"):
        app.config.intersphinx_disabled_domains = ["std"]  # type: ignore[attr-defined]

    default = _load_mapping(Path(app.srcdir))
    mapping: Dict[str, ProjectMapping] = app.config.intersphinx_mapping
    for key, value in default.items():
        mapping.setdefault(key, value)

    formatting.format_toc(
        Path(app.srcdir, ".sphinx/_toc.yml.in"),
        Path(app.srcdir, ".sphinx/_toc.yml"),
        _get_context(Path(app.srcdir), mapping),
    )
    app.config.external_toc_path = "./.sphinx/_toc.yml"  # type: ignore[attr-defined]


def setup(app: Sphinx) -> Dict[str, Any]:
    app.setup_extension("sphinx.ext.intersphinx")
    app.setup_extension("sphinx_external_toc")

    # This needs to happen before external-tocs's config-inited (priority=900)
    app.connect("config-inited", _update_config)
    return {"parallel_read_safe": True, "parallel_write_safe": True}


def debug_projects() -> None:
    mapping = _load_mapping(Path())
    print(mapping)
    context = _get_context(Path(), mapping)
    print(context)
    toc_in = Path("./.sphinx/_toc.yml.in")
    if len(sys.argv) > 1:
        toc_in = Path(sys.argv[1])
    toc_out = toc_in.with_suffix("")
    if len(sys.argv) > 2:
        toc_out = Path(sys.argv[2])

    formatting.format_toc(
        toc_in,
        toc_out,
        _get_context(Path(), mapping),
    )


if __name__ == "__main__":
    debug_projects()
