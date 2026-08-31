"""Add Doxygen group anchors as sidebar children for XML+Breathe projects.

Projects that render their Doxygen API reference through Breathe directives
(rather than doxysphinx HTML) put every group on a single page as in-page
sections, e.g. ``functions.md`` with a ``## <group title>`` heading per group.
sphinx-external-toc cannot represent in-page anchors as navigation nodes, and
pydata-sphinx-theme strips ``#``-fragment links from the sidebar. This module
injects those group anchors back into the left sidebar as nested children of
the page that hosts them.

The group list and display titles come from the Doxygen XML index; the actual
anchor slug and hosting page come from Sphinx's std domain (the authoritative
source once MyST has assigned heading anchors). Pages are auto-detected: any
document whose sections resolve to Doxygen group anchors is expanded.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from sphinx.application import Sphinx
from sphinx.config import Config
from sphinx.domains.std import StandardDomain
from sphinx.util import logging

logger = logging.getLogger(__name__)

try:
    from bs4 import BeautifulSoup

    BS4_AVAILABLE = True
except ImportError:  # pragma: no cover - bs4 ships with the theme
    BS4_AVAILABLE = False


def _find_xml_dir(config: Config) -> Path | None:
    """Locate the Doxygen XML output directory from breathe config."""
    projects: dict[str, Any] = getattr(config, "breathe_projects", {}) or {}
    default = getattr(config, "breathe_default_project", None)

    candidates: list[Path] = []
    if default and default in projects:
        candidates.append(Path(projects[default]))
    candidates.extend(Path(p) for p in projects.values())

    for path in candidates:
        if (path / "index.xml").is_file():
            return path
    return None


def _read_group_titles(xml_dir: Path) -> dict[str, str]:
    """Map Doxygen group tag -> human title from the XML index.

    Insertion order follows index.xml, which matches the order groups are
    rendered on the page.
    """
    titles: dict[str, str] = {}
    try:
        index = ET.parse(xml_dir / "index.xml").getroot()
    except (ET.ParseError, OSError) as err:
        logger.warning(f"Could not read Doxygen XML index: {err}")
        return titles

    for compound in index.findall("compound"):
        if compound.get("kind") != "group":
            continue
        refid = compound.get("refid") or ""
        name = (compound.findtext("name") or "").strip()
        if not name or not refid:
            continue
        title = name
        group_file = xml_dir / f"{refid}.xml"
        if group_file.is_file():
            try:
                cdef = ET.parse(group_file).getroot().find("compounddef")
                if cdef is not None:
                    title = (cdef.findtext("title") or "").strip() or name
            except (ET.ParseError, OSError):
                pass
        titles[name] = title
    return titles


def _resolve_group_locations(
    app: Sphinx, group_titles: dict[str, str]
) -> dict[str, list[tuple[str, str, str]]]:
    """Group anchors by hosting docname.

    Returns ``{docname: [(anchor, title, group_tag), ...]}`` where anchor and
    docname are resolved via the std domain (authoritative post-MyST), and the
    per-doc order follows index.xml.
    """
    std = cast(StandardDomain, app.env.get_domain("std"))
    by_doc: dict[str, list[tuple[str, str, str]]] = {}

    for tag, title in group_titles.items():
        # MyST lowercases target labels; std domain is keyed accordingly.
        labelled = std.labels.get(tag.lower())
        anon = std.anonlabels.get(tag.lower())
        label: tuple[str, str] | None
        if labelled is not None:
            label = (labelled[0], labelled[1])
        elif anon is not None:
            label = anon
        else:
            label = None
        if label is None:
            continue
        docname, anchor = label
        by_doc.setdefault(docname, []).append((anchor, title, tag))

    return by_doc


def _build_children_html(
    pathto: Callable[[str], str],
    docname: str,
    entries: list[tuple[str, str, str]],
) -> str:
    """Build the nested <ul> of group anchor links for one page."""
    base = pathto(docname)
    # For the page currently being rendered, pathto returns "#"; avoid the
    # resulting "##anchor" by using a bare fragment.
    if base == "#":
        base = ""
    items = []
    for anchor, title, _tag in entries:
        href = f"{base}#{anchor}"
        items.append(
            f'<li class="toctree-l2 doxygen-group">'
            f'<a class="reference internal" href="{href}">{title}</a></li>'
        )
    return (
        '<ul class="nav bd-sidenav doxygen-group-nav">' + "".join(items) + "</ul>"
    )


def _install_wrapper(
    pagename: str,
    context: dict[str, Any],
    by_doc: dict[str, list[tuple[str, str, str]]],
) -> None:
    """Wrap generate_toctree_html to splice group anchors into the sidebar."""
    original = context.get("generate_toctree_html")
    if original is None or not callable(original):
        return

    pathto = context.get("pathto")
    if pathto is None:
        return

    def wrapped(*args: Any, **kwargs: Any) -> Any:
        html = original(*args, **kwargs)
        # Only augment the sidebar navigation, not the raw navbar.
        if kwargs.get("kind") != "sidebar":
            return html

        soup = BeautifulSoup(str(html), "html.parser")

        # Sidebar entries for the hosting pages may appear at any nesting
        # depth (e.g. a "Functions" page nested under a "C/C++ API" parent),
        # so match links at any level rather than a fixed toctree-lN.
        for link in soup.select("a.reference.internal"):
            href = str(link.get("href", ""))
            # Resolve the sidebar link back to a docname we host anchors for.
            target_doc = _match_docname(href, pagename, by_doc, pathto)
            if target_doc is None:
                continue
            li = link.parent
            if li is None or li.name != "li":
                continue
            if li.find("ul") is not None:
                continue  # already has children; don't duplicate
            fragment = BeautifulSoup(
                _build_children_html(pathto, target_doc, by_doc[target_doc]),
                "html.parser",
            )
            li.append(fragment)
            raw_classes = li.get("class")
            class_list: list[str] = []
            if isinstance(raw_classes, list):
                class_list = [str(c) for c in raw_classes]
            elif raw_classes:
                class_list = [str(raw_classes)]
            if "has-children" not in class_list:
                li["class"] = " ".join([*class_list, "has-children"])

        return str(soup)

    context["generate_toctree_html"] = wrapped


def _match_docname(
    href: str,
    pagename: str,
    by_doc: dict[str, list[tuple[str, str, str]]],
    pathto: Callable[[str], str],
) -> str | None:
    """Find which hosted docname a sidebar href points to, if any."""
    if not href or href.startswith(("http://", "https://")):
        return None
    # The current page's own sidebar link renders as "#", so match it to the
    # page being rendered.
    if href == "#":
        return pagename if pagename in by_doc else None
    if "#" in href:
        return None
    for docname in by_doc:
        if pathto(docname) == href:
            return docname
    return None


def _on_html_page_context(
    app: Sphinx,
    pagename: str,
    _templatename: str,
    context: dict[str, Any],
    _doctree: Any,
) -> None:
    if not getattr(app.config, "doxygen_group_toc", False):
        return
    if not BS4_AVAILABLE:
        logger.warning(
            "doxygen_group_toc requires beautifulsoup4; sidebar not augmented."
        )
        return

    xml_dir = _find_xml_dir(app.config)
    if xml_dir is None:
        logger.debug("doxygen_group_toc: no Doxygen XML index found")
        return

    group_titles = _read_group_titles(xml_dir)
    if not group_titles:
        return

    by_doc = _resolve_group_locations(app, group_titles)
    if not by_doc:
        logger.debug("doxygen_group_toc: no group anchors resolved via std domain")
        return

    _install_wrapper(pagename, context, by_doc)


def _register_assets(app: Sphinx) -> None:
    """Register the scrollspy script when the feature is enabled.

    The script ships in the rocm_docs_theme static directory, so it only
    needs registering (not copying) here.
    """
    if not getattr(app.config, "doxygen_group_toc", False):
        return
    if app.builder is not None and app.builder.format != "html":
        return
    app.add_js_file("doxygen_group_toc.js", loading_method="defer")


def setup(app: Sphinx) -> dict[str, Any]:
    """Set up rocm_docs.doxygen_group_toc as a Sphinx extension."""
    app.add_config_value("doxygen_group_toc", False, rebuild="html", types=bool)
    # Must run after pydata-sphinx-theme's add_toctree_functions (which installs
    # generate_toctree_html at the default html-page-context priority of 500),
    # so we wrap the function it provides.
    app.connect("html-page-context", _on_html_page_context, priority=900)
    app.connect("builder-inited", _register_assets)
    return {
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
