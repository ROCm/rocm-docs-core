from __future__ import annotations

from typing import Any, Literal

import unittest.mock
from pathlib import Path

import pytest

import rocm_docs.projects

from .log_fixtures import ExpectLogFixture
from .sphinx_fixtures import SITES_BASEFOLDER

TEMPLATE_FOLDER = SITES_BASEFOLDER / "templates"


def str_or_list_to_id(val: str | list[str]) -> str:
    if isinstance(val, str):
        return val
    return ",".join(val)


def create_app(
    srcdir: Path, external_projects: Any
) -> unittest.mock.NonCallableMock:
    app = unittest.mock.NonCallableMock()
    app.srcdir = srcdir
    app.config = unittest.mock.NonCallableMock()
    app.config.overrides = []
    app.config._raw_config = {
        "external_projects_current_project": "a",
        "external_projects": external_projects,
        "external_toc_template_path": TEMPLATE_FOLDER
        / "minimal"
        / ".sphinx"
        / "_toc.yml.in",
        "external_toc_path": "_toc.yml",
        "intersphinx_mapping": {},
    }
    app.config.configure_mock(**app.config._raw_config)
    return app


@pytest.mark.parametrize(
    "external_projects",
    [[], ["a"], ["b"], ["a", "b"], "all"],
    ids=str_or_list_to_id,
)
@pytest.mark.usefixtures("_no_unexpected_warnings")
def test_external_projects(
    external_projects: list[str] | Literal["all"],
    mocked_projects: dict[str, rocm_docs.projects._Project],
    tmp_path: Path,
    with_no_git_repo: ExpectLogFixture.Validator,
) -> None:
    with_no_git_repo.required = False
    app = create_app(tmp_path, external_projects)
    rocm_docs.projects._update_config(app, app.config)

    keys = (
        external_projects
        if external_projects != "all"
        else mocked_projects.keys()
    )

    expected_mapping = {
        k: (v.target, tuple(v.inventory))
        for k, v in mocked_projects.items()
        if k in keys
    }
    assert app.config.intersphinx_mapping == expected_mapping

    expected_context = {
        k: v.target for k, v in mocked_projects.items() if k in keys
    }
    assert app.config.projects_context["projects"] == expected_context


@pytest.mark.usefixtures("mocked_projects", "_no_unexpected_warnings")
def test_external_projects_invalid_value(
    expect_log: ExpectLogFixture,
    with_no_git_repo: ExpectLogFixture.Validator,
    tmp_path: Path,
) -> None:
    with_no_git_repo.required = False
    app = create_app(tmp_path, "invalid_value")

    with expect_log(
        "sphinx.rocm_docs.projects",
        "ERROR",
        'Unexpected value "invalid_value" in external_projects.\n'
        'Must be set to a list of project names or "all" to enable all projects'
        " defined in projects.yaml",
    ):
        rocm_docs.projects._update_config(app, app.config)


@pytest.mark.usefixtures("_no_unexpected_warnings")
def test_external_projects_unknown_project(
    expect_log: ExpectLogFixture,
    mocked_projects: dict[str, rocm_docs.projects._Project],
    with_no_git_repo: ExpectLogFixture.Validator,
    tmp_path: Path,
) -> None:
    with_no_git_repo.required = False
    # First keys of mocked_projects
    a_defined_project = next(iter(mocked_projects.keys()))
    app = create_app(tmp_path, [a_defined_project, "unknown_project", "foo"])

    with expect_log(
        "sphinx.rocm_docs.projects",
        "ERROR",
        'Unknown projects: ["unknown_project", "foo"] in external_projects.\n'
        "Valid projects are: [{}]".format(
            ", ".join([f'"{p}"' for p in mocked_projects])
        ),
    ):
        rocm_docs.projects._update_config(app, app.config)
