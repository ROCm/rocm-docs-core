---
myst:
    html_meta:
        "description": "Defining external intersphinx project mapping"
        "keywords": "Intersphinx, project mapping, Documentation configuration"
---

# External Intersphinx Project Mapping

Projects should be defined in `projects.yaml` and should set which key they correspond to by setting external_projects_current_project to this key.

## Example

Given the following `projects.yaml` file:

```yaml
projects:
  python: https://docs.python.org/3/
  rtd: https://docs.readthedocs.io/en/stable/
  sphinx: https://www.sphinx-doc.org/en/master/
  rocm-docs-core: https://rocm.docs.amd.com/projects/rocm-docs-core/en/${version}
```

The `conf.py` from `rocm-docs-core` should contain:

```python3
external_projects_current_project = "rocm-docs-core"
```

Adds support for specifying the "development" branch for each project defined in `projects.yaml`.
This is achieved by setting the `development_branch` key for the project:

```yaml
projects:
  ...
  project:
    target: <target-url>
    development_branch: master
```

With this the mapping between projects is changed to the following:

Development branches map between each other.
Essentially, links on project A's `develop` branch point to the project B's `master` branch.
Vice-versa if A has set its `development_branch` to `develop` and B sets it to `master`.

Symbolic versions "latest" and "stable" map to themselves in other projects.

Any other branch maps to "latest".

## Explicitly list external projects

By default the inventories of all external projects defined in `projects.yaml`
will be downloaded. This can take a long time as it requires a network request
for each external project.

The `external_projects` configuration option can be set to a list with the names
of remote projects to fetch inventories from & enable links to.
The list must be a subset of the project names defined in `projects.yaml`.
The default value of `"all"` means to fetch all projects.

Intersphinx references to projects that are not in `external_projects` will not
be resolved. References in the the TOC like `${project:project_name}` will
continue to be resolved to the URL of `project_name`, even if `project_name` is
not set in `external_projects` (but it's defined in `projects.yaml`).

## Building before the external projects are public

Intersphinx normally downloads `<target>/objects.inv` from the public URL of
each project, which fails for docs that are not published yet. To build ahead of
time, set `external_projects_inventory_url` (or the environment variable
`ROCM_DOCS_INVENTORY_URL`) to a template for a non-public location of the
inventories:

```python
external_projects_inventory_url = "https://private.example.com/{path}/objects.inv"
```

Available placeholders:

- `{project}`: the project name in `projects.yaml`
- `{target}`: the resolved public target URL, without trailing slash
- `{path}`: the path component of the target, without leading or trailing slash
- `{token}`: the value of the environment variable `ROCM_DOCS_INVENTORY_TOKEN`,
  for example to use as `https://user:{token}@host/...`

Only the inventory is read from this location. The target is unchanged, so links
in the built HTML already point to the final public URLs and the docs don't need
to be rebuilt once published. If the inventory can't be fetched, Sphinx falls
back to the public location. Projects that set an explicit `inventory` in
`projects.yaml` are not affected.

Sphinx hides the user and password of a URL in its log output, but not query
parameters, so prefer basic authentication over a token in the query string.
