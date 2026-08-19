"""Docutils/Sphinx node classes and directives for the selector extension."""

from typing import Any, ClassVar

import html as html_mod
import json
from collections.abc import Callable
from pathlib import Path

from docutils import nodes
from docutils.parsers.rst import directives
from sphinx.util.docutils import SphinxDirective

from .utils import kv_to_data_attr, logger, normalize_key

# CSS classes forming the Python / CSS / JS interface
SELECTOR_GROUP_CLASS = "rocm-docs-selector-group"
SELECTOR_HEADING_CLASS = "rocm-docs-selector-group-heading"
SELECTOR_HEADING_TEXT_CLASS = "rocm-docs-selector-group-heading-text"
SELECTOR_OPTION_CLASS = "rocm-docs-selector-option"
SELECTOR_DROPDOWN_INPUT_CLASS = "rocm-docs-selector-dropdown-input"
SELECTOR_ICON_CLASS = "rocm-docs-selector-icon"
SELECTED_CONTENT_CLASS = "rocm-docs-selected-content"
CUSTOM_HEADING_CLASS = "rocm-docs-custom-heading"
DEFAULT_OPTION_CLASS = "rocm-docs-selector-option-default"

# Defaults
DEFAULT_HEADING_WIDTH = 3
DEFAULT_OPTION_WIDTH = 6
DirectiveOptionSpec = dict[str, Callable[[str], Any]]


def register_selector_assets(app):
    """Register selector static assets with the Sphinx application.

    Must be called from a setup-time event (e.g. ``builder-inited``) so that
    ``app.add_js_file`` / ``app.add_css_file`` are invoked before parallel
    reading starts.  Calling these during directive ``run()`` is unsafe with
    ``parallel_read_safe=True`` because worker-process environments are merged
    back to the parent without the app-level asset registrations.
    """
    static_assets_dir = Path(__file__).parent / "static"
    if str(static_assets_dir) not in app.config.html_static_path:
        app.config.html_static_path.append(str(static_assets_dir))
    # https://tom-select.js.org/
    app.add_js_file("vendor/tom-select.base.min.js")
    app.add_css_file("vendor/tom-select.bootstrap5.min.css")
    app.add_js_file("selector.js", type="module", defer="defer")
    app.add_css_file("selector.css")


def _warn_must_be_nested(state, lineno, docname, directive_name, parent_name):
    # Walk the ancestor chain (not descendants) to find a SelectorGroup.
    node = getattr(state, "parent", None)
    while node is not None:
        if isinstance(node, SelectorGroup):
            return
        node = node.parent
    logger.warning(
        f"'.. {directive_name}::' at line {lineno} should be nested"
        f" under a '.. {parent_name}::' directive",
        location=(docname, lineno),
    )


def _parse_heading_width(value, lineno, docname):
    """Parse and validate :heading-width: (1-12 integer or CSS percentage)."""
    if isinstance(value, str) and value.endswith("%"):
        try:
            pct = float(value[:-1])
            if pct <= 0 or pct > 100:
                raise ValueError("must be between 0 and 100")
            return value
        except ValueError as e:
            logger.warning(
                f"Invalid percentage heading-width '{value}' ({e}), using default",
                location=(docname, lineno),
            )
            return DEFAULT_HEADING_WIDTH
    else:
        try:
            col_num = int(value)
            if col_num < 1 or col_num > 12:
                raise ValueError("must be between 1 and 12")
            return col_num
        except ValueError as e:
            logger.warning(
                f"Invalid heading-width '{value}' ({e}), using default",
                location=(docname, lineno),
            )
            return DEFAULT_HEADING_WIDTH


