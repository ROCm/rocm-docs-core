from __future__ import annotations

from typing import Any, Literal

import unittest.mock
from pathlib import Path

import pytest
from sphinx.errors import ExtensionError

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

    # Every project is available in the HTML templates and TOC, regardless of
    # the value of "external_projects"
    expected_context = {k: v.target for k, v in mocked_projects.items()}
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


@pytest.mark.usefixtures("_no_unexpected_warnings")
@pytest.mark.parametrize(
    "doxygen", ["doxygen/html", {"html": "doxygen/html"}], ids=["str", "dict"]
)
def test_doxygen_html_types(
    doxygen: str | dict[str, str],
) -> None:
    result = rocm_docs.projects._Project._get_doxygen_html({"doxygen": doxygen})  # type: ignore
    assert result == "doxygen/html"


@pytest.mark.usefixtures("_no_unexpected_warnings")
@pytest.mark.parametrize(
    "doxygen_html",
    ["https:", "//has_netloc", "has#fragment", "has?query", "/absolute"],
)
def test_doxygen_html_invalid(
    doxygen_html: str,
) -> None:
    with pytest.raises(ExtensionError):
        rocm_docs.projects._Project._get_doxygen_html({"doxygen": doxygen_html})


@pytest.mark.usefixtures("_no_unexpected_warnings")
@pytest.mark.parametrize(
    "current_project",
    [None, rocm_docs.projects._Project("", [], "", None)],
    ids=["no_current_project", "not_set"],
)
def test_set_doxygen_html_not_defined(
    current_project: rocm_docs.projects._Project | None,
) -> None:
    app = unittest.mock.NonCallableMock()
    app.config = unittest.mock.NonCallableMock()
    app.config.doxygen_html = "must-not-be-changed"
    rocm_docs.projects._set_doxygen_html(app, current_project)
    assert app.config.doxygen_html == "must-not-be-changed"


@pytest.mark.usefixtures("_no_unexpected_warnings")
def test_set_doxygen_html_mismatched(expect_log: ExpectLogFixture) -> None:
    app = create_app(Path(""), [])
    app.config.doxygen_html = "must-not-be-changed"
    app.config._raw_config["doxygen_html"] = "must-not-be-changed"
    with expect_log(
        "sphinx.rocm_docs.projects",
        "WARNING",
        'The setting doxygen_html="must-not-be-changed"'
        ' differs from projects.yaml value: "does-not-match"',
    ):
        rocm_docs.projects._set_doxygen_html(
            app, rocm_docs.projects._Project("", [], "", "does-not-match")
        )
    assert app.config.doxygen_html == "must-not-be-changed"
