# Linking

## Cross References

When making links that cross-reference documentation sites, the following
format should be used:

```Markdown
{doc}`Text here<project_name:path/to/page_name>`
```

### Example

The following Markdown:

```Markdown
{doc}`ROCm Documentation<rocm:reference/all>`
```

will be rendered as the follwoing link:

{doc}`ROCm Documentation<rocm:reference/all>`

### Project Names

The [`projects.yaml`](https://github.com/RadeonOpenCompute/rocm-docs-core/blob/develop/src/rocm_docs/data/projects.yaml)
configuration file contains the names of projects
that should be used when making links that cross-reference documentation sites.
