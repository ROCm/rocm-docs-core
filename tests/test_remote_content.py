"""Tests for rocm_docs.remote_content -- the branch-aware remote-content directive.

The directive's transform logic (``:doc:`` conversion, doc_ignore/doc_remap,
replace/replace_re, CSV widths, LaTeX math, ref/version selection) is pure and
network-free, so these tests instantiate the directive with a stub Sphinx
environment and exercise the methods directly. The network paths
(fetch/fallback and image download) are covered with ``requests.get`` mocked so
they run deterministically offline.
"""

from __future__ import annotations

from typing import Any

import unittest.mock

import pytest
import requests

from rocm_docs.remote_content import (
    CONFIG_DOCS_BASE,
    DEFAULT_DOCS_BASE,
    BranchAwareRemoteContent,
)


def make_directive(
    options: dict[str, Any] | None = None,
    *,
    version: str = "",
    official_branch: Any = None,
    docs_base: str = DEFAULT_DOCS_BASE,
    srcdir: str = "/srcdir",
) -> BranchAwareRemoteContent:
    """Build a directive instance with a stub env, bypassing Directive.__init__.

    ``Directive.__init__`` needs the full RST state machine, which these unit
    tests do not exercise; the transform methods only touch ``self.options`` and
    ``self.state.document.settings.env``, so a stub env is enough.
    """
    directive = BranchAwareRemoteContent.__new__(BranchAwareRemoteContent)
    directive.options = options or {}

    env = unittest.mock.NonCallableMock()
    env.config.html_context = {"version": version}
    if official_branch is not None:
        env.config.html_context["official_branch"] = official_branch
    setattr(env.config, CONFIG_DOCS_BASE, docs_base)
    env.srcdir = srcdir

    state = unittest.mock.NonCallableMock()
    state.document.settings.env = env
    directive.state = state
    return directive


# --------------------------------------------------------------------------- #
# get_current_version / get_target_ref
# --------------------------------------------------------------------------- #


def test_current_version_none_when_not_version_shaped() -> None:
    d = make_directive(version="develop")
    assert d.get_current_version() is None


def test_current_version_release_via_official_branch() -> None:
    d = make_directive(version="7.14.0", official_branch=0)
    assert d.get_current_version() == "7.14.0"


def test_current_version_release_via_rtd_version_type() -> None:
    d = make_directive(version="7.14.0")
    with unittest.mock.patch.dict(
        "os.environ", {"READTHEDOCS_VERSION_TYPE": "tag"}, clear=True
    ):
        assert d.get_current_version() == "7.14.0"


def test_current_version_release_via_rtd_slug() -> None:
    d = make_directive(version="7.14.0")
    with unittest.mock.patch.dict(
        "os.environ", {"READTHEDOCS_VERSION": "docs-7.14.0"}, clear=True
    ):
        assert d.get_current_version() == "7.14.0"


def test_current_version_none_when_not_a_release() -> None:
    d = make_directive(version="7.14.0")
    with unittest.mock.patch.dict("os.environ", {}, clear=True):
        assert d.get_current_version() is None


def test_target_ref_uses_tag_prefix_on_release() -> None:
    d = make_directive(
        {"tag_prefix": "docs-"}, version="7.14.0", official_branch=0
    )
    assert d.get_target_ref() == "docs-7.14.0"


def test_target_ref_falls_back_to_default_branch() -> None:
    d = make_directive({"default_branch": "docs/develop"}, version="develop")
    assert d.get_target_ref() == "docs/develop"


def test_target_ref_none_without_default_branch() -> None:
    d = make_directive({}, version="develop")
    assert d.get_target_ref() is None


# --------------------------------------------------------------------------- #
# project name / base URL / doc URL construction
# --------------------------------------------------------------------------- #


def test_project_name_from_repo() -> None:
    assert make_directive({"repo": "ROCm/HIP"}).get_project_name() == "HIP"


def test_project_name_explicit_override() -> None:
    d = make_directive({"repo": "ROCm/HIP", "project_name": "Custom"})
    assert d.get_project_name() == "Custom"


def test_docs_base_url_uses_config_value() -> None:
    d = make_directive(docs_base="https://example.com/projects")
    assert d.get_docs_base_url() == "https://example.com/projects"


def test_docs_base_url_option_overrides_config() -> None:
    d = make_directive(
        {"docs_base_url": "https://override.example/projects"},
        docs_base="https://example.com/projects",
    )
    assert d.get_docs_base_url() == "https://override.example/projects"


def test_construct_doc_url_project_pattern() -> None:
    d = make_directive({"repo": "ROCm/HIP"})
    url = d.construct_doc_url("how-to/foo.rst", "docs-7.14.0")
    assert url == (f"{DEFAULT_DOCS_BASE}/HIP/en/docs-7.14.0/how-to/foo.html")


