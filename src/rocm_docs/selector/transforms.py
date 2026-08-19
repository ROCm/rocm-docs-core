"""Post-transforms for converting selector nodes for non-HTML builders."""

from collections.abc import Sequence

from docutils import nodes
from sphinx.errors import ExtensionError
from sphinx.transforms.post_transforms import SphinxPostTransform

from .nodes import SelectedContent, SelectorGroup, SelectorOption
from .utils import logger, make_unique_id, normalize_key

# ---------------------------------------------------------------------------
# Constants and helpers for SelectorPDFReorganizeTransform.
# These must appear after all node classes they reference.
# ---------------------------------------------------------------------------

# Node types that are selector UI chrome — always skipped when gathering content
_SELECTOR_UI = (SelectorGroup, SelectorOption)

# Condition keys to treat as always-match during PDF filtering.
#
# Empty by design: all condition keys must be *evaluated*, not ignored.
# A key absent from the current combo causes ``_matches`` to return False,
# so blocks guarded by keys not in the combo are correctly excluded from
# PDF output without an explicit allowlist here.
_IGNORE_KEYS: set[str] = set()


def _parse_cond(show_cond: str) -> dict[str, list[str]]:
    """Parse a ``show-cond`` string into {key: [values]}.

    Same-key entries are OR'd; different keys are AND'd.
    Keys in ``_IGNORE_KEYS`` are dropped so they never block a match.
    """
    result: dict[str, list[str]] = {}
    for token in show_cond.split():
        if "=" not in token:
            continue
        k, _, v = token.partition("=")
        k = normalize_key(k)
        v = normalize_key(v)
        if k in _IGNORE_KEYS:
            continue
        result.setdefault(k, []).append(v)
    return result


def _visible_in_partial_combo(
    group_cond: str,
    partial_combo: dict[str, str],
    decided_absent: set[str] | None = None,
) -> bool:
    """Return True if a selector group is NOT definitively hidden given *partial_combo*.

    Used during combo building, where *partial_combo* only contains keys set so
    far.  Unlike ``_matches``, an absent condition key normally means "not yet
    decided" — the group might become visible once that key is set.  The
    exception is *decided_absent*: keys that were processed but had no visible
    values (and were therefore skipped entirely).  A condition referencing a
    decided-absent key can never be satisfied, so the group is hidden.
    """
    if not group_cond:
        return True
    cond = _parse_cond(group_cond)
    for key, allowed in cond.items():
        if key in partial_combo:
            if partial_combo[key] not in allowed:
                return False  # definitively hidden by value mismatch
        elif decided_absent is not None and key in decided_absent:
            return False  # key was skipped — condition can never be met
        # else: not yet decided — keep the group visible
    return True


def _matches(show_cond: str, combo: dict[str, str]) -> bool:
    """Return True if *combo* satisfies all conditions in *show_cond*.

    *combo* is a dict of {key: value} for the current (fam, os, ver, i).

    - Empty show-cond → always True (unconditional content).
    - Keys in ``_IGNORE_KEYS`` are stripped before matching (too granular).
    - Any remaining key that is absent from *combo* means the content
      belongs to a dimension that does not exist in the PDF (e.g. ``w``
      for the graphics/compute workload toggle) → returns False so those
      blocks are excluded rather than duplicated across every combo.
    """
    if not show_cond:
        return True
    cond = _parse_cond(show_cond)
    for key, allowed in cond.items():
        if key not in combo:
            return False  # dimension absent from PDF combos — exclude
        if combo[key] not in allowed:
            return False
    return True


def _make_pdf_id(*parts: str) -> str:
    """Build a unique, valid HTML/LaTeX ID from an arbitrary list of strings."""
    raw = "-".join(str(p) for p in parts if p)
    id_ = nodes.make_id(raw)
    # make_id returns "" for strings that start with digits (e.g. version "26.04");
    # fall back to a prefixed slug.
    return id_ or "pdf-" + raw.replace(".", "-").replace(" ", "-").lower()


def _iter_matrix_own(start, cls_name):
    """Yield descendants of *start* whose class is *cls_name*, stopping at a nested matrix.

    An inner matrix's rows/cells are not pulled into the outer grid.

    The matrix nodes live in a sibling extension; they are matched by class
    name rather than imported so this module stays decoupled from the matrix
    package (the import path differs across repo layouts).
    """
    for child in start.children:
        if type(child).__name__ == "CustomTable":
            continue  # boundary: a nested matrix owns its own rows/cells
        if type(child).__name__ == cls_name:
            yield child
        yield from _iter_matrix_own(child, cls_name)


