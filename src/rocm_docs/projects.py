"""Handle external projects.

Remote loading of intersphinx_mapping from file, templating projects in toc.yml).
"""

from typing import Any, Dict, List, Optional, Tuple, Union, cast

import functools
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import fastjsonschema  # type: ignore[import]
import github
import sphinx.util.logging
import yaml
from pydata_sphinx_theme.utils import config_provided_by_user  # type: ignore[import]
from sphinx.application import Sphinx
from sphinx.config import Config

from rocm_docs import formatting, util

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


class InvalidMappingFileError(RuntimeError):
    """Mapping file has invalid format, or failed to validate."""


ProjectItem = Union[str, None, List[Union[str, None]]]
ProjectEntry = Union[str, Dict[str, ProjectItem]]


@dataclass
class _Project:
    target: str
    inventory: List[Union[str, None]]
    development_branch: str

    @staticmethod
    @functools.lru_cache
    def yaml_schema() -> Dict[str, Any]:
        base = importlib_resources.files("rocm_docs") / "data"
        schema_file = base / "projects.schema.json"

        return cast(
            Dict[str, Any], json.load(schema_file.open(encoding="utf-8"))
        )

    @classmethod
    def schema(cls) -> Dict[str, Any]:
        return cast(Dict[str, Any], cls.yaml_schema()["$defs"]["project"])

    @classmethod
    def default_value(cls, prop: str) -> str:
        return cast(str, cls.schema()["properties"][prop]["default"])

    @classmethod
    def from_yaml_entry(cls, entry: ProjectEntry) -> "_Project":
        """Create from an entry that conforms to the project schema."""
        if isinstance(entry, str):
            return _Project(
                entry,
                [cls.default_value("inventory")],
                cls.default_value("development_branch"),
            )

        # It's okay to just index into optional fields, because jsonschema
        # fills in any missing fields with their default values
        inventory = entry["inventory"]
        if not isinstance(inventory, list):
            inventory = [inventory]

        return _Project(
            cast(str, entry["target"]),
            inventory,
            cast(str, entry["development_branch"]),
        )

    @classmethod
    def get_static_version(
        cls,
        current_branch: str,
        current_project: Optional["_Project"],
    ) -> Optional[str]:
        """Returns a common static version if it exists.

        In some cases all remote projects will receive the same version,
        return that version if this is the case, returns None otherwise.
        """
        # Canonically available everywhere
        if current_branch in ["latest", "stable"]:
            return current_branch

        # Past release versions always with docs/
        if current_branch.startswith("docs-"):
            return current_branch

        # Anything besides the canonical development branch links to latest docs
        development_branch: str = cls.default_value("development_branch")
        if current_project is not None:
            development_branch = current_project.development_branch

        if current_branch != development_branch:
            return "latest"

        return None

    def evaluate(self, static_version: Optional[str]) -> None:
        """Evaluate ${version} placeholders in the inventory and target values."""
        version = (
            static_version
            if static_version is not None
            else self.development_branch
        )
        self.target = self.target.replace("${version}", version)
        for item in self.inventory:
            if item is None:
                continue
            item = item.replace("${version}", version)

    @property
    def mapping(self) -> ProjectMapping:
        """Target and inventory location in the format expected by sphinx."""
        return (self.target, tuple(self.inventory))


def _create_projects(
    project_yaml: Union[str, Traversable]
) -> Dict[str, _Project]:
    contents = yaml.safe_load(
        project_yaml
        if isinstance(project_yaml, str)
        else project_yaml.open(encoding="utf-8")
    )

    data: Dict[str, Union[int, Dict[str, ProjectEntry]]]
    try:
        data = fastjsonschema.validate(_Project.yaml_schema(), contents)
    except fastjsonschema.exceptions.JsonSchemaValueException as err:
        raise InvalidMappingFileError(
            f"Mapping file is invalid: {err.message}."
        ) from err

    assert isinstance(data["projects"], dict)
    return {
        project_id: _Project.from_yaml_entry(entry)
        for project_id, entry in data["projects"].items()
    }


