# Linking

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

Cross references to anchors or arbitrary locations in documentation
can be done using labels.

See the [Sphinx documentation on cross-referencing arbitrary locations](https://www.sphinx-doc.org/en/master/usage/referencing.html#ref-role) for information on labels.

The format using a label would appear as follows:

```Markdown
:ref:`Text here<project_name:label_name>`
```

#### Example

The following Markdown:

```Markdown
{doc}`ROCm Documentation<rocm:about/license>`

:ref:`ROCm for AI Install<rocm:rocm-for-ai-install>`
```

will be rendered as the following link:

{doc}`ROCm Documentation<rocm:about/license>`

:ref:`ROCm for AI Install<rocm:rocm-for-ai-install>`

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

## Table of Contents

### Syntax

Variables of the form `${<variable>}` are substituted, currently the following
list is supported:

- `${branch}` or `{branch}`: the name of the current branch
- `${url}` or `{url}`: GitHub URL of the current project
- `${project:<project_name>}`: base URL of the documentation of `<project_name>`
based on Intersphinx mapping

#### Example

```in
    - url: "{url}/tree/{branch}"
    - url: ${project:python}
    - url: ${project:rocm-docs-core}
    - url: ${project:hipify}
```