def test_construct_doc_url_rocm_special_case() -> None:
    d = make_directive({"repo": "ROCm/ROCm"})
    url = d.construct_doc_url("about/release-notes", "docs-7.14.0")
    assert url == (
        "https://rocm.docs.amd.com/en/docs-7.14.0/about/release-notes.html"
    )


# --------------------------------------------------------------------------- #
# resolve_relative_doc_path
# --------------------------------------------------------------------------- #


def test_resolve_relative_doc_path_absolute_unchanged() -> None:
    d = make_directive()
    assert d.resolve_relative_doc_path("how-to/foo", "docs/index.rst") == (
        "how-to/foo"
    )


def test_resolve_relative_doc_path_joins_against_source_dir() -> None:
    d = make_directive()
    # The path is joined against the source file's directory. `..` segments are
    # not collapsed here (Path() does not resolve them without resolve()); that
    # matches the canonical directive's behavior.
    resolved = d.resolve_relative_doc_path("../ref/bar", "docs/how-to/x.rst")
    assert resolved.replace("\\", "/") == "docs/how-to/../ref/bar"


# --------------------------------------------------------------------------- #
# :doc: role processing (ignore / remap / external conversion / namespaced)
# --------------------------------------------------------------------------- #


def test_doc_role_converted_to_external_link() -> None:
    d = make_directive({"repo": "ROCm/HIP", "path": "docs/index.rst"})
    out = d.process_doc_roles(":doc:`how-to/foo`", "docs-7.14.0")
    assert f"<{DEFAULT_DOCS_BASE}/HIP/en/docs-7.14.0/how-to/foo.html>`__" in out


def test_doc_role_with_display_text() -> None:
    d = make_directive({"repo": "ROCm/HIP", "path": "docs/index.rst"})
    out = d.process_doc_roles(":doc:`Foo Guide <how-to/foo>`", "docs-7.14.0")
    assert out.startswith("`Foo Guide <")
    assert out.endswith(">`__")


def test_doc_role_ignored_left_unconverted() -> None:
    d = make_directive(
        {
            "repo": "ROCm/HIP",
            "path": "docs/index.rst",
            "doc_ignore": "how-to/foo",
        }
    )
    src = ":doc:`how-to/foo`"
    assert d.process_doc_roles(src, "docs-7.14.0") == src


def test_doc_role_remapped_to_local_keep_text() -> None:
    d = make_directive(
        {
            "repo": "ROCm/HIP",
            "path": "docs/index.rst",
            "doc_remap": "install/guide|how-to/getting_started",
        }
    )
    out = d.process_doc_roles(":doc:`install/guide`", "docs-7.14.0")
    # Without an explicit new display text, the original target text is kept as
    # the display text, so the remapped role uses the "text <path>" form.
    assert out == ":doc:`install/guide <how-to/getting_started>`"


def test_doc_role_remapped_with_new_text() -> None:
    d = make_directive(
        {
            "repo": "ROCm/HIP",
            "path": "docs/index.rst",
            "doc_remap": "install/guide|Getting Started|how-to/getting_started",
        }
    )
    out = d.process_doc_roles(":doc:`install/guide`", "docs-7.14.0")
    assert out == ":doc:`Getting Started <how-to/getting_started>`"


def test_doc_role_namespaced_left_for_intersphinx() -> None:
    d = make_directive({"repo": "ROCm/HIP", "path": "docs/index.rst"})
    src = ":doc:`rocm:about/release-notes`"
    assert d.process_doc_roles(src, "docs-7.14.0") == src


# --------------------------------------------------------------------------- #
# replace / replace_re
# --------------------------------------------------------------------------- #


def test_apply_replacements_multiple() -> None:
    d = make_directive({"replace": "foo|bar;; baz|qux"})
    assert d.apply_replacements("foo and baz") == "bar and qux"


def test_apply_replacements_noop_without_option() -> None:
    d = make_directive({})
    assert d.apply_replacements("unchanged") == "unchanged"


def test_apply_regex_replacements_with_newline_escape() -> None:
    d = make_directive({"replace_re": r"a\s+b|A\nB"})
    assert d.apply_regex_replacements("a   b") == "A\nB"


def test_apply_regex_replacements_dotall_multiline() -> None:
    d = make_directive({"replace_re": r"START.*END|GONE"})
    assert d.apply_regex_replacements("START\nx\ny\nEND") == "GONE"


# --------------------------------------------------------------------------- #
# CSV widths / LaTeX math
# --------------------------------------------------------------------------- #


def test_csv_widths_injected_after_header() -> None:
    d = make_directive({"csv_widths": "33 67"})
    content = ".. csv-table::\n   :header: A, B\n\n   1, 2\n"
    out = d.process_csv_tables(content)
    assert ":widths: 33 67" in out
    # widths appears after the header option.
    assert out.index(":header:") < out.index(":widths:")


def test_csv_widths_not_duplicated() -> None:
    d = make_directive({"csv_widths": "33 67"})
    content = ".. csv-table::\n   :header: A, B\n   :widths: 10 90\n"
    out = d.process_csv_tables(content)
    assert out.count(":widths:") == 1
    assert ":widths: 10 90" in out