def _get_current_project(
    projects: Dict[str, _Project], current_id: str
) -> Optional[_Project]:
    if current_id in projects:
        return projects[current_id]

    logger.warning(
        f"Current project '{current_id}' not found in projects.\n"
        "Did you forget to set 'external_projects_current_project' to "
        "the name of the current project?"
    )
    return None


def _create_mapping(
    projects: Dict[str, _Project],
    current_project: Optional[_Project],
    current_branch: str,
) -> Dict[str, ProjectMapping]:
    static_version = _Project.get_static_version(
        current_branch, current_project
    )
    for project in projects.values():
        project.evaluate(static_version)

    return {name: project.mapping for name, project in projects.items()}


class MappingFileFetchError(RuntimeError):
    """Fetching the yaml file from the remote failed."""


def _fetch_projects(
    remote_repository: str,
    remote_branch: str,
    remote_filepath: str,
) -> str:
    try:
        gh_api = github.Github(os.environ.get("TOKEN"))
        repo = gh_api.get_repo(remote_repository)
        contents = repo.get_contents(remote_filepath, remote_branch)
        if isinstance(contents, list):
            raise MappingFileFetchError("Expected a file not a directory!")

        return contents.decoded_content.decode("utf-8")
    except github.GithubException as err:
        assert isinstance(err.data["message"], str)
        message: str = err.data["message"]
        raise MappingFileFetchError(
            "failed to read remote mappings from "
            f"{remote_repository}:{remote_filepath} "
            f"on branch={remote_branch}, API returned {err.status}: {message}.",
        ) from err


def _load_projects(
    remote_repository: str, remote_branch: str
) -> Dict[str, _Project]:
    projects_file_loc = "data/projects.yaml"

    def should_fetch_mappings(
        remote_repository: Optional[str], remote_branch: Optional[str]
    ) -> bool:
        if not remote_repository:
            logger.info(
                "Skipping the fetch for remote mappings, remote_repository "
                "is unset."
            )
            return False

        if not remote_branch:
            logger.error(
                "Remote branch is unset, cannot fetch remote mappings."
            )
            return False

        logger.info(
            "Remote mappings will be fetched from "
            f"{remote_repository} branch={remote_branch}"
        )
        return True

    projects: Optional[Dict[str, _Project]] = None
    if should_fetch_mappings(remote_repository, remote_branch):
        try:
            remote_filepath = "src/rocm_docs/" + projects_file_loc
            projects = _create_projects(
                _fetch_projects(
                    remote_repository,
                    remote_branch,
                    remote_filepath,
                )
            )
        except (MappingFileFetchError, InvalidMappingFileError) as err:
            logger.warning(
                f"Failed to use remote mapping: {err} "
                "Falling back to bundled mapping."
            )

    if projects is None:
        projects = _create_projects(
            importlib_resources.files("rocm_docs") / projects_file_loc
        )

    return projects


def _get_context(
    repo_path: Path, mapping: Dict[str, ProjectMapping]
) -> Dict[str, Any]:
    url, branch = util.get_branch(repo_path)
    return {
        "url": url,
        "branch": branch,
        "projects": {k: v[0].rstrip("/") for k, v in mapping.items()},
    }


def _update_theme_configs(
    app: Sphinx, current_project: Optional[_Project], current_branch: str
) -> None:
    """Update configurations for use in theme.py"""
    latest_version = "5.6.0"
    latest_version_string = f"docs-{latest_version}"
    release_candidate = "5.7"
    release_candidate_string = f"docs-{release_candidate}"

    development_branch = _Project.default_value("development_branch")
    if current_project is not None:
        development_branch = current_project.development_branch

    if current_branch in [latest_version_string, "latest"]:
        app.config.projects_version_type = util.VersionType.LATEST_RELEASE  # type: ignore[attr-defined]
    elif current_branch.startswith(release_candidate_string):
        app.config.projects_version_type = util.VersionType.RELEASE_CANDIDATE  # type: ignore[attr-defined]
    elif current_branch.startswith("docs-"):
        app.config.projects_version_type = util.VersionType.OLD_RELEASE  # type: ignore[attr-defined]
    elif current_branch == development_branch:
        app.config.projects_version_type = util.VersionType.DEVELOPMENT  # type: ignore[attr-defined]