def _filter_matrix(
    table_node: nodes.Node, combo: dict[str, str], id_prefix: str = ""
) -> nodes.Node:
    """Return a deep copy of a matrix ``CustomTable`` filtered for *combo*.

    In HTML, matrix rows/cells carrying a ``show-cond`` are shown or hidden by
    JavaScript for the selected device. The PDF has no JavaScript, so without
    filtering every conditional cell would render — e.g. all 11 GPU-specific
    package-name cells exploding a 3-column table into 14 columns. This drops
    rows and cells whose ``show-cond`` does not match *combo*, then filters any
    ``SelectedContent`` nested inside a surviving cell (so its per-GPU variants
    collapse to the matching one).
    """
    new_table = table_node.deepcopy()
    for row in list(_iter_matrix_own(new_table, "CustomTableRow")):
        row_cond = row.get("show-cond", "")
        if row_cond and not _matches(row_cond, combo):
            row.parent.remove(row)
            continue
        for cell in list(_iter_matrix_own(row, "CustomTableCell")):
            cell_cond = cell.get("show-cond", "")
            if cell_cond and not _matches(cell_cond, combo):
                cell.parent.remove(cell)
                continue
            if list(cell.findall(SelectedContent)):
                filtered: list[nodes.Node] = []
                _gather_content(cell.children, combo, filtered, id_prefix)
                cell.children = []
                for c in filtered:
                    c.parent = cell
                    cell.children.append(c)
    return new_table


def _gather_content(
    children: Sequence[nodes.Node],
    combo: dict[str, str],
    into: list[nodes.Node],
    id_prefix: str = "",
    document: nodes.document | None = None,
    id_remap: dict[str, str] | None = None,
) -> None:
    """Recursively collect content nodes that match *combo*.

    - ``SelectedContent`` nodes whose ``show-cond`` does not match *combo* are
      skipped entirely.
    - ``SelectedContent`` nodes that match are unwrapped: their children are
      processed recursively, with a heading section prepended if they carry one.
    - Regular ``section`` nodes (Prerequisites, Installation, etc.) are recursed
      into and rebuilt with only the filtered content; empty sections are dropped.
    - Selector UI nodes (``SelectorGroup`` etc.) are always skipped.
    - ``nodes.transition`` elements are skipped (decorative horizontal rules).
    - ``nodes.target`` elements are preserved and remapped to fresh unique IDs so
      that explicit RST labels used by ``refid`` cross-references are not lost.
    - Any other container node (dropdowns, admonitions, etc.) that contains
      ``SelectedContent`` descendants is recursed into and rebuilt so that
      filtering propagates through it.  Containers with no ``SelectedContent``
      descendants are deep-copied as-is.

    *document* and *id_remap* must be supplied together.  When present, every
    new section and target receives a document-unique ID assigned via
    ``make_unique_id``, and the old→new mapping is recorded in *id_remap* so
    the caller can update ``reference['refid']`` values after the tree is built.
    """

    def _new_id(base: str, node: nodes.Node | None = None) -> str:
        if document is not None:
            uid: str = make_unique_id(document, base, node)
            if id_remap is not None and base != uid:
                id_remap[base] = uid
            return uid
        return _make_pdf_id(id_prefix, base)

    for child in children:
        if isinstance(child, _SELECTOR_UI):
            continue
        if isinstance(child, nodes.transition):
            continue
        if isinstance(child, nodes.target):
            # Preserve explicit RST label targets but give each copy a fresh
            # unique ID so duplicated combo sections do not share IDs.
            new_target = child.deepcopy()
            old_ids: list[str] = list(new_target.get("ids", []))
            new_ids = []
            for oid in old_ids:
                nid = _new_id(oid, new_target)
                new_ids.append(nid)
            if new_ids:
                new_target["ids"] = new_ids
            into.append(new_target)
            continue
        if isinstance(child, SelectedContent):
            if child.get("no-pdf"):
                continue
            show_cond = child.get("show-cond", "")
            if show_cond and not _matches(show_cond, combo):
                continue
            heading = child.get("heading", "")
            if heading:
                inner: list[nodes.Node] = []
                _gather_content(
                    child.children, combo, inner, id_prefix, document, id_remap
                )
                if inner:
                    sec_id = _new_id(_make_pdf_id(id_prefix, heading))
                    section = nodes.section(ids=[sec_id], names=[sec_id])
                    section += nodes.title(text=heading)
                    for item in inner:
                        section += item
                    into.append(section)
            else:
                _gather_content(
                    child.children, combo, into, id_prefix, document, id_remap
                )
        elif isinstance(child, nodes.section):
            # Step section (e.g. Prerequisites, Installation): recurse and rebuild
            # with only the filtered content so unmatched variants are dropped.
            title_node = next(
                (c for c in child.children if isinstance(c, nodes.title)), None
            )
            non_title = [
                c for c in child.children if not isinstance(c, nodes.title)
            ]
            inner = []
            _gather_content(
                non_title, combo, inner, id_prefix, document, id_remap
            )
            if inner:
                step_title = title_node.astext() if title_node else ""
                sec_id = _new_id(_make_pdf_id(id_prefix, step_title))
                new_section = nodes.section(ids=[sec_id], names=[sec_id])
                if title_node:
                    new_section += title_node.deepcopy()
                for item in inner:
                    new_section += item
                # Record the original section IDs in the remap so that
                # references to the original source section resolve correctly.
                if id_remap is not None:
                    for oid in child.get("ids", []):
                        if oid not in id_remap:
                            id_remap[oid] = sec_id
                into.append(new_section)
        elif type(child).__name__ == "CustomTable":
            # A matrix table: filter its rows/cells by show-cond for this combo
            # (JavaScript does this in HTML; the PDF has no JS). Keep the custom
            # node type intact — MatrixToTableTransform converts it to a docutils
            # table later.
            into.append(_filter_matrix(child, combo, id_prefix))
        elif list(child.findall(SelectedContent)):
            # Container (e.g. dropdown/admonition) wrapping SelectedContent nodes.
            # Deep-copy the container then replace its children with the filtered set
            # so that conditional content inside it is properly pruned.
            new_node = child.deepcopy()
            filtered: list[nodes.Node] = []
            _gather_content(
                child.children, combo, filtered, id_prefix, document, id_remap
            )
            new_node.children = []
            for c in filtered:
                c.parent = new_node
                new_node.children.append(c)
            if new_node.children:
                into.append(new_node)
        else:
            into.append(child.deepcopy())