def _parse_width(value, lineno, docname):
    if isinstance(value, str) and value.endswith("%"):
        try:
            pct = float(value[:-1])
            if pct <= 0 or pct > 100:
                raise ValueError("must be between 0 and 100")
            return value
        except ValueError as e:
            logger.warning(
                f"Invalid percentage width '{value}' ({e}), using default",
                location=(docname, lineno),
            )
            return DEFAULT_OPTION_WIDTH
    else:
        try:
            col_num = int(value)
            if col_num < 1 or col_num > 12:
                raise ValueError("must be between 1 and 12")
            return col_num
        except ValueError as e:
            logger.warning(
                f"Invalid width '{value}' ({e}), using default",
                location=(docname, lineno),
            )
            return DEFAULT_OPTION_WIDTH


class SelectorGroup(nodes.General, nodes.Element):
    """A row or dropdown within a selector container."""

    @staticmethod
    def visit_html(translator, node):
        """Emit the opening HTML for a selector group row."""
        label = node["label"]
        key = node["key"]
        show_cond_attr = kv_to_data_attr("show-cond", node["show-cond"])
        heading_width = node["heading-width"]
        is_dropdown = node.get("dropdown-input", False)

        role_attr = "" if is_dropdown else 'role="radiogroup"'
        select_open = (
            f'<select class="form-select {SELECTOR_DROPDOWN_INPUT_CLASS}"'
            f' data-selector-key="{key}" aria-label="{label}">'
            if is_dropdown
            else ""
        )

        if isinstance(heading_width, str) and heading_width.endswith("%"):
            remainder = f"{100 - float(heading_width[:-1])}%"
            heading_div_attrs = (
                f'class="me-1 px-2 {SELECTOR_HEADING_CLASS}"'
                f' style="width: {heading_width}"'
            )
            content_div_attrs = f'class="row pe-0" style="width: {remainder}"'
        else:
            col = int(heading_width)
            heading_div_attrs = (
                f'class="col-{col} me-1 px-2 {SELECTOR_HEADING_CLASS}"'
            )
            content_div_attrs = f'class="row col-{12 - col} pe-0"'

        translator.body.append(
            f"""
            <div id="{node['dom-id']}"
                class="{SELECTOR_GROUP_CLASS} row pt-2"
                data-selector-key="{key}"
                {show_cond_attr}
                {role_attr}
                aria-label="{label}"
            >
                <div {heading_div_attrs}>
                    <span class="{SELECTOR_HEADING_TEXT_CLASS}">{label}</span>
                </div>
                <div {content_div_attrs}>
                {select_open}
            """.strip()
        )

    @staticmethod
    def depart_html(translator, node):
        """Emit the closing HTML for a selector group row."""
        is_dropdown = node.get("dropdown-input", False)
        translator.body.append(
            f"""
                {"</select>" if is_dropdown else ""}
                </div>
            </div>
            """
        )


class _SelectorGroupBase(SphinxDirective):
    required_arguments = 1  # title text
    final_argument_whitespace = True
    has_content = True
    _is_dropdown = False  # overridden in subclass

    def run(self):
        if not hasattr(self.env, "_selector_pages"):
            self.env._selector_pages = set()  # type: ignore[attr-defined]
        self.env._selector_pages.add(self.env.docname)  # type: ignore[attr-defined]

        label = self.arguments[0]
        node = SelectorGroup()
        node["label"] = label
        node["key"] = normalize_key(self.options.get("key", label))
        node["show-cond"] = self.options.get("show-cond", "")
        node["heading-width"] = _parse_heading_width(
            self.options.get("heading-width", DEFAULT_HEADING_WIDTH),
            self.lineno,
            self.env.docname,
        )
        node["dropdown-input"] = self._is_dropdown

        # Allocate a document-unique DOM ID for this group so repeated titles
        # (e.g. two "Installation method" selectors on one page) do not
        # collide in the HTML output and confuse getUniqueGroups.
        if not hasattr(self.env, "_selector_group_ids"):
            self.env._selector_group_ids = {}  # type: ignore[attr-defined]
        page_ids = self.env._selector_group_ids.setdefault(self.env.docname, set())  # type: ignore[attr-defined]
        base_id = (
            nodes.make_id(label)
            or "selector-" + label.replace(" ", "-").lower()
        )
        candidate = base_id
        counter = 1
        while candidate in page_ids:
            counter += 1
            candidate = f"{base_id}-{counter}"
        page_ids.add(candidate)
        node["dom-id"] = candidate

        self.state.nested_parse(self.content, self.content_offset, node)

        option_nodes = list(node.findall(SelectorOption))
        if option_nodes:
            sort_order = self.options.get("sort", "").lower()
            if sort_order in ("asc", "desc"):
                reverse = sort_order == "desc"
                sorted_options = sorted(
                    option_nodes, key=lambda opt: opt["label"], reverse=reverse
                )
                # Reorder only SelectorOption children in-place, preserving non-option siblings
                option_positions = [
                    i
                    for i, c in enumerate(node.children)
                    if isinstance(c, SelectorOption)
                ]
                for pos, opt in zip(option_positions, sorted_options):
                    node.children[pos] = opt
                option_nodes = sorted_options
            elif sort_order:
                raise self.error(
                    f"Invalid ':sort:' value '{sort_order}' — expected 'asc' or 'desc'"
                )

            for opt in option_nodes:
                opt["group_key"] = node["key"]
                opt["dropdown-input"] = self._is_dropdown

            if not any(opt["default"] for opt in option_nodes):
                option_nodes[0]["default"] = True

        return [node]


