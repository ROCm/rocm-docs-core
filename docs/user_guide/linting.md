---
myst:
    html_meta:
        "description": "Linting ensures correct Markdown and ReStructuredText formatting on every pull request"
        "keywords": "Formatting PR, Formatting pull requests, Linting checks, Documentation settings"
---

# Linting

`rocm-docs-core` has linting to ensure correct Markdown and ReStructuredText
formatting on every pull request (PR) via GitHub Actions.

If a PR fails linting, the errors must be addressed before it can be merged.

The results of linting is viewable in the "Checks" tab for a PR.

## Markdown Linting

The current linter used for Markdown is [`markdownlint`](https://github.com/DavidAnson/markdownlint),
which uses the [following rules](https://github.com/DavidAnson/markdownlint/blob/main/doc/Rules.md).

### Optional

`markdownlint` can also be installed and run locally using the [`markdownlint` extension](https://marketplace.visualstudio.com/items?itemName=DavidAnson.vscode-markdownlint) on [Visual Studio Code](https://code.visualstudio.com/Download).
