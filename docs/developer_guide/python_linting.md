---
myst:
    html_meta:
        "description": "Tools used for checking correctness in Python code"
        "keywords": "Python linting tool, Error checker, Documentation configuration"
---

# Python Linting

The following list of tools is used for checking correctness in Python code.
These tools are set up to run as [git pre-commit hooks](https://pre-commit.com/)
via [pre-commit](https://github.com/pre-commit/pre-commit).

- [`Ruff`](https://github.com/astral-sh/ruff) for linting
  - [Usage](https://github.com/astral-sh/ruff#usage)
- [`Mypy`](https://github.com/python/mypy) for static type checking
  - [Usage](https://github.com/python/mypy#quick-start)
- [`Black`](https://github.com/psf/black) for code formatting
  - [Usage](https://github.com/psf/black#usage)
- [`isort`](https://github.com/PyCQA/isort) for import sorting
  - [Usage](https://github.com/PyCQA/isort#using-isort)

Some non-Python-specific hooks are also enabled:

- Check `yaml`, `toml`, and `json` validity
- Check for no trailing whitespaces and additional newline at the end of files