class SelectorGroupDirective(_SelectorGroupBase):
    """Directive for a radio-button selector group row."""

    option_spec: ClassVar[DirectiveOptionSpec] = {
        "key": directives.unchanged,
        "show-cond": directives.unchanged,
        "heading-width": directives.unchanged,
    }
    _is_dropdown = False


class SelectorDropdownDirective(_SelectorGroupBase):
    """Directive for a dropdown selector group row."""

    option_spec: ClassVar[DirectiveOptionSpec] = {
        "key": directives.unchanged,
        "show-cond": directives.unchanged,
        "heading-width": directives.unchanged,
        "sort": directives.unchanged,
    }
    _is_dropdown = True


class SelectorOption(nodes.General, nodes.Element):
    """A selectable tile or list-item option within a selector group."""

    @staticmethod
    def visit_html(translator, node):
        """Emit the opening HTML for a selector option tile or dropdown item."""
        label = node["label"]
        value = node["value"]
        show_cond_attr = kv_to_data_attr("show-cond", node["show-cond"])
        disable_cond_attr = kv_to_data_attr(
            "disable-cond", node["disable-cond"]
        )
        default = node["default"]
        width = node["width"]
        is_dropdown = node.get("dropdown-input", False)
        alt_name = node.get("alt-name", "")
        toc_label = node.get("toc-label", "")

        extra_bindings = node.get("extra-bindings", {})
        extra_bindings_attr = (
            f'data-selector-extra-bindings="{html_mod.escape(json.dumps(extra_bindings))}"'
            if extra_bindings
            else ""
        )

        if is_dropdown:
            display_text = alt_name if alt_name else label
            default_class = f" {DEFAULT_OPTION_CLASS}" if default else ""
            toc_label_attr = (
                f' data-toc-label="{toc_label}"' if toc_label else ""
            )
            translator.body.append(
                f'<option class="{SELECTOR_OPTION_CLASS}{default_class}"'
                f' value="{value}"'
                f' data-selector-key="{node.get("group_key", "")}"'
                f' data-selector-value="{value}"'
                f"{' selected' if default else ''}"
                f" {show_cond_attr} {disable_cond_attr}"
                f"{toc_label_attr} {extra_bindings_attr}>{display_text}</option>"
            )
            return

        default_class = DEFAULT_OPTION_CLASS if default else ""

        if isinstance(width, str) and width.endswith("%"):
            width_class = ""
            width_style = f' style="width: {width}"'
        else:
            width_class = f"col-{width}"
            width_style = ""

        toc_label_attr = f'data-toc-label="{toc_label}"' if toc_label else ""

        translator.body.append(
            f"""
            <div class="{SELECTOR_OPTION_CLASS} {default_class} {width_class} px-2"
                data-selector-key="{node.get("group_key", "")}"
                data-selector-value="{value}"
                {show_cond_attr}
                {disable_cond_attr}
                tabindex="0"
                role="radio"
                aria-checked="false"
                {toc_label_attr}
                {extra_bindings_attr}
                {width_style}
            >
                <span>{label}</span>
            """.strip()
        )

    @staticmethod
    def depart_html(translator, node):
        """Emit the closing HTML for a selector option tile."""
        if node.get("dropdown-input", False):
            return
        icon = node["icon"]
        if icon:
            translator.body.append(
                f'<i class="{SELECTOR_ICON_CLASS} {icon}"></i>'
            )
        translator.body.append("</div>")


