from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import rocm_docs.doxygen_toc_expander as mod

pytest.importorskip("yaml")
import yaml


def _write_group_html(doxygen_html: Path) -> None:
    """A group page that references two structs and one file page."""
    (doxygen_html / "group__widgets.html").write_text(
        '<a href="structWidget.html">Widget</a>'
        '<a href="structGadget.html">Gadget</a>'
        '<a href="widget__impl_8h.html">widget_impl.h</a>',
        encoding="utf-8",
    )
    (doxygen_html / "annotated.html").write_text(
        '<a href="structWidget.html">Widget</a>', encoding="utf-8"
    )
    (doxygen_html / "files.html").write_text(
        '<a href="widget__impl_8h.html">widget_impl.h</a>', encoding="utf-8"
    )


@pytest.fixture
def doxygen_html(tmp_path: Path) -> Path:
    d = tmp_path / "docBin" / "html"
    d.mkdir(parents=True)
    _write_group_html(d)
    return d


def _toc_template(tmp_path: Path) -> Path:
    template = tmp_path / "_toc.yml.in"
    template.write_text(
        "# a comment header\n"
        "root: index\n"
        "subtrees:\n"
        "- entries:\n"
        "  - file: doxygen/html/group__widgets\n"
        "  - file: doxygen/html/annotated\n"
        "  - file: doxygen/html/files\n",
        encoding="utf-8",
    )
    return template


def test_do_expansion_writes_output_not_source(
    tmp_path: Path, doxygen_html: Path
) -> None:
    template = _toc_template(tmp_path)
    original = template.read_text(encoding="utf-8")
    output = tmp_path / "gen" / "_toc.yml.in"
    output.parent.mkdir()

    result = mod._do_expansion(
        template, output, doxygen_html, SimpleNamespace(doxygen_toc_max_children=50)
    )

    # Source template is never modified.
    assert template.read_text(encoding="utf-8") == original
    # Generated output exists and is the returned path.
    assert result == output
    assert output.is_file()


def test_do_expansion_preserves_comment_header(
    tmp_path: Path, doxygen_html: Path
) -> None:
    template = _toc_template(tmp_path)
    output = tmp_path / "out.yml"
    mod._do_expansion(
        template, output, doxygen_html, SimpleNamespace(doxygen_toc_max_children=50)
    )
    text = output.read_text(encoding="utf-8")
    assert text.startswith("# a comment header")


def test_do_expansion_routes_children(
    tmp_path: Path, doxygen_html: Path
) -> None:
    template = _toc_template(tmp_path)
    output = tmp_path / "out.yml"
    mod._do_expansion(
        template, output, doxygen_html, SimpleNamespace(doxygen_toc_max_children=50)
    )
    data = yaml.safe_load(output.read_text(encoding="utf-8"))
    entries = data["subtrees"][0]["entries"]
    by_file = {e["file"]: e for e in entries}

    # Structs routed under the 'annotated' sibling.
    annotated = by_file["doxygen/html/annotated"]
    struct_files = {
        c["file"] for c in annotated["subtrees"][0]["entries"]
    }
    assert "doxygen/html/structWidget" in struct_files
    assert "doxygen/html/structGadget" in struct_files

    # File page routed under the 'files' sibling.
    files = by_file["doxygen/html/files"]
    file_files = {c["file"] for c in files["subtrees"][0]["entries"]}
    assert "doxygen/html/widget__impl_8h" in file_files


def test_do_expansion_dedupes_routed_struct(
    tmp_path: Path, doxygen_html: Path
) -> None:
    # structWidget is referenced by both the group page and annotated.html;
    # it must appear exactly once under 'annotated' (regression guard for the
    # merge/dedup path that the total_children count fix depends on).
    template = _toc_template(tmp_path)
    output = tmp_path / "out.yml"
    mod._do_expansion(
        template, output, doxygen_html, SimpleNamespace(doxygen_toc_max_children=50)
    )
    data = yaml.safe_load(output.read_text(encoding="utf-8"))
    annotated = next(
        e
        for e in data["subtrees"][0]["entries"]
        if e["file"] == "doxygen/html/annotated"
    )
    struct_files = [c["file"] for c in annotated["subtrees"][0]["entries"]]
    assert struct_files.count("doxygen/html/structWidget") == 1


def test_expand_toc_template_disabled_returns_none(tmp_path: Path) -> None:
    app = SimpleNamespace(
        config=SimpleNamespace(doxygen_toc_auto_expand=False),
        srcdir=str(tmp_path),
        outdir=str(tmp_path / "out"),
    )
    assert mod.expand_toc_template(app, tmp_path) is None


def test_expand_toc_template_missing_html_returns_none(tmp_path: Path) -> None:
    template = tmp_path / ".sphinx" / "_toc.yml.in"
    template.parent.mkdir(parents=True)
    template.write_text("root: index\n", encoding="utf-8")
    app = SimpleNamespace(
        config=SimpleNamespace(
            doxygen_toc_auto_expand=True,
            external_toc_template_path=".sphinx/_toc.yml.in",
            doxygen_html=None,
        ),
        srcdir=str(tmp_path),
        outdir=str(tmp_path / "out"),
    )
    # No docBin/html under doxygen_root -> cannot expand.
    assert mod.expand_toc_template(app, tmp_path / "nodox") is None