def _remap_references(tree: list[nodes.Node], id_remap: dict[str, str]) -> None:
    """Update ``reference['refid']`` values in *tree* using *id_remap*.

    Called after each combo's content nodes are attached so that internal
    cross-references point at the freshly assigned unique IDs rather than the
    original source IDs that no longer exist in the reorganised PDF doctree.
    """
    if not id_remap:
        return
    for node in tree:
        for ref in node.findall(nodes.reference):
            old = ref.get("refid", "")
            if old in id_remap:
                ref["refid"] = id_remap[old]


def _collect_selector_options(
    chapter: nodes.Node,
) -> dict[str, list[tuple[str, str, str, str]]]:
    """Scan the chapter for SelectorGroup/SelectorOption nodes and return options.

    Returns ``{key: [(value, label, group_show_cond, option_show_cond)]}`` with
    values deduplicated in document order.  ``group_show_cond`` is the parent
    SelectorGroup's ``show-cond``; ``option_show_cond`` is the individual
    SelectorOption's own ``show-cond``.  Both are checked when determining
    whether a value is reachable for a given partial combo.
    """
    opts: dict[str, list[tuple[str, str, str, str]]] = {}
    # Deduplicate by (value, group_show_cond) so the same value exposed by
    # multiple condition groups (e.g. i=pkgman as "apt" for Ubuntu and "dnf"
    # for RHEL) keeps each group's entry, enabling correct label selection and
    # visibility filtering in _iter_combos.
    seen: dict[str, set[tuple[str, str, str]]] = {}
    for sg in chapter.findall(SelectorGroup):
        key = sg.get("key", "")
        if not key:
            continue
        if key not in opts:
            opts[key] = []
            seen[key] = set()
        group_show_cond = sg.get("show-cond", "")

        # Inherit show-cond from ancestor SelectedContent blocks.  A selector
        # group nested inside ``.. selected:: os=windows`` should only be
        # visible when os=windows, even if it carries no explicit show-cond of
        # its own.  Concatenating the ancestor conditions (outermost first) with
        # the group's own condition preserves AND semantics across keys and OR
        # semantics within a key, matching how _parse_cond works.
        ancestor_parts: list[str] = []
        node = sg.parent
        while node is not None:
            if isinstance(node, SelectedContent):
                sc_cond = node.get("show-cond", "")
                if sc_cond:
                    ancestor_parts.append(sc_cond)
            node = node.parent
        if ancestor_parts:
            parts = list(reversed(ancestor_parts))
            if group_show_cond:
                parts.append(group_show_cond)
            group_show_cond = " ".join(parts)

        for opt in sg.findall(SelectorOption):
            val = opt.get("value", "")
            label = opt.get("label", val)
            option_show_cond = opt.get("show-cond", "")
            # Deduplicate by (val, group_show_cond, option_show_cond): the same
            # value may appear in the same selector group multiple times with
            # *different* option-level conditions (e.g. "10.2" conditioned on
            # gpu=X AND separately on fam=all).  Each combination must be
            # preserved so that _iter_combos can evaluate all possible paths for
            # visibility; dropping one hides values that are reachable via the
            # alternative condition.
            if (
                val
                and (val, group_show_cond, option_show_cond) not in seen[key]
            ):
                opts[key].append(
                    (val, label, group_show_cond, option_show_cond)
                )
                seen[key].add((val, group_show_cond, option_show_cond))
    return opts