class SelectorOptionDirective(SphinxDirective):
    """Directive for a selectable option tile or dropdown item."""

    required_arguments = 1  # text of tile
    final_argument_whitespace = True
    option_spec: ClassVar[DirectiveOptionSpec] = {
        "value": directives.unchanged,
        "alt-name": directives.unchanged,
        "show-cond": directives.unchanged,
        "disable-cond": directives.unchanged,
        "default": directives.flag,
        "width": directives.unchanged,
        "icon": directives.unchanged,
        "toc-label": directives.unchanged,
    }
    has_content = True

    def run(self):
        """Parse the directive and return a SelectorOption node."""
        label = self.arguments[0]
        node = SelectorOption()
        node["label"] = label

        # :value: accepts an optional bare value followed by extra key=value
        # bindings, e.g. ":value: mi355x gfx=gfx950 arch=cdna3".
        # The first token without '=' is the option's own value; the rest set
        # additional selector keys when this option is chosen.
        if "value" in self.options:
            value_raw = self.options["value"]
            tokens = value_raw.split()
            bare_tokens = [t for t in tokens if "=" not in t]
            kv_tokens = [t for t in tokens if "=" in t]
            node["value"] = normalize_key(
                bare_tokens[0] if bare_tokens else label
            )
        else:
            kv_tokens = []
            node["value"] = normalize_key(label)

        extra_bindings = {}
        for token in kv_tokens:
            k, _, v = token.partition("=")
            if k and v:
                extra_bindings[normalize_key(k)] = normalize_key(v)
        node["extra-bindings"] = extra_bindings

        node["show-cond"] = self.options.get("show-cond", "")
        node["disable-cond"] = self.options.get("disable-cond", "")
        node["default"] = "default" in self.options
        node["width"] = _parse_width(
            self.options.get("width", DEFAULT_OPTION_WIDTH),
            self.lineno,
            self.env.docname,
        )
        node["alt-name"] = self.options.get("alt-name", "")
        node["icon"] = self.options.get("icon")
        node["toc-label"] = self.options.get("toc-label", "")

        _warn_must_be_nested(
            self.state,
            self.lineno,
            self.env.docname,
            "selector-option",
            "selector",
        )

        return [node]


