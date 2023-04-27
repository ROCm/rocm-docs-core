"""Load intersphinx mappings from an external file possibly fetched from a
remote location"""

import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple, Union

import fastjsonschema  # type: ignore[import]
import github
import sphinx.util.logging
import yaml
from pydata_sphinx_theme.utils import config_provided_by_user  # type: ignore[import]
from sphinx.application import Sphinx
from sphinx.config import Config

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


def _format_mapping(
    mapping_yaml: Union[str, Traversable], version: str
) -> Dict[str, ProjectMapping]:
    base = importlib_resources.files("rocm_docs") / "data"
    schema_file = base / "intersphinx_mapping.schema.json"

    schema = json.load(schema_file.open(encoding="utf-8"))
    contents = yaml.safe_load(
        mapping_yaml
        if isinstance(mapping_yaml, str)
        else mapping_yaml.open(encoding="utf-8")
    )

    ProjectItem = Union[str, None, List[Union[str, None]]]
    Project = Dict[str, ProjectItem]
    data: Dict[str, Union[int, Dict[str, Project]]]
    try:
        data = fastjsonschema.validate(schema, contents)
    except fastjsonschema.exceptions.JsonSchemaValueException as err:
        raise RuntimeError(
            str(schema_file) + ": mapping file not valid."
        ) from err

    def format_item(item: Union[str, None]) -> Union[str, None]:
        if isinstance(item, str):
            return item.replace("${version}", version)
        return item

    def get_target(project: Project) -> ProjectMapping:
        assert isinstance(project["target"], str)
        target: str = project["target"].replace("${version}", version)

        inventory: ProjectItem = project["inventory"]
        if isinstance(inventory, list):
            return (target, tuple(map(format_item, inventory)))

        return (target, format_item(inventory))

    assert isinstance(data["projects"], dict)
    return {key: get_target(value) for key, value in data["projects"].items()}


def _fetch_mapping(
    remote_repository: str, remote_branch: str
) -> Union[str, Traversable]:
    mapping_file_loc = "data/intersphinx_mapping.yaml"
    remote_filepath = "src/rocm_docs/" + mapping_file_loc
    try:
        gh = github.Github(os.environ.get("TOKEN"))
        repo = gh.get_repo(remote_repository)
        contents = repo.get_contents(remote_filepath, remote_branch)
        if isinstance(contents, list):
            raise RuntimeError("Expected a file not a directory!")

        return contents.decoded_content.decode("utf-8")
    except github.GithubException as err:
        assert isinstance(err.data["message"], str)
        message: str = err.data["message"]
        logger.warning(
            "failed to read remote mappings from "
            f"{remote_repository}:{remote_filepath} "
            f"on branch={remote_branch}, API returned {err.status}: {message}",
        )
        return importlib_resources.files("rocm_docs") / mapping_file_loc


def _update_config(app: Sphinx, _: Config) -> None:
    if not config_provided_by_user(app, "intersphinx_disabled_domains"):
        app.config.intersphinx_disabled_domains = ["std"]  # type: ignore[attr-defined]

    __, branch, ___ = util.get_branch(app.srcdir)
    default = _format_mapping(
        _fetch_mapping(
            os.environ.get(
                "INTERSPHINX_REPOSITORY", DEFAULT_INTERSPHINX_REPOSITORY
            ),
            os.environ.get("INTERSPHINX_BRANCH", DEFAULT_INTERSPHINX_BRANCH),
        ),
        branch,
    )

    mapping: Dict[str, Any] = app.config.intersphinx_mapping
    for key, value in default.items():
        mapping.setdefault(key, value)
    print(app.config.intersphinx_mapping)


def setup(app: Sphinx) -> Dict[str, Any]:
    app.setup_extension("sphinx.ext.intersphinx")
    app.connect("config-inited", _update_config)
    return {"parallel_read_safe": True, "parallel_write_safe": True}