def _iter_combos(
    remaining_keys: list[str],
    sel_opts: dict[str, list[tuple[str, str, str, str]]],
    combo: dict[str, str],
    decided_absent: set[str],
    labels: dict[str, str],
    out: list[tuple[dict[str, str], dict[str, str]]],
) -> None:
    """Recursively build (combo, labels) pairs for every key combination.

    Keys are iterated in dependency-sorted order as independent flat dimensions.

    *decided_absent* accumulates keys that were processed but had no visible
    values.  Conditions that reference a decided-absent key are treated as
    definitively unmet, preventing downstream keys from expanding into combos
    that can never exist (e.g. os groups conditioned on a gpu that was skipped).

    When multiple option groups expose the same value (e.g. the same
    install-method under different OSes), the label whose group ``show-cond``
    best matches the partial combo built so far is chosen.
    """
    if not remaining_keys:
        out.append((dict(combo), dict(labels)))
        return

    key = remaining_keys[0]
    rest = remaining_keys[1:]
    entries = sel_opts.get(key, [])

    # Unique values in document order; collect all (label, group_cond,
    # option_cond) per value.
    val_label_options: dict[str, list[tuple[str, str, str]]] = {}
    vals_ordered: list[str] = []
    seen_vals: set[str] = set()
    for val, label, group_cond, option_cond in entries:
        if val not in seen_vals:
            vals_ordered.append(val)
            seen_vals.add(val)
        val_label_options.setdefault(val, []).append(
            (label, group_cond, option_cond)
        )

    # Only iterate values not definitively hidden given the partial combo so far.
    # A value is kept if at least one of its (group, option) condition pairs is
    # not definitively hidden.  Both the group condition and the per-option
    # condition must be satisfiable simultaneously.
    visible_vals = [
        v
        for v in vals_ordered
        if any(
            _visible_in_partial_combo(gc, combo, decided_absent)
            and _visible_in_partial_combo(oc, combo, decided_absent)
            for _, gc, oc in val_label_options[v]
        )
    ]
    if not visible_vals:
        # This key has no visible values — record it as decided-absent so
        # downstream conditions that reference it are definitively hidden.
        decided_absent.add(key)
        _iter_combos(rest, sel_opts, combo, decided_absent, labels, out)
        decided_absent.discard(key)
        return

    for val in visible_vals:
        # Pick the label whose group show-cond best matches the partial combo.
        best_label = val_label_options[val][0][0]
        for lbl, group_cond, _opt_cond in val_label_options[val]:
            if _matches(group_cond, combo):
                best_label = lbl
                break

        combo[key] = val
        labels[key] = best_label
        _iter_combos(rest, sel_opts, combo, decided_absent, labels, out)
        del combo[key]
        del labels[key]


