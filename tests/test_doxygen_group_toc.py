from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import rocm_docs.doxygen_group_toc as mod

INDEX_XML = """<?xml version='1.0' encoding='UTF-8'?>
<doxygenindex>
  <compound refid="group__tagAsic" kind="group"><name>tagAsic</name></compound>
  <compound refid="group__tagPower" kind="group"><name>tagPower</name></compound>
  <compound refid="group__nogroupfile" kind="group"><name>tagOrphan</name></compound>
  <compound refid="struct_x" kind="struct"><name>SomeStruct</name></compound>
</doxygenindex>
"""

GROUP_ASIC = """<?xml version='1.0' encoding='UTF-8'?>
<doxygen>
  <compounddef id="group__tagAsic" kind="group">
    <compoundname>tagAsic</compoundname>
    <title>ASIC &amp; Board Info</title>
  </compounddef>
</doxygen>
"""

GROUP_POWER = """<?xml version='1.0' encoding='UTF-8'?>
<doxygen>
  <compounddef id="group__tagPower" kind="group">
    <compoundname>tagPower</compoundname>
    <title>Power Queries</title>
  </compounddef>
</doxygen>
"""


@pytest.fixture
def xml_dir(tmp_path: Path) -> Path:
    (tmp_path / "index.xml").write_text(INDEX_XML, encoding="utf-8")
    (tmp_path / "group__tagAsic.xml").write_text(GROUP_ASIC, encoding="utf-8")
    (tmp_path / "group__tagPower.xml").write_text(GROUP_POWER, encoding="utf-8")
    return tmp_path


def test_find_xml_dir_prefers_default(tmp_path: Path) -> None:
    (tmp_path / "index.xml").touch()
    config = SimpleNamespace(
        breathe_projects={"amdsmi": tmp_path, "other": tmp_path / "missing"},
        breathe_default_project="amdsmi",
    )
    assert mod._find_xml_dir(config) == tmp_path


def test_find_xml_dir_none_when_no_index(tmp_path: Path) -> None:
    config = SimpleNamespace(
        breathe_projects={"amdsmi": tmp_path},
        breathe_default_project="amdsmi",
    )
    assert mod._find_xml_dir(config) is None


def test_read_group_titles_order_and_titles(xml_dir: Path) -> None:
    titles = mod._read_group_titles(xml_dir)
    # index.xml order preserved; struct compound ignored.
    assert list(titles.keys()) == ["tagAsic", "tagPower", "tagOrphan"]
    assert titles["tagAsic"] == "ASIC & Board Info"
    assert titles["tagPower"] == "Power Queries"
    # No group file -> falls back to the tag name as the title.
    assert titles["tagOrphan"] == "tagOrphan"


def test_resolve_group_locations_uses_lowercased_std_labels(
    xml_dir: Path,
) -> None:
    # MyST lowercases target labels; the std domain is keyed accordingly.
    std = SimpleNamespace(
        labels={
            "tagasic": ("reference/functions", "tagasic", "ASIC & Board Info"),
            "tagpower": ("reference/functions", "tagpower", "Power Queries"),
        },
        anonlabels={},
    )
    app = SimpleNamespace(env=SimpleNamespace(get_domain=lambda _: std))
    titles = mod._read_group_titles(xml_dir)

    by_doc = mod._resolve_group_locations(app, titles)

    assert set(by_doc) == {"reference/functions"}
    entries = by_doc["reference/functions"]
    # Order follows index.xml; unresolved tagOrphan is dropped.
    assert [e[0] for e in entries] == ["tagasic", "tagpower"]
    assert [e[1] for e in entries] == ["ASIC & Board Info", "Power Queries"]


def test_build_children_html_other_page() -> None:
    entries = [("tagasic", "ASIC & Board Info", "tagAsic")]
    html = mod._build_children_html(
        lambda _d: "functions.html", "reference/functions", entries
    )
    assert 'href="functions.html#tagasic"' in html
    assert "ASIC &amp; Board Info" in html or "ASIC & Board Info" in html
    assert "doxygen-group-nav" in html


def test_build_children_html_current_page_no_double_hash() -> None:
    entries = [("tagasic", "ASIC & Board Info", "tagAsic")]
    # pathto returns "#" for the page currently being rendered.
    html = mod._build_children_html(lambda _d: "#", "reference/functions", entries)
    assert 'href="#tagasic"' in html
    assert "##" not in html


@pytest.mark.parametrize(
    ("href", "pagename", "expected"),
    [
        ("functions.html", "install/install", "reference/functions"),
        ("#", "reference/functions", "reference/functions"),
        ("#", "install/install", None),  # current page not hosted
        ("https://x/functions.html", "p", None),  # external
        ("functions.html#tagasic", "p", None),  # already a fragment
        ("other.html", "p", None),  # not a hosted doc
    ],
)
def test_match_docname(
    href: str, pagename: str, expected: str | None
) -> None:
    by_doc = {"reference/functions": [("tagasic", "ASIC", "tagAsic")]}

    def pathto(doc: str) -> str:
        return "functions.html" if doc == "reference/functions" else doc

    assert mod._match_docname(href, pagename, by_doc, pathto) == expected


def test_install_wrapper_injects_children() -> None:
    pytest.importorskip("bs4")
    by_doc = {"reference/functions": [("tagasic", "ASIC & Board Info", "tagAsic")]}

    sidebar_html = (
        '<ul class="nav bd-sidenav">'
        '<li class="toctree-l2"><a class="reference internal" '
        'href="functions.html">Functions</a></li>'
        "</ul>"
    )

    def original(**_kwargs: object) -> str:
        return sidebar_html

    context = {
        "generate_toctree_html": original,
        "pathto": lambda d: "functions.html"
        if d == "reference/functions"
        else d,
    }
    mod._install_wrapper("install/install", context, by_doc)

    result = context["generate_toctree_html"](kind="sidebar")
    assert "doxygen-group-nav" in result
    assert "functions.html#tagasic" in result
    assert "has-children" in result


def test_install_wrapper_ignores_non_sidebar() -> None:
    pytest.importorskip("bs4")
    by_doc = {"reference/functions": [("tagasic", "ASIC", "tagAsic")]}
    called = {"n": 0}

    def original(**_kwargs: object) -> str:
        called["n"] += 1
        return "<ul></ul>"

    context = {
        "generate_toctree_html": original,
        "pathto": lambda d: d,
    }
    mod._install_wrapper("p", context, by_doc)
    # kind != "sidebar" -> passthrough, no injection.
    out = context["generate_toctree_html"](kind="raw")
    assert "doxygen-group-nav" not in out
