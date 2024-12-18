---
myst:
    html_meta:
        "description": "Setting up links in the Table of Contents for ROCm documentation"
        "keywords": "Links in TOC, Links in table of content, Documentation TOC, Documentation table of content, Document index, Documentation settings"
---

# Linking in the Table of Contents

## Syntax

Variables of the form `${<variable>}` are substituted, currently the following
list is supported:

- `${branch}` or `{branch}`: the name of the current branch
- `${url}` or `{url}`: GitHub URL of the current project
- `${project:<project_name>}`: base URL of the documentation of `<project_name>`
based on Intersphinx mapping

### Example

```in
    - url: "{url}/tree/{branch}"
    - url: ${project:python}
    - url: ${project:rocm-docs-core}
    - url: ${project:hipify}
```