def _sorted_keys(
    sel_opts: dict[str, list[tuple[str, str, str, str]]],
) -> list[str]:
    """Return selector keys in an order safe for combo expansion.

    Keys whose ``show-cond`` references another selector key must come *after*
    that key; otherwise ``_visible_in_partial_combo`` sees the condition key as
    absent ("not yet decided") and expands the conditioned key unconditionally,
    causing a combinatorial explosion.

    A topological sort (dependencies first) is used.  Any key that has no
    inter-key dependencies keeps its original document order relative to other
    such keys, so the section hierarchy in the PDF is stable.
    """
    keys = list(sel_opts.keys())
    key_set = set(keys)

    # Build a dependency map: key → set of keys whose values must be known first.
    deps: dict[str, set[str]] = {k: set() for k in keys}
    for key, entries in sel_opts.items():
        for _val, _label, group_cond, option_cond in entries:
            for cond in (group_cond, option_cond):
                for token in cond.split():
                    if "=" in token:
                        dep_key = normalize_key(token.split("=", 1)[0])
                        if dep_key in key_set and dep_key != key:
                            deps[key].add(dep_key)

    # Kahn's algorithm: emit nodes whose dependencies are all satisfied.
    in_degree = {k: len(deps[k]) for k in keys}
    dependants: dict[str, list[str]] = {k: [] for k in keys}
    for k, dep_set in deps.items():
        for d in dep_set:
            dependants[d].append(k)

    queue = [k for k in keys if in_degree[k] == 0]
    ordered: list[str] = []
    while queue:
        node = queue.pop(0)
        ordered.append(node)
        for dependent in dependants[node]:
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)

    # If a cycle exists, fall back to document order for remaining keys.
    remaining = [k for k in keys if k not in set(ordered)]
    return ordered + remaining


def _build_combos(
    sel_opts: dict[str, list[tuple[str, str, str, str]]],
) -> list[tuple[dict[str, str], dict[str, str]]]:
    """Build the ordered list of (combo_dict, labels_dict) from selector options.

    All selector keys are treated as independent flat dimensions.  Keys are
    iterated in dependency order so that a key's ``show-cond`` can always be
    evaluated against an already-fixed partial combo, preventing combinatorial
    expansion of conditionally-hidden keys.  Labels are resolved by matching
    each option group's ``show-cond`` against the partial combo at the time the
    label is needed, so context-dependent labels (e.g. ``apt`` vs ``dnf`` for
    the same install-method value) are picked correctly.
    """
    combos: list[tuple[dict[str, str], dict[str, str]]] = []
    _iter_combos(_sorted_keys(sel_opts), sel_opts, {}, set(), {}, combos)
    return combos


def _combo_matches_spec(combo: dict[str, str], spec: dict[str, str]) -> bool:
    """Return True if *combo* satisfies every key in *spec* (a partial match).

    Keys absent from *spec* act as wildcards. Keys and values are normalized so
    specs can be written naturally (e.g. ``"Ubuntu"`` matches ``"ubuntu"``).
    Spec keys must exactly match the dimension names declared in the selector
    directives (the ``:key:`` values).
    """
    for raw_key, raw_val in spec.items():
        key = normalize_key(str(raw_key))
        want = normalize_key(str(raw_val))
        if key not in combo:
            return False
        if normalize_key(str(combo[key])) != want:
            return False
    return True


def _filter_combos_for_pdf(
    all_combos: list[tuple[dict[str, str], dict[str, str]]], specs: list[object]
) -> list[tuple[dict[str, str], dict[str, str]]]:
    """Keep only combos matching at least one spec dict in *specs*.

    Each entry of *specs* must be a dict of ``{dimension: value}`` constraints.
    Non-dict entries are ignored with a warning so a malformed config value
    degrades to "match nothing extra" rather than crashing the build.
    """
    valid_specs = []
    for spec in specs:
        if isinstance(spec, dict):
            valid_specs.append(spec)
        else:
            raise ExtensionError(
                f"rocm_docs_pdf_mock_selector_state: spec entries must be "
                f"dicts, got {spec!r}."
            )

    # Raise if any spec key doesn't match any dimension — catches typos and
    # mismatched key names (e.g. a key not declared as :key: in any selector).
    if valid_specs and all_combos:
        # Collect ALL unique dimension keys across every combo, not just the
        # first one.  Different selector branches can introduce keys that only
        # exist in certain combos (e.g. a sub-dropdown conditioned on another
        # selector's value), so a key may be absent from some combos entirely.
        known_keys: set[str] = set()
        for combo, _ in all_combos:
            known_keys.update(combo.keys())
        for spec in valid_specs:
            for raw_key in spec:
                if normalize_key(str(raw_key)) not in known_keys:
                    raise ExtensionError(
                        f"rocm_docs_pdf_mock_selector_state: spec key "
                        f"{raw_key!r} does not match any combo dimension. "
                        f"Available dimensions: {sorted(known_keys)}. "
                        f"Dimension names must match the :key: values "
                        f"declared in the selector directives."
                    )

    return [
        (combo, labels)
        for combo, labels in all_combos
        if any(_combo_matches_spec(combo, spec) for spec in valid_specs)
    ]


