---
myst:
    html_meta:
        "description": "How rocm-docs-core reads shared build data from a local rocm-docs-common checkout"
        "keywords": "rocm-docs-common, shared data, build performance, rate limit, projects.yaml"
---

# Local common data

`rocm_docs` reads its shared build-data files from a local checkout of the
[`rocm-docs-common`](https://github.com/neon60/rocm-docs-common) repository
instead of fetching them from GitHub on every build.

The shared files are:

- `data/latest_version.txt`
- `data/release_candidate.txt`
- `data/rocm_toolkits.txt`
- `data/google_site_verification.txt`
- `data/projects.yaml` (the intersphinx project mapping)

## Benefits of local common data

Previously each of these files was fetched from `raw.githubusercontent.com` on
every build, and the version and toolkit files were fetched once per page.
`projects.yaml` also required an unauthenticated GitHub API call. Across the
parallel component-repository CI this produced hundreds of requests per build
and hit GitHub rate limits, and the retry loops could stall a build for minutes
on throttling.

Reading from a pinned local checkout removes those requests and the retry
loops, and makes builds depend on committed data rather than a moving branch.

## Determining the common data directory

At `config-inited`, `rocm_docs` resolves the checkout location in this order
(see `rocm_docs.common.ensure_common_dir`):

1. The `rocm_docs_common_dir` config value, if set in `conf.py`.
2. The `ROCM_DOCS_COMMON_DIR` environment variable, if set.
3. Otherwise, clone `rocm-docs-common` (tip of `main`) to
   `<repo>/rocm-docs-common`, or refresh it to the tip of `main` if it already
   exists, and use that.

The resolved path is stored back on the config so the theme and projects reads
reuse it. There is no per-file remote fallback: if the resolved directory or a
requested file is missing, the build fails rather than silently fetching from a
moving branch.

## Local builds

No setup is required. When you run `sphinx-build`, `rocm_docs` clones
`rocm-docs-common` to the repository root if the folder is absent. If the folder
is already present, `rocm_docs` fast-forwards it to the tip of `main` so
repeated local builds do not read stale data. This refresh is best-effort: if it
fails (for example, you are offline), the build logs a warning and uses the
existing checkout. Delete the directory to force a fresh clone. The clone
directory is listed in `.gitignore`, so it is never committed.

To use a checkout you already have — for example, to test unreleased common
data — point `rocm_docs_common_dir` at it in `conf.py`:

```python
rocm_docs_common_dir = "/path/to/rocm-docs-common"
```

or set the environment variable:

```bash
export ROCM_DOCS_COMMON_DIR=/path/to/rocm-docs-common
```

The config value takes precedence over the environment variable.

## Read the Docs builds

A `post_checkout` job in `.readthedocs.yaml` clones `rocm-docs-common` (tip of
`main`) to the repository root before dependencies are installed. This is the
same path `ensure_common_dir` would clone to, so on Read the Docs the automatic
clone is a no-op and the build reads the data provided by the job.

To pin a different checkout on Read the Docs, set `rocm_docs_common_dir` in
`conf.py` or `ROCM_DOCS_COMMON_DIR` in the build environment; the resolver then
defers to it and the cloned directory is unused.
