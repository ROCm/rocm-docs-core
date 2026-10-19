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
        "external_projects_inventory_url": "",
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


@pytest.mark.usefixtures("_no_unexpected_warnings")
def test_private_inventory_url(
    mocked_projects: dict[str, rocm_docs.projects._Project],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    with_no_git_repo: ExpectLogFixture.Validator,
) -> None:
    with_no_git_repo.required = False
    monkeypatch.setenv("RTD_TOKEN_A", "secret-a")
    monkeypatch.setenv("RTD_TOKEN_B", "secret-b")
    app = create_app(tmp_path, "all")
    app.config.external_projects_inventory_url = (
        "https://{token}:@private.example.com/{project}/{path}/objects.inv"
    )
    rocm_docs.projects._update_config(app, app.config)

    # Targets are unchanged, inventories come from the private location with
    # the public location as a fallback.
    assert app.config.intersphinx_mapping == {
        k: (
            v.target,
            (
                f"https://secret-{k}:@private.example.com/{k}/{k}/objects.inv",
                None,
            ),
        )
        for k, v in mocked_projects.items()
    }


def test_private_inventory_token_env_name() -> None:
    assert rocm_docs.projects._inventory_token_env("docs") == "RTD_TOKEN_DOCS"
    assert (
        rocm_docs.projects._inventory_token_env("hip-python")
        == "RTD_TOKEN_HIP_PYTHON"
    )


def test_private_inventory_url_missing_token(
    expect_log: ExpectLogFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("RTD_TOKEN_A", raising=False)
    mapping: dict[str, rocm_docs.projects.ProjectMapping] = {
        "a": ("https://example.com/a", (None,)),
    }
    with expect_log(
        "sphinx.rocm_docs.projects",
        "WARNING",
        "RTD_TOKEN_A is not set, using the public inventory of project 'a'.",
    ):
        result = rocm_docs.projects._use_private_inventories(
            "https://{token}:@private.example.com/{path}/objects.inv", mapping
        )
    assert result == mapping


@pytest.mark.usefixtures("_no_unexpected_warnings")
def test_private_inventory_url_keeps_explicit_inventory() -> None:
    mapping: dict[str, rocm_docs.projects.ProjectMapping] = {
        "a": ("https://example.com/a", ("objects-a.inv",)),
        "b": ("https://example.com/b", (None,)),
    }
    result = rocm_docs.projects._use_private_inventories(
        "https://private.example.com/{path}/objects.inv", mapping
    )
    assert result["a"] == mapping["a"]
    assert result["b"] == (
        "https://example.com/b",
        ("https://private.example.com/b/objects.inv", None),
    )


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
    [None, rocm_docs.projects._Project("", [], "", [], None)],
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
            app, rocm_docs.projects._Project("", [], "", [], "does-not-match")
        )
    assert app.config.doxygen_html == "must-not-be-changed"


@pytest.mark.parametrize(
    ("current_branch", "expected"),
    [
        ("latest", "latest"),
        ("stable", "stable"),
        ("docs-7.2.0", "docs-7.2.0"),
        ("7.13.0-preview", "7.13.0-preview"),
        ("8.0.0-preview", "8.0.0-preview"),
        ("some-feature-branch", "latest"),
    ],
)
def test_get_static_version(current_branch: str, expected: str) -> None:
    assert (
        rocm_docs.projects._Project.get_static_version(current_branch, None)
        == expected
    )
