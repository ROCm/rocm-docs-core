---
myst:
    html_meta:
        "description": "Make ROCm documentation accessible to AI agents and coding assistants using a generated index and full-text file, plus the per-page download button"
        "keywords": "LLM documentation, AI agent, download button, ROCm docs core user guide"
---

# LLM-friendly output

`rocm-docs-core` supports three features that make documentation more accessible to AI coding assistants and agents:

- A per-page **download button** that lets users and agents copy page content directly into an AI context window.
- A generated **`llms.txt`** index file that AI agents can discover and use as an entry point to the documentation.
- A generated **`llms-full.txt`** file that combines the prose documentation into a single document.

All three features are opt-in and configured in `conf.py`. The `llms.txt` and `llms-full.txt` files are produced from the same setting and are generated from Sphinx's resolved doctree. As a result, RST and Markdown sources are handled identically and constructs such as tables, code blocks, math, footnotes, and cross-references are preserved.

## Per-page download button

The Sphinx Book Theme includes a built-in download button that lets readers download the current page as Markdown or RST. Enable it by setting `use_download_button` in `html_theme_options`:

```python
html_theme_options = {
    "use_download_button": True,
}
```

Once enabled, a download icon appears on each page. Clicking it downloads the source file for that page, which users and agents can paste directly into an AI context window.

## Enabling generation

Set `rocm_docs_generate_llms_full = True` in `conf.py` to generate both `llms.txt` and `llms-full.txt`:

```python
rocm_docs_generate_llms_full = True
```

After each successful build, both files are written to the Sphinx output directory alongside the built HTML. For a standard build, this is `docs/_build/html/`, making them available at `{project_url}/llms.txt` and `{project_url}/llms-full.txt`. Neither file is generated if the build fails.

### Setting the base URL

Links in the generated files point to your published documentation. Set the base URL with `rocm_docs_llms_base_url` in `conf.py`:

```python
rocm_docs_llms_base_url = "https://rocm.docs.amd.com/projects/<project>/en/latest"
```

If `rocm_docs_llms_base_url` is unset, the generator falls back to `html_baseurl`, then to the `READTHEDOCS_CANONICAL_URL` environment variable. If none is available, links are written relative to the output root.

## `llms.txt`

`llms.txt` is a curated index of your documentation pages, following the [llmstxt.org](https://llmstxt.org/) convention for AI agent documentation discovery. It is also compatible with [Read the Docs llms-txt support](https://docs.readthedocs.com/platform/stable/reference/llms-txt.html).

The index is generated automatically, so it cannot drift from the docs:

- The section structure and ordering follow the project's table of contents (`sphinx_external_toc`). Projects without an external TOC fall back to all documents in the project, sorted by name.
- Each entry's description comes from that page's `description` metadata, set with a MyST `html_meta` field in Markdown or a `.. meta::` directive in RST. When no description is present, the page title is used.
- The project description (the blockquote summary) comes from the root page's description.
- External URL entries in the TOC are included as links.

To give a page a description, add it to the page's metadata. In Markdown:

```yaml
---
myst:
  html_meta:
    "description lang=en": "One-sentence description of the page."
---
```

In RST:

```rst
.. meta::
   :description lang=en: One-sentence description of the page.
```

## `llms-full.txt`

`llms-full.txt` collects all documentation pages into a single Markdown document, with the `llms.txt` index as its header. Each page follows a `---` separator and a `Source:` link to the published page.

The content is produced from Sphinx's resolved doctree using the Markdown translator from [`sphinx-markdown-builder`](https://pypi.org/project/sphinx-markdown-builder/), rather than a text filter. As a result:

- RST and Markdown sources produce identical, clean Markdown output.
- Tables, fenced code blocks (with language tags), math, footnotes, and cross-references are preserved. Cross-references are rewritten to absolute URLs using the configured base URL.
- Generated API-reference pages (for example, Doxygen output under `doxygen/`) are excluded from the inlined prose; they remain linked from the index where present in the TOC.

### Excluding large pages from the full text

Some pages can dominate `llms-full.txt` due to their size. Use `rocm_docs_llms_full_exclude` to keep such pages out of the inlined prose while still listing them in `llms.txt`. It accepts a list of document names or glob patterns, matched against each page's path relative to the documentation root (without the file extension):

```python
rocm_docs_llms_full_exclude = [
    "reference/gpu-atomics-operation",
    "reference/*-performance-counters",
]
```

Excluded pages still appear in the `llms.txt` index, so they remain discoverable.

## Example configuration

The following example enables all three features together:

```python
html_theme_options = {
    "use_download_button": True,
}

rocm_docs_generate_llms_full = True
rocm_docs_llms_base_url = "https://rocm.docs.amd.com/projects/<project>/en/latest"
```
