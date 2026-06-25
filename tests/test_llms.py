"""Tests for rocm_docs.llms -- llms.txt / llms-full.txt generation.

These tests run a real Sphinx build of the ``llms`` fixture site (which mixes
RST and Markdown sources) and assert on the generated files, so they exercise
the full doctree -> Markdown pipeline rather than mocking it.
"""

from __future__ import annotations

import dataclasses
import logging
import shutil
import unittest.mock
from pathlib import Path

import pytest

from .sphinx_fixtures import SITES_BASEFOLDER, build_sphinx

BASE_URL = "https://example.com/docs"


@dataclasses.dataclass
class _LlmsBuild:
    """Results of a single build of the ``llms`` fixture site."""

    index: str
    full: str
    warnings: list[str]


class _RecordingHandler(logging.Handler):
    """Logging handler that collects emitted records in a list."""

    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


@pytest.fixture(scope="module")
def llms_build(
    tmp_path_factory: pytest.TempPathFactory,
) -> _LlmsBuild:
    """Build the ``llms`` fixture site once and return its generated files.

    Module-scoped so the (relatively expensive) Sphinx build runs a single time
    for all of the read-only assertions below. The fixture site's ``conf.py``
    disables remote project/intersphinx fetching to keep the build offline.
    Warnings from the Markdown translator are captured so tests can assert that
    none were emitted without triggering a second build.
    """
    srcdir = tmp_path_factory.mktemp("llms")
    outdir = tmp_path_factory.mktemp("llms_build")
    shutil.copytree(SITES_BASEFOLDER / "llms", srcdir, dirs_exist_ok=True)

    handler = _RecordingHandler()
    translator_log = logging.getLogger(
        "sphinx.sphinx_markdown_builder.translator"
    )
    translator_log.addHandler(handler)

    # Allow building outside a git repository (mirrors the with_no_git_repo
    # fixture) without pulling in function-scoped fixtures.
    try:
        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setenv("ROCM_DOCS_REMOTE_DETAILS", ",")
            # Sphinx's logging.setup() reconfigures global logging handlers,
            # which would corrupt log capture in other test modules. Disable it
            # for this build, exactly as the _with_sphinx_logs fixture does.
            monkeypatch.setattr(
                "sphinx.util.logging.setup", unittest.mock.Mock()
            )
            build_sphinx(srcdir, outdir)
    finally:
        translator_log.removeHandler(handler)

    return _LlmsBuild(
        index=(outdir / "llms.txt").read_text(encoding="utf-8"),
        full=(outdir / "llms-full.txt").read_text(encoding="utf-8"),
        warnings=[r.getMessage() for r in handler.records],
    )


def test_both_files_written_and_newline_terminated(
    llms_build: _LlmsBuild,
) -> None:
    assert llms_build.index.endswith("\n")
    assert llms_build.full.endswith("\n")


def test_index_has_title_and_summary(llms_build: _LlmsBuild) -> None:
    assert llms_build.index.startswith("# LLMs Test Project")
    # Summary blockquote comes from the root page's MyST html_meta description.
    assert "> Root page of the LLMs test project." in llms_build.index


def test_index_notes_multiple_llms_files(llms_build: _LlmsBuild) -> None:
    # Every llms.txt notes that each project publishes its own llms files.
    assert "split across multiple projects" in llms_build.index
    assert "projects/<project_name>/en/latest/" in llms_build.index


def test_index_lists_pages_in_toc_order(llms_build: _LlmsBuild) -> None:
    index = llms_build.index
    rst_pos = index.find("page_rst.html")
    md_pos = index.find("page_md.html")
    assert rst_pos != -1
    assert md_pos != -1
    # _toc.yml.in declares page_rst before page_md.
    assert rst_pos < md_pos


def test_index_descriptions_from_both_source_formats(
    llms_build: _LlmsBuild,
) -> None:
    # RST description comes from a `.. meta::` directive.
    assert (
        f"[RST page]({BASE_URL}/page_rst.html): "
        "An RST page with a list-table, code block, and cross-reference."
    ) in llms_build.index
    # Markdown description comes from MyST html_meta.
    assert (
        f"[Markdown page]({BASE_URL}/page_md.html): "
        "A Markdown page with a code block and a table."
    ) in llms_build.index


def test_rst_list_table_becomes_markdown_table(
    llms_build: _LlmsBuild,
) -> None:
    full = llms_build.full
    # The RST list-table (previously mangled) must become a real Markdown
    # table: a header separator row plus every cell.
    assert "| Feature" in full
    assert "| --" in full or "|--" in full
    for cell in ("Atomics", "Wavefront size", "Yes", "32", "64"):
        assert cell in full


def test_code_blocks_are_fenced_with_language(
    llms_build: _LlmsBuild,
) -> None:
    full = llms_build.full
    # RST code-block, Markdown fenced block, and a second-language RST block.
    assert "```cpp" in full
    assert "```bash" in full
    assert "__global__ void rst_kernel" in full
    assert "__global__ void md_kernel" in full
    assert "export HIP_VISIBLE_DEVICES=0" in full