def _update_config(app: Sphinx, _: Config) -> None:
    if not config_provided_by_user(app, "intersphinx_disabled_domains"):
        app.config.intersphinx_disabled_domains = ["std"]  # type: ignore[attr-defined]

    remote_repository = app.config.external_projects_remote_repository
    remote_branch = app.config.external_projects_remote_branch
    projects = _load_projects(remote_repository, remote_branch)

    repo_path = Path(app.srcdir)
    __, branch = util.get_branch(repo_path)
    current_project = _get_current_project(
        projects, app.config.external_projects_current_project
    )
    default = _create_mapping(projects, current_project, branch)

    mapping: Dict[str, ProjectMapping] = app.config.intersphinx_mapping
    for key, value in default.items():
        mapping.setdefault(key, value)

    if not config_provided_by_user(app, "external_toc_path"):
        app.config.external_toc_path = "./.sphinx/_toc.yml"  # type: ignore[attr-defined]

    context = _get_context(Path(app.srcdir), mapping)
    formatting.format_toc(
        Path(app.srcdir, app.config.external_toc_template_path),
        Path(app.srcdir, app.config.external_toc_path),
        context,
    )
    # Store the context to be referenced later
    app.config.projects_context = context  # type: ignore[attr-defined]

    _update_theme_configs(app, current_project, branch)


def _setup_projects_context(
    app: Sphinx, _: str, __: str, context: Dict[str, Any], ___: Any
) -> None:
    context["projects"] = app.config.projects_context["projects"]


def setup(app: Sphinx) -> Dict[str, Any]:
    """Setup rocm_docs.projects as a sphinx extension."""
    app.setup_extension("sphinx.ext.intersphinx")
    app.setup_extension("sphinx_external_toc")

    app.add_config_value(
        "external_projects_remote_repository",
        DEFAULT_INTERSPHINX_REPOSITORY,
        rebuild="env",
        types=str,
    )
    app.add_config_value(
        "external_projects_remote_branch",
        DEFAULT_INTERSPHINX_BRANCH,
        rebuild="env",
        types=str,
    )
    app.add_config_value(
        "external_projects_current_project",
        lambda config: config.project,
        rebuild="env",
        types=str,
    )

    def external_toc_template_default(config: Config) -> str:
        toc_path = Path(config.external_toc_path)
        return str(toc_path.with_suffix(toc_path.suffix + ".in"))

    app.add_config_value(
        "external_toc_template_path",
        external_toc_template_default,
        rebuild="env",
        types=[str, Path],
    )

    # This needs to happen before external-tocs's config-inited (priority=900)
    app.connect("config-inited", _update_config)
    app.connect("html-page-context", _setup_projects_context)
    return {"parallel_read_safe": True, "parallel_write_safe": True}


def debug_projects() -> None:
    """Get remote mappings display them and format the toc.

    Provided as a debugging tool for the functionality of this module.
    """
    projects = _load_projects(
        DEFAULT_INTERSPHINX_REPOSITORY, DEFAULT_INTERSPHINX_BRANCH
    )
    print(projects)

    current_project = _get_current_project(projects, "rocm-docs-core")
    print(current_project)

    repo_path = Path()
    _, branch = util.get_branch(repo_path)
    mapping = _create_mapping(projects, current_project, branch)
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
        context,
    )


if __name__ == "__main__":
    debug_projects()
