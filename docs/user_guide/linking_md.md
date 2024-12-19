---
myst:
    html_meta:
        "description": "Setting up links in Markdown to other projects, current project and external sites in ROCm documentation"
        "keywords": "Markdown links, Project linking, Project reference, Adding links in Markdown, Documentation settings"
---

# Linking in Markdown

## Markdown

### Cross References to Other Projects

The [`projects.yaml`](https://github.com/ROCm/rocm-docs-core/blob/develop/src/rocm_docs/data/projects.yaml)
configuration file contains the names of projects
that should be used when making links that cross-reference documentation sites.

When making links that cross-reference documentation sites, the following
format should be used:

```Markdown
{doc}`Text here<project_name:path/to/page_name>`
```

Cross-references are achieved via Intersphinx.
For more information, refer to the
[Sphinx documentation](https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html)
or [Read the Docs documentation](https://docs.readthedocs.io/en/stable/guides/intersphinx.html)
on Intersphinx.

#### Example

The following Markdown:

```Markdown
{doc}`ROCm Documentation<rocm:about/license>`
```

will be rendered as the following link:

{doc}`ROCm Documentation<rocm:about/license>`

### Relative Links to Current Project

#### Example

The following Markdown:

```Markdown
[Link Text](../index)
```

will be rendered as the following link:

[Link Text](../index)

### Absolute Links to External Sites

For other links, usual Markdown conventions should be used.

#### Example

The following Markdown:

```Markdown
[Link Text](https://github.com/ROCm/ROCm)
```

will be rendered as the following link:

[Link Text](https://github.com/ROCm/ROCm)