def test_inline_constructs_preserved(llms_build: _LlmsBuild) -> None:
    full = llms_build.full
    # Inline literals from both RST (``hipFree``) and Markdown (`hipMalloc`).
    assert "`hipFree`" in full
    assert "`hipMalloc`" in full
    # Inline math and a nested list bullet from the Markdown page.
    assert "$a^2 + b^2 = c^2$" in full
    assert "Nested item" in full
    # A Markdown link renders with its target.
    assert "[external link](https://rocm.docs.amd.com)" in full


def test_cross_reference_rewritten_to_absolute_url(
    llms_build: _LlmsBuild,
) -> None:
    # The RST page's :doc:`page_md` xref must resolve to an absolute HTML URL.
    assert f"({BASE_URL}/page_md.html" in llms_build.full


def test_supported_and_unsupported_admonitions_preserved(
    llms_build: _LlmsBuild,
) -> None:
    full = llms_build.full
    # A supported `.. note::` renders normally.
    assert "Supported note body text that must be rendered." in full
    # `.. tip::` has no Markdown-builder visitor; its body must still be
    # preserved (converted to a note) rather than dropped.
    assert "Unique tip body text that must survive conversion." in full


def test_tab_labels_preserved_as_bold(llms_build: _LlmsBuild) -> None:
    full = llms_build.full
    # Tab labels (sd_tab_label) have no Markdown-builder visitor; they must be
    # rendered as bold text so platform-specific tabs are not conflated, while
    # the tab bodies are also kept.
    assert "**AMD**" in full
    assert "**NVIDIA**" in full
    assert "Use `amdclang++` on AMD platforms." in full
    assert "Use `nvcc` on NVIDIA platforms." in full


def test_doxygen_page_indexed_but_not_inlined(
    llms_build: _LlmsBuild,
) -> None:
    # The page lives under a nested ``.../doxygen/html/`` segment. Its body must
    # not be inlined into the full text (no body prose, no Source: section)...
    assert "stands in for generated doxygen" not in llms_build.full
    assert "Source: " + BASE_URL + "/api/doxygen/html/generated.html" not in (
        llms_build.full
    )
    # ...but it must still be listed as a link in the index.
    assert (
        f"[Generated API reference]({BASE_URL}/api/doxygen/html/generated.html)"
        in llms_build.index
    )


def test_full_exclude_keeps_page_in_index_only(
    llms_build: _LlmsBuild,
) -> None:
    """A page in rocm_docs_llms_full_exclude is indexed but not inlined."""
    # The excluded page is still listed in the index...
    assert f"[Excluded page]({BASE_URL}/excluded_page.html)" in (
        llms_build.index
    )
    # ...but its body is not inlined into the full text.
    assert "UNIQUE_EXCLUDED_BODY_MARKER" not in llms_build.full
    assert "excluded_kernel" not in llms_build.full


def test_no_meta_warning(llms_build: _LlmsBuild) -> None:
    """meta nodes are stripped, so no 'unknown node type' warning is emitted."""
    assert not any("<meta" in msg for msg in llms_build.warnings)


def test_no_files_written_on_build_failure(tmp_path: Path) -> None:
    """generate_llms_full is a no-op when the build raised an exception."""
    import unittest.mock

    from rocm_docs.llms import generate_llms_full

    app = unittest.mock.NonCallableMock()
    app.outdir = str(tmp_path)
    app.builder.format = "html"
    generate_llms_full(app, exception=RuntimeError("build failed"))
    assert not (tmp_path / "llms.txt").exists()
    assert not (tmp_path / "llms-full.txt").exists()


def test_no_files_written_for_non_html_builder(tmp_path: Path) -> None:
    """generate_llms_full is a no-op under non-HTML builders (linkcheck, etc.)."""
    import unittest.mock

    from rocm_docs.llms import generate_llms_full

    app = unittest.mock.NonCallableMock()
    app.outdir = str(tmp_path)
    app.builder.format = "text"  # e.g. linkcheck/gettext have non-"html" format
    generate_llms_full(app, exception=None)
    assert not (tmp_path / "llms.txt").exists()
    assert not (tmp_path / "llms-full.txt").exists()


def test_unknown_node_warning_downgraded_to_info() -> None:
    """The filter lowers 'unknown node type' warnings to INFO, leaving others."""
    import logging

    from rocm_docs.llms import _DowngradeUnknownNodeFilter

    flt = _DowngradeUnknownNodeFilter()

    def _record(msg: str) -> logging.LogRecord:
        return logging.LogRecord(
            "x", logging.WARNING, __file__, 0, msg, None, None
        )

    unknown = _record("unknown node type: <mermaid: ...>")
    assert flt.filter(unknown) is True
    assert unknown.levelno == logging.INFO
    assert unknown.levelname == "INFO"

    # An unrelated warning is left untouched.
    other = _record("some other warning")
    assert flt.filter(other) is True
    assert other.levelno == logging.WARNING
