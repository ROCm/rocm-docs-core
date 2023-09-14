# Linking

## Cross References to Other Projects

When making links that cross-reference documentation sites, the following
format should be used:

```Markdown
{doc}`Text here<project_name:path/to/page_name>`
```

The [`projects.yaml`](https://github.com/RadeonOpenCompute/rocm-docs-core/blob/develop/src/rocm_docs/data/projects.yaml)
configuration file contains the names of projects
that should be used when making links that cross-reference documentation sites.

### Example

The following Markdown:

```Markdown
{doc}`ROCm Documentation<rocm:reference/all>`
```

will be rendered as the following link:

{doc}`ROCm Documentation<rocm:reference/all>`

## Other

For other links, usual Markdown conventions should be used.

### Example: Absolute Links to External Sites

The following Markdown:

```Markdown
[Link Text](https://github.com/RadeonOpenCompute/ROCm)
```

will be rendered as the following link:

[Link Text](https://github.com/RadeonOpenCompute/ROCm)

### Example: Relative Links to Current Project

The following Markdown:

```Markdown
[Link Text](../index)
```

will be rendered as the following link:

<!-- markdown-link-check-disable-next-line -->
[Link Text](../index)
