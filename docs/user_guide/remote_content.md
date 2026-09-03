---
myst:
    html_meta:
        "description": "Include RST content from another ROCm repository at the matching branch or tag using the remote-content directive"
        "keywords": "remote-content, remote content, cross-repo include, branch-aware, ROCm docs core user guide"
---

# Remote content

Use the `remote-content` directive to pull an `.rst` file from another GitHub
repository into the current page at build time. It selects the branch or tag of
the source repository that matches the version being built, so a release build
inlines release content and a development build inlines development content.

Beyond inlining, the directive rewrites `:doc:` cross-references to external
URLs (or remaps them to local pages), downloads referenced images, applies text
and regex replacements, adds widths to CSV tables, and can fix common LaTeX math
issues.

## Enabling the extension

The directive is opt-in. Add it to `extensions` in `conf.py`:

```python
extensions = [
    "rocm_docs",
    "rocm_docs.remote_content",
]
```

## Basic usage

```rst
.. remote-content::
   :repo: ROCm/ROCm
   :path: docs/about/what-is-rocm.rst
   :default_branch: develop
```

On a release build (a `docs-X.Y.Z` branch, or a Read the Docs tag build), the
directive fetches `docs/about/what-is-rocm.rst` from the matching tag. Otherwise
it falls back to `default_branch`.

## Version selection

The target ref is chosen as follows:

- If the build is a **release** (the `version` is `X.Y.Z` and one of: the local
  branch is a `docs/` branch, `READTHEDOCS_VERSION_TYPE` is `tag`, or the version
  appears in the `READTHEDOCS_VERSION` slug), the ref is `<tag_prefix><version>`.
- Otherwise the ref is `default_branch`.

If a release fetch fails (for example, the tag does not exist yet), the directive
retries once against `default_branch`.

## Options

| Option | Description |
| --- | --- |
| `repo` | Source repository as `owner/name` (required). |
| `path` | Path to the `.rst` file within the source repo (required). |
| `default_branch` | Branch to use when the build is not a release, and as the release fallback. |
| `tag_prefix` | Prefix prepended to the version to form the release tag (e.g. `docs-`). |
| `start_line` | Include the file starting from this line number. |
| `replace` | Literal text replacements, `old\|new`, multiple separated by `;;`. |
| `replace_re` | Regex replacements, `pattern\|replacement` (DOTALL; `\n` in the replacement becomes a newline), multiple separated by `;;`. |
| `project_name` | Override the project name used when building external `:doc:` URLs. |
| `docs_base_url` | Override the base URL used for external `:doc:` URLs. |
| `doc_ignore` | `:doc:` targets to leave unconverted, separated by `;;`. |
| `doc_remap` | Remap `:doc:` targets to local pages: `old\|new` or `old\|new_text\|new`, separated by `;;`. |
| `csv_widths` | Add a `:widths:` value (e.g. `33 67`) to CSV tables that lack one. |
| `fix_latex_math` | Set to `true` to escape underscores inside `\text{}` in math. |

### Handling `:doc:` references

By default, each `:doc:` role in the fetched content is rewritten to an absolute
URL on the published documentation site, so links resolve from the page that
inlined the content. You can change this per target:

- **`doc_ignore`** leaves a target as a normal `:doc:` role (useful when the
  target also exists locally or is resolved by intersphinx).
- **`doc_remap`** rewrites a target to a different **local** page. Use
  `old|new` to keep the original link text, or `old|new_text|new` to also
  change the displayed text.

Namespaced references such as `:doc:`rocm:about/release-notes`` are left
untouched so intersphinx can resolve them, unless a `doc_remap` entry matches.

## Configuration

The base URL used to build external `:doc:` links defaults to
`https://rocm.docs.amd.com/projects`. Override it globally in `conf.py`:

```python
rocm_docs_remote_content_docs_base = "https://rocm.docs.amd.com/projects"
```

The per-directive `docs_base_url` option takes precedence over this value.

## Images

Images referenced by the fetched content are downloaded into
`_remote_images/<owner>_<name>/` under the Sphinx source directory and the image
nodes are updated to point at the local copies, so they render without depending
on the remote host at serve time. Absolute image URLs are left unchanged.
