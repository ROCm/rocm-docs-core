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
