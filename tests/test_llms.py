"""Tests for rocm_docs.llms -- llms.txt / llms-full.txt generation.

These tests run a real Sphinx build of the ``llms`` fixture site (which mixes
RST and Markdown sources) and assert on the generated files, so they exercise
the full doctree -> Markdown pipeline rather than mocking it.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from .log_fixtures import ExpectLogFixture
from .sphinx_fixtures import build_sphinx

BASE_URL = "https://example.com/docs"


@pytest.fixture
def llms_build(
    build_factory: Callable[..., tuple[Path, Path]],
    with_no_git_repo: ExpectLogFixture.Validator,
) -> tuple[str, str]:
    """Build the ``llms`` fixture site and return (llms.txt, llms-full.txt)."""
    with_no_git_repo.required = False
    srcdir, outdir = build_factory("llms")
    build_sphinx(srcdir, outdir)
    index = (outdir / "llms.txt").read_text(encoding="utf-8")
    full = (outdir / "llms-full.txt").read_text(encoding="utf-8")
    return index, full


def test_both_files_written_and_newline_terminated(
    llms_build: tuple[str, str],
) -> None:
    index, full = llms_build
    assert index.endswith("\n")
    assert full.endswith("\n")


def test_index_has_title_and_summary(llms_build: tuple[str, str]) -> None:
    index, _ = llms_build
    assert index.startswith("# LLMs Test Project")
    # Summary blockquote comes from the root page's MyST html_meta description.
    assert "> Root page of the LLMs test project." in index


def test_index_lists_pages_in_toc_order(llms_build: tuple[str, str]) -> None:
    index, _ = llms_build
    rst_pos = index.find("page_rst.html")
    md_pos = index.find("page_md.html")
    assert rst_pos != -1
    assert md_pos != -1
    # _toc.yml.in declares page_rst before page_md.
    assert rst_pos < md_pos


def test_index_descriptions_from_both_source_formats(
    llms_build: tuple[str, str],
) -> None:
    index, _ = llms_build
    # RST description comes from a `.. meta::` directive.
    assert (
        f"[RST page]({BASE_URL}/page_rst.html): "
        "An RST page with a list-table, code block, and cross-reference."
    ) in index
    # Markdown description comes from MyST html_meta.
    assert (
        f"[Markdown page]({BASE_URL}/page_md.html): "
        "A Markdown page with a code block and a table."
    ) in index


def test_rst_list_table_becomes_markdown_table(
    llms_build: tuple[str, str],
) -> None:
    _, full = llms_build
    # The RST list-table (previously mangled) must become a real Markdown
    # table: a header separator row plus every cell.
    assert "| Feature" in full
    assert "| --" in full or "|--" in full
    for cell in ("Atomics", "Wavefront size", "Yes", "32", "64"):
        assert cell in full


def test_rst_code_block_is_fenced_with_language(
    llms_build: tuple[str, str],
) -> None:
    _, full = llms_build
    assert "```cpp" in full
    assert "__global__ void rst_kernel" in full


def test_cross_reference_rewritten_to_absolute_url(
    llms_build: tuple[str, str],
) -> None:
    _, full = llms_build
    # The RST page's :doc:`page_md` xref must resolve to an absolute HTML URL.
    assert f"({BASE_URL}/page_md.html" in full


def test_doxygen_page_excluded_from_fulltext(
    llms_build: tuple[str, str],
) -> None:
    index, full = llms_build
    assert "Generated API reference" not in full
    assert "doxygen/generated" not in index


def test_no_meta_warning(
    build_factory: Callable[..., tuple[Path, Path]],
    with_no_git_repo: ExpectLogFixture.Validator,
    expect_log: ExpectLogFixture,
) -> None:
    """meta nodes are stripped, so no 'unknown node type' warning is emitted."""
    with_no_git_repo.required = False
    srcdir, outdir = build_factory("llms")
    with expect_log(
        "sphinx.sphinx_markdown_builder.translator",
        "WARNING",
        "unknown node type: <meta: >",
        required=False,
    ) as meta_warning:
        build_sphinx(srcdir, outdir)
    assert not meta_warning.found


def test_no_files_written_on_build_failure(tmp_path: Path) -> None:
    """generate_llms_full is a no-op when the build raised an exception."""
    import unittest.mock

    from rocm_docs.llms import generate_llms_full

    app = unittest.mock.NonCallableMock()
    app.outdir = str(tmp_path)
    generate_llms_full(app, exception=RuntimeError("build failed"))
    assert not (tmp_path / "llms.txt").exists()
    assert not (tmp_path / "llms-full.txt").exists()
