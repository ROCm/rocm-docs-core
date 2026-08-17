"""Sphinx extension providing the selector directive for conditional content."""

from pathlib import Path

from .nodes import (
    SelectedContent,
    SelectedContentDirective,
    SelectorDropdownDirective,
    SelectorGroup,
    SelectorGroupDirective,
    SelectorInfo,
    SelectorInfoDirective,
    SelectorOption,
    SelectorOptionDirective,
)
from .transforms import (
    SelectorPDFReorganizeTransform,
    SelectorToSectionTransform,
)
from .utils import noop, register_output_flags, skip_node

_TEMPLATES_DIR = str(Path(__file__).parent / "templates")


def _add_templates(_app, config):
    if _TEMPLATES_DIR not in config.templates_path:
        config.templates_path.append(_TEMPLATES_DIR)


def _purge_selector_pages(_app, env, docname):
    if hasattr(env, "_selector_pages"):
        env._selector_pages.discard(docname)


def _merge_selector_pages(_app, env, _docnames, other):
    if not hasattr(env, "_selector_pages"):
        env._selector_pages = set()
    env._selector_pages.update(getattr(other, "_selector_pages", set()))


def _has_toc2_metadata(env, docname):
    metadata = env.metadata.get(docname, {})
    return "selector-toc2" in metadata or "selector-toc2-icon" in metadata


def _inject_selector_sidebar(app, env):
    selector_pages: set[str] = getattr(env, "_selector_pages", set())
    if not selector_pages:
        return
    sidebar = app.config.html_theme_options.setdefault(
        "secondary_sidebar_items", {}
    )
    if not isinstance(sidebar, dict):
        return
    sidebar.setdefault("**", ["page-toc"])
    for docname in selector_pages:
        if _has_toc2_metadata(env, docname) and docname not in sidebar:
            sidebar[docname] = ["selector-toc2"]


def _inject_selector_toc2_context(
    app, pagename, _templatename, context, _doctree
):
    if pagename not in getattr(app.env, "_selector_pages", set()):
        return
    if not _has_toc2_metadata(app.env, pagename):
        return
    metadata = app.env.metadata.get(pagename, {})
    context["selector_toc2"] = metadata.get("selector-toc2", "")
    context["selector_toc2_icon"] = metadata.get(
        "selector-toc2-icon", "fa-solid fa-computer"
    )


def setup(app):
    """Register all selector nodes, directives, and event hooks with Sphinx."""
    app.add_node(
        SelectorGroup,
        html=(SelectorGroup.visit_html, SelectorGroup.depart_html),
        markdown=(skip_node, noop),
        latex=(skip_node, noop),
        text=(skip_node, noop),
        man=(skip_node, noop),
        texinfo=(skip_node, noop),
    )
    app.add_node(
        SelectorInfo,
        html=(SelectorInfo.visit_html, SelectorInfo.depart_html),
        markdown=(skip_node, noop),
        latex=(skip_node, noop),
        text=(skip_node, noop),
        man=(skip_node, noop),
        texinfo=(skip_node, noop),
    )
    app.add_node(
        SelectorOption,
        html=(SelectorOption.visit_html, SelectorOption.depart_html),
        markdown=(skip_node, noop),
        latex=(skip_node, noop),
        text=(skip_node, noop),
        man=(skip_node, noop),
        texinfo=(skip_node, noop),
    )
    app.add_node(
        SelectedContent,
        html=(SelectedContent.visit_html, SelectedContent.depart_html),
        markdown=(SelectedContent.visit_markdown, noop),
        latex=(SelectedContent.visit_static, noop),
        text=(SelectedContent.visit_static, noop),
        man=(SelectedContent.visit_static, noop),
        texinfo=(SelectedContent.visit_static, noop),
    )

    app.add_directive("selector", SelectorGroupDirective)
    app.add_directive("selector-dropdown", SelectorDropdownDirective)
    app.add_directive("selector-info", SelectorInfoDirective)
    app.add_directive("selector-option", SelectorOptionDirective)
    app.add_directive("selected-content", SelectedContentDirective)
    app.add_directive("selected", SelectedContentDirective)

    # for builder=latex
    app.add_post_transform(SelectorPDFReorganizeTransform)
    app.add_post_transform(SelectorToSectionTransform)

    register_output_flags(app)

    app.connect("config-inited", _add_templates)
    app.connect("env-purge-doc", _purge_selector_pages)
    app.connect("env-merge-info", _merge_selector_pages)
    app.connect("env-updated", _inject_selector_sidebar)
    app.connect("html-page-context", _inject_selector_toc2_context)

    # The post-transforms mutate each document's own doctree independently and
    # hold no cross-document state, so parallel writing is safe.
    return {
        "version": "1.5",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