def test_latex_math_escapes_underscores_when_enabled() -> None:
    d = make_directive({"fix_latex_math": "true"})
    out = d.process_latex_math(r"\text{a_b_c}")
    assert out == r"\text{a\_b\_c}"


def test_latex_math_noop_when_disabled() -> None:
    d = make_directive({"fix_latex_math": "false"})
    assert d.process_latex_math(r"\text{a_b}") == r"\text{a_b}"


# --------------------------------------------------------------------------- #
# image path resolution (pure helper)
# --------------------------------------------------------------------------- #


def test_resolve_image_path_rocm_adds_docs_prefix() -> None:
    d = make_directive({"repo": "ROCm/ROCm", "path": "docs/how-to/x.rst"})
    # ../data/img.png from docs/how-to/ normalizes to docs/data/img.png
    assert d._resolve_image_path("../data/img.png") == "docs/data/img.png"


def test_resolve_image_path_rocm_systems_component_base() -> None:
    d = make_directive(
        {
            "repo": "ROCm/rocm-systems",
            "path": "projects/hip/docs/how-to/x.rst",
        }
    )
    out = d._resolve_image_path("../../data/img.png")
    assert out == "projects/hip/docs/data/img.png"


# --------------------------------------------------------------------------- #
# network paths (mocked)
# --------------------------------------------------------------------------- #


def _mock_response(text: str = "", status_ok: bool = True) -> Any:
    resp = unittest.mock.NonCallableMock()
    resp.text = text
    resp.content = text.encode()
    if status_ok:
        resp.raise_for_status.return_value = None
    else:
        resp.raise_for_status.side_effect = requests.exceptions.HTTPError("404")
    return resp


def test_run_fetches_and_parses(monkeypatch: pytest.MonkeyPatch) -> None:
    d = make_directive(
        {"repo": "ROCm/HIP", "path": "docs/index.rst"},
        version="7.14.0",
        official_branch=0,
    )
    captured: dict[str, str] = {}

    def fake_fetch(url: str, _source_path: str, ref: str) -> list[Any]:
        captured["url"] = url
        captured["ref"] = ref
        return ["PARSED"]

    monkeypatch.setattr(d, "fetch_and_parse_content", fake_fetch)
    result: list[Any] = d.run()
    assert result == ["PARSED"]
    assert captured["ref"] == "7.14.0"
    assert captured["url"] == (
        "https://raw.githubusercontent.com/ROCm/HIP/7.14.0/docs/index.rst"
    )


def test_run_falls_back_to_default_branch_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    d = make_directive(
        {
            "repo": "ROCm/HIP",
            "path": "docs/index.rst",
            "default_branch": "docs/develop",
        },
        version="7.14.0",
        official_branch=0,
    )
    calls: list[str] = []

    def fake_fetch(_url: str, _source_path: str, ref: str) -> list[Any]:
        calls.append(ref)
        if ref == "7.14.0":
            raise requests.exceptions.ConnectionError("boom")
        return ["FALLBACK"]

    monkeypatch.setattr(d, "fetch_and_parse_content", fake_fetch)
    result: list[Any] = d.run()
    assert result == ["FALLBACK"]
    # First the tag, then the fallback branch.
    assert calls == ["7.14.0", "docs/develop"]


def test_run_returns_empty_without_repo_or_path() -> None:
    assert make_directive({"repo": "ROCm/HIP"}).run() == []
    assert make_directive({"path": "docs/index.rst"}).run() == []


def test_download_image_writes_file(tmp_path: Any) -> None:
    d = make_directive(
        {"repo": "ROCm/HIP", "path": "docs/index.rst"},
        srcdir=str(tmp_path),
    )
    with unittest.mock.patch(
        "requests.get", return_value=_mock_response("PNGDATA")
    ):
        local = d.download_image("docs/data/img.png", "7.14.0")
    assert local is not None
    assert local.read_bytes() == b"PNGDATA"


def test_download_image_returns_none_on_failure(tmp_path: Any) -> None:
    d = make_directive(
        {"repo": "ROCm/HIP", "path": "docs/index.rst"},
        srcdir=str(tmp_path),
    )
    with unittest.mock.patch(
        "requests.get",
        side_effect=requests.exceptions.ConnectionError("no net"),
    ):
        assert d.download_image("docs/data/img.png", "7.14.0") is None


def test_setup_registers_directive_and_config() -> None:
    from rocm_docs.remote_content import setup

    app = unittest.mock.NonCallableMock()
    meta = setup(app)
    app.add_directive.assert_called_once_with(
        "remote-content", BranchAwareRemoteContent
    )
    app.add_config_value.assert_called_once()
    assert app.add_config_value.call_args.args[0] == CONFIG_DOCS_BASE
    assert meta["parallel_read_safe"] is True
    assert meta["parallel_write_safe"] is True