class SelectedContent(nodes.General, nodes.Element):
    """A container to hold documentation content to be shown conditionally.

    rST usage::

        .. selected-content:: os=ubuntu
           :heading: Ubuntu Notes
    """

    @staticmethod
    def visit_html(translator, node):
        """Emit the opening HTML for a conditional content block."""
        show_cond = node.get("show-cond", "")
        show_cond_attr = kv_to_data_attr("show-cond", show_cond)
        classes = " ".join(node.get("class", []))
        heading = node.get("heading", "")
        heading_level = max(2, min(node.get("heading-level") or 2, 6))

        id_attr = ""
        heading_elem = ""
        explicit_id = node.get("id", "")
        if heading:
            combined_show_cond = node.get("combined-show-cond", show_cond)
            id_attr = explicit_id or nodes.make_id(
                f"{heading}-{combined_show_cond}"
            )
            heading_elem = (
                f'<h{heading_level} class="{CUSTOM_HEADING_CLASS}">'
                f'{heading}<a class="headerlink" href="#{id_attr}" title="Link to this heading">#</a>'
                f"</h{heading_level}>"
            )
        elif explicit_id:
            id_attr = explicit_id

        tag = "section" if heading else "div"
        translator.body.append(
            f"""
            <{tag}
                id="{id_attr}"
                class="{SELECTED_CONTENT_CLASS} {classes}"
                {show_cond_attr}
                aria-hidden="true">
                {heading_elem}
            """.strip()
        )

    @staticmethod
    def depart_html(translator, node):
        """Emit the closing HTML for a conditional content block."""
        tag = "section" if node.get("heading", "") else "div"
        translator.body.append(f"</{tag}>")

    @staticmethod
    def visit_static(translator, _node):
        """Visit handler for static builders (LaTeX/text/man/texinfo).

        Normally SelectorToSectionTransform rewrites every SelectedContent into
        plain sections before the writer runs, so this handler sees nothing. But
        when ``rocm_docs_pdf_mock_selector_state`` is False that transform is
        skipped for LaTeX, leaving raw SelectedContent nodes in the tree. A
        plain no-op visit would still let the writer descend into and render
        all children; skip the whole subtree instead so the conditional content
        is genuinely omitted from the PDF.
        """
        if not translator.config.rocm_docs_pdf_mock_selector_state:
            raise nodes.SkipNode
        # PDF generation enabled (or a non-LaTeX static builder): let the
        # already-transformed children render as before.

    @staticmethod
    def visit_markdown(translator, node):
        """Render conditional content inline in Markdown/llms-full.txt output.

        The Markdown translator has no visitor for selector nodes. Content is
        rendered inline, prefixed with a bold condition/heading label so
        mutually-exclusive variants are not conflated. When Markdown generation
        is disabled, the block is dropped entirely.
        """
        if not translator.config.rocm_selector_markdown_generation:
            raise nodes.SkipNode
        heading = node.get("heading", "")
        # Use this node's own condition (not combined-show-cond): the Markdown
        # walker descends into nested SelectedContent nodes, each of which emits
        # its own label, so nesting context is already represented. The combined
        # value also picks up sibling conditions for top-level blocks.
        show_cond = node.get("show-cond", "")
        label_parts = []
        if show_cond:
            label_parts.append(show_cond)
        if heading:
            label_parts.append(heading)
        label = " — ".join(label_parts)
        if label:
            para = nodes.paragraph()
            para += nodes.strong(text=label)
            para.walkabout(translator)
        for child in node.children:
            child.walkabout(translator)
        raise nodes.SkipNode


class SelectedContentDirective(SphinxDirective):
    """Directive for conditionally shown content blocks."""

    required_arguments = 1  # condition (e.g., os=ubuntu)
    final_argument_whitespace = True
    has_content = True
    option_spec: ClassVar[DirectiveOptionSpec] = {
        "id": directives.unchanged,
        "class": directives.class_option,
        "heading": directives.unchanged,
        "heading-level": directives.nonnegative_int,
        "no-pdf": directives.flag,
    }

    def run(self):
        """Parse the directive and return a SelectedContent node."""
        node = SelectedContent()
        node["show-cond"] = self.arguments[0]
        node["id"] = self.options.get("id", "")
        node["class"] = self.options.get("class", "")
        node["heading"] = self.options.get("heading", "")
        node["heading-level"] = self.options.get("heading-level", None)
        node["no-pdf"] = "no-pdf" in self.options

        parent_show_conds = [
            ancestor["show-cond"]
            for ancestor in self.state.parent.traverse(include_self=True)
            if isinstance(ancestor, SelectedContent) and "show-cond" in ancestor
        ]
        node["combined-show-cond"] = "+".join(
            [*parent_show_conds, node["show-cond"]]
        )

        self.state.nested_parse(self.content, self.content_offset, node)
        return [node]
