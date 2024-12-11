---
myst:
    html_meta:
        "description": "Just is a command runner used to quickly setup an environment for documentation development"
        "keywords": "Documentation development environment, Environment for documentation development, Just, Documentation configuration"
---

# Just

[`just`](https://github.com/casey/just) is a command runner used to
quickly setup an environment for documentation development.

The aim is to make contributing to `rocm-docs-core` more approachable
by providing ready-to-use environments for development.

## Usage

### Setting up a development environment

`just devenv`

This creates a Python virtual environment,
installs the dependencies, and sets up the pre-commit hooks.

### Running linting commands

> These commands work on both Linux and Windows

`just check-codestyle`

Check files for formatting errors and report them.

`just fix-codestyle`

Automatically fix errors that have suggested fixes.

## GitHub

GitHub Actions CI is extended to run these tools on PRs
(using the `just`-based entry-points).

Development container setup and settings are added
for Visual Studio Development containers (and GitHub Codespaces) and Gitpod.

- [VS Code Dev Containers Guide](https://code.visualstudio.com/docs/devcontainers/containers)
  - [Dev Container Dockerfile and Configuration](https://github.com/ROCm/rocm-docs-core/tree/develop/.devcontainer)
- [Gitpod Guide](https://www.gitpod.io/docs/introduction/getting-started)
  - [Gitpod Configuration](https://github.com/ROCm/rocm-docs-core/blob/develop/.gitpod.yml)