class SelectorPDFReorganizeTransform(SphinxPostTransform):
    """Reorganize selector-driven pages for PDF/LaTeX output.

    In HTML the selector widgets let users pick their configuration and see
    only the relevant content.  In a PDF that interactivity is lost, so the
    document is restructured: for every valid combination of selector values
    a dedicated section hierarchy is produced

        <key1 value> → <key2 value> → … → full guide

    so a reader can find the complete instructions for their setup in one
    place rather than scanning through all possible variants mixed together.
    The key order and names are discovered dynamically from the doctree.

    The transform only runs for the LaTeX builder and only when the page
    contains enough ``SelectedContent`` nodes to be worth reorganising
    (threshold: ≥ 10 nodes).
    """

    default_priority = 488  # before SelectorToSectionTransform (490)

    def apply(self, **_kwargs):
        """Reorganize the install chapter into per-combo sections for PDF output."""
        if self.app.builder.format != "latex":
            return

        # PDF generation disabled: skip the per-combo reorganization.
        pdf_setting = self.config.rocm_docs_pdf_mock_selector_state
        if not pdf_setting:
            return

        # When page-scoped, only process pages listed in the dict.
        # When True, process every page that has enough SelectedContent nodes.
        if isinstance(pdf_setting, dict):
            target_docnames = set(pdf_setting.keys())
        else:
            target_docnames = None  # all pages

        # In the LaTeX builder, post-transforms run on the assembled mega-doctree
        # (all pages inlined).  Each sub-document's sections are tagged with a
        # docname attribute by inline_all_toctrees.  Process each matching section.
        for chapter in self.document.findall(nodes.section):
            docname = chapter.get("docname")
            if target_docnames is not None and docname not in target_docnames:
                continue
            specs = (
                pdf_setting.get(docname, [])
                if isinstance(pdf_setting, dict)
                else None
            )
            self._reorganize_chapter(chapter, docname or "", specs)

    def _reorganize_chapter(
        self, chapter: nodes.section, docname: str, specs: list[object] | None
    ) -> None:
        """Reorganize one chapter section into per-combo sections for PDF output."""
        all_selected = list(chapter.findall(SelectedContent))
        if not all_selected:
            return

        # ------------------------------------------------------------------
        # Preserve the preamble: the chapter title and any non-selector,
        # non-section nodes before the first SelectedContent.
        # ------------------------------------------------------------------
        preamble = []
        first_selected_idx = None
        for i, child in enumerate(chapter.children):
            # A SelectedContent may be wrapped in a container/section; check
            # both the child itself and any descendants.
            if isinstance(child, SelectedContent) or list(
                child.findall(SelectedContent)
            ):
                first_selected_idx = i
                break
            if isinstance(child, _SELECTOR_UI):
                continue
            preamble.append(child.deepcopy())

        if first_selected_idx is None:
            return

        # Source pool: chapter children from the first SelectedContent onwards.
        # Everything before that index is already captured in the preamble and
        # must not be repeated inside every per-combo section.
        source_children = chapter.children[first_selected_idx:]

        # ------------------------------------------------------------------
        # Discover selector options from the doctree.
        # ------------------------------------------------------------------
        sel_opts = _collect_selector_options(chapter)
        all_combos = _build_combos(sel_opts)

        # specs is None → include all combos; a list → filter to matching ones.
        if specs is not None:
            total = len(all_combos)
            if all_combos:
                # Log ALL unique dimension keys across every combo so the
                # message is accurate even when different selector branches
                # introduce keys that only exist in certain combos.
                all_keys: set[str] = set()
                for combo, _ in all_combos:
                    all_keys.update(combo.keys())
                logger.info(
                    "rocm_docs_pdf_mock_selector_state[%r]: available combo "
                    "dimensions: %s",
                    docname,
                    sorted(all_keys),
                )
            all_combos = _filter_combos_for_pdf(all_combos, specs)
            logger.info(
                "rocm_docs_pdf_mock_selector_state[%r]: keeping %d of %d "
                "combinations for PDF.",
                docname,
                len(all_combos),
                total,
            )
            if not all_combos:
                raise ExtensionError(
                    f"rocm_docs_pdf_mock_selector_state[{docname!r}]: no "
                    f"combinations matched the given selector state. "
                    f"Check the selector state keys and values."
                )

        # ------------------------------------------------------------------
        # Build the new chapter contents: preamble + per-combo sections.
        #
        # The section hierarchy mirrors the selector key order discovered in
        # the doctree.  Each combo produces a path of (key, val) pairs; a
        # section is created for each step of the path on first encounter.
        # After all combos are processed, sections are connected bottom-up
        # so that only paths with actual content make it into the output.
        # ------------------------------------------------------------------
        new_children = list(preamble)

        # Omit keys that have only one distinct value across all filtered combos:
        # they add no discriminating information to the TOC and only deepen the
        # hierarchy unnecessarily.
        constant_keys: set[str] = set()
        if all_combos:
            all_combo_keys: set[str] = set()
            for combo, _ in all_combos:
                all_combo_keys.update(combo.keys())
            for k in all_combo_keys:
                values = {combo[k] for combo, _ in all_combos if k in combo}
                if len(values) <= 1:
                    constant_keys.add(k)

        # path_sections: tuple of (key, val) pairs → section node
        path_sections: dict[tuple[tuple[str, str], ...], nodes.section] = {}
        # paths that received content (directly or via a descendant)
        path_has_content: set[tuple[tuple[str, str], ...]] = set()

        # Key iteration order matching _build_combos (dependency-sorted).
        all_keys_ordered = _sorted_keys(sel_opts)

        for combo, labels in all_combos:
            # Build the ordered section path for this combo using document key
            # order; skip keys absent from this combo or constant across all combos.
            path: list[tuple[str, str, str]] = []
            for k in all_keys_ordered:
                if k not in combo or k in constant_keys:
                    continue
                val = combo[k]
                path.append((k, val, labels.get(k, val)))

            id_prefix = _make_pdf_id(*[val for _, val, _ in path])
            # id_remap accumulates old-ID → new-ID mappings produced by
            # _gather_content so we can update reference['refid'] after the
            # tree is built. IDs are assigned uniquely at construction time
            # (via make_unique_id inside _gather_content) rather than in a
            # post-pass so that no reference-resolved ID is ever renamed.
            id_remap: dict[str, str] = {}
            content_nodes: list[nodes.Node] = []
            _gather_content(
                source_children,
                combo,
                content_nodes,
                id_prefix,
                self.document,
                id_remap,
            )

            if not content_nodes:
                continue

            if not path:
                # All dimensions are constant — no section hierarchy needed;
                # attach content directly to the chapter's new children.
                new_children.extend(content_nodes)
                _remap_references(content_nodes, id_remap)
                continue

            # Create sections along the path (on first encounter).
            # Assign unique IDs at construction time to avoid post-pass renaming.
            for depth in range(len(path)):
                path_key = tuple((k, v) for k, v, _ in path[: depth + 1])
                if path_key not in path_sections:
                    _, _, lbl = path[depth]
                    raw_id = _make_pdf_id("pdf", *[v for _, v in path_key])
                    sec_id = make_unique_id(self.document, raw_id)
                    if raw_id != sec_id and id_remap is not None:
                        id_remap[raw_id] = sec_id
                    sec = nodes.section(ids=[sec_id], names=[sec_id])
                    sec += nodes.title(text=lbl)
                    path_sections[path_key] = sec

            # Attach content to the innermost section.
            innermost = tuple((k, v) for k, v, _ in path)
            for n in content_nodes:
                path_sections[innermost] += n
            _remap_references(content_nodes, id_remap)

            # Mark every ancestor path as having content.
            for depth in range(len(path)):
                path_has_content.add(
                    tuple((k, v) for k, v, _ in path[: depth + 1])
                )

        # Connect sections bottom-up (deepest first) and collect top-level ones.
        for path_key in sorted(path_sections, key=len, reverse=True):
            if path_key not in path_has_content:
                continue
            if len(path_key) == 1:
                new_children.append(path_sections[path_key])
            else:
                parent_key = path_key[:-1]
                if parent_key in path_sections:
                    path_sections[parent_key] += path_sections[path_key]

        # ------------------------------------------------------------------
        # Replace the chapter's children with the reorganised content.
        # ------------------------------------------------------------------
        chapter.children = []
        for child in new_children:
            child.parent = chapter
            chapter += child


