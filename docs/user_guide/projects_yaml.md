# External Intersphinx Project Mapping

Projects should be defined in `projects.yaml` and should set which key they correspond to by setting external_projects_current_project to this key.

## Example

Given the following `projects.yaml` file:

```
projects:
  python: https://docs.python.org/3/
  rtd: https://docs.readthedocs.io/en/stable/
  sphinx: https://www.sphinx-doc.org/en/master/
  rocm-docs-core: [https://rocm.docs.amd.com/projects/rocm-docs-core/en/${version}](https://rocm.docs.amd.com/projects/rocm-docs-core/en/$%7Bversion%7D)
```

The `conf.py` from `rocm-docs-core` should contain:

```
external_projects_current_project = "rocm-docs-core"
```

Adds support for specifying the "development" branch for each project defined in `projects.yaml`.
This is achieved by setting the `development_branch` key for the project:

```
projects:
  ...
  project:
    target: <target-url>
    development_branch: master
```

With this the mapping between projects is changed to the following:
  
  Development branches map between each other.
  Essentially, links on project A's "develop" branch point to the project B's "master" branch.
  Vice-versa if A has set its `development_branch` to "develop" and B sets it to "master".

  Symbolic versions "latest" and "stable" map to themselves in other projects.

  Any other branch maps to "latest".