class SelectorToSectionTransform(SphinxPostTransform):
    """Convert SelectedContent nodes to proper docutils structures for non-HTML builders.

    In HTML, SelectedContent nodes render as conditional show/hide sections driven
    by JavaScript. In static formats (LaTeX/PDF, text, man) there is no interactivity,
    so all content must be visible. This transform runs before the LaTeX translator:

    - Nodes with a ``:heading:`` option become proper docutils ``section`` nodes so
      that headings appear correctly in the PDF table of contents and body text.
    - Nodes without a heading are unwrapped in place — their children are spliced
      directly into the parent so all condition variants render sequentially, which
      is correct behaviour for a static format.

    The HTML path is untouched: the transform exits immediately for HTML builds.
    The Markdown path (llms-full.txt) is also left untouched — it runs under the
    HTML builder and renders SelectedContent via the dedicated Markdown node
    handler instead.
    """

    default_priority = 490  # run before MatrixToTableTransform (500)

    def apply(self, **_kwargs):
        """Convert SelectedContent nodes to docutils sections for non-HTML builders."""
        if self.app.builder.format == "html":
            return

        pdf_setting = self.config.rocm_docs_pdf_mock_selector_state

        # PDF generation disabled: skip converting SelectedContent for LaTeX.
        # The nodes' latex visitors are no-ops, so the conditional content is
        # simply omitted from the PDF. Other non-HTML builders still convert.
        if self.app.builder.format == "latex" and not pdf_setting:
            return

        # For page-scoped dicts, determine which docnames the reorganizer
        # already processed.  Nodes on *unlisted* pages must be removed here
        # rather than unwrapped — the config contract states that unlisted
        # pages are excluded from PDF output, so exposing all their variants
        # would contradict that.
        listed_docnames: set[str] | None = None
        if self.app.builder.format == "latex" and isinstance(pdf_setting, dict):
            listed_docnames = set(pdf_setting.keys())

        def _chapter_docname(node: nodes.Node) -> str | None:
            """Walk up to the nearest section with a docname attribute."""
            n: nodes.Node | None = node
            while n is not None:
                dn = n.get("docname") if hasattr(n, "get") else None
                if dn:
                    return str(dn)
                n = n.parent
            return None

        # Collect upfront so that replacing nodes mid-traversal is safe.
        for node in list(self.document.findall(SelectedContent)):
            if node.parent is None:
                continue  # already detached by a parent replacement

            # Guard 1: :no-pdf: blocks must be removed, not unwrapped.
            if self.app.builder.format == "latex" and node.get("no-pdf"):
                node.parent.remove(node)
                continue

            # Guard 2: nodes on pages not listed in the dict setting are
            # removed so that unlisted pages contribute no selector content.
            if listed_docnames is not None:
                dn = _chapter_docname(node)
                if dn not in listed_docnames:
                    node.parent.remove(node)
                    continue

            heading = node.get("heading", "")

            if heading:
                # Replace with a proper section so the heading appears in the PDF.
                # Headings repeat across conditional blocks (e.g. "Prerequisites"
                # under each OS), so the ID must be deduplicated against the
                # document or cross-references collapse onto the first match.
                sec_id = make_unique_id(self.document, heading)
                section = nodes.section(ids=[sec_id], names=[sec_id])
                section += nodes.title(text=heading)
                for child in node.children[:]:
                    section += child
                node.replace_self(section)
            else:
                # No heading — splice children directly into the parent so the
                # SelectedContent wrapper disappears without dropping any content.
                # replace_self routes through Element.replace, which reparents
                # each spliced child (sets .parent/.document); a raw children
                # slice assignment would leave them pointing at the detached
                # wrapper and corrupt later transforms/translators.
                node.replace_self(node.children[:])
