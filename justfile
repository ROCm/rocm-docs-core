venvdir := ".venv"
base-python := "python"
binfolder := if os_family() == "windows" {"Scripts"} else {"bin"}
bindir := venvdir / binfolder
python := bindir / "python"
ruff_exe := bindir / "ruff"

verbose_errors := "false"

set windows-shell := ["powershell.exe", "-c"]

[unix]
_virtualenv:
	[ -d {{venvdir}} ] || {{base-python}} -m venv {{venvdir}}

[windows]
_virtualenv:
	if (-Not (Test-Path {{venvdir}} -PathType Container)) { {{base-python}} -m venv {{venvdir}} }

_install-defusedxml: _virtualenv
	{{python}} -m pip install defusedxml

_install-pip-tools: _virtualenv
	{{python}} -m pip install pip-tools

# Install development and runtime dependencies
deps: _install-pip-tools
	{{python}} -m piptools sync requirements.txt
	{{python}} -m mypy --non-interactive --install-types src

# (Re-)lock the dependencies with pip-compile
lock-deps +extra_args="":
	{{python}} -m piptools compile --all-extras {{extra_args}} pyproject.toml

# Install git-hooks for development
install-git-hooks:
	{{python}} -m pre_commit install

# Set up a development environment
devenv: deps install-git-hooks && install

# Install the package in editable mode
install:
	{{python}} -m pip install -e ".[api_reference]" \
		--config-settings editable_mode=strict

build:
	{{python}} -m build

_format extra_args +files:
	{{python}} -m black --config pyproject.toml {{extra_args}} {{files}}

format +files="src tests docs": (_format "" files)
check-format +files="src tests docs": (_format "--check" files)

_isort extra_args +files:
	{{python}} -m isort --settings-path pyproject.toml {{extra_args}} {{files}}

# Sort imports
isort +files="src tests docs": (_isort "" files)
# Check if imports are correctly sorted
check-isort +files="src tests docs": (_isort "--check" files)

_ruff extra_args +files:
	{{ruff_exe}} check --config pyproject.toml {{extra_args}} {{files}}

# Run ruff to lint files
ruff +files="src tests": (_ruff "" files)
# Run ruff and autolint
fix-ruff +files="src tests": (_ruff "--fix --exit-non-zero-on-fix" files)

_run-hook hook:
	@{{python}} -m pre_commit run --all-files {{ if verbose_errors == "true" {"--show-diff-on-failure"} else {""} }} {{hook}}

# Run basic pre-commit hooks
hooks: (_run-hook "check-yaml") (_run-hook "check-json") (_run-hook "check-toml") (_run-hook "end-of-file-fixer") (_run-hook "file-contents-sorter") (_run-hook "trailing-whitespace")

# Run linters, no files are modified
lint +files="src tests": (ruff "" files) hooks
# Run linters, trying to fix errors automatically
fix-lint +files="src tests": (fix-ruff files) hooks

# Run type-checking
mypy +files="src tests":
	{{python}} -m mypy --config-file pyproject.toml {{files}}

# Run formatting, linters, imports sorting, fixing errors if possible
fix-codestyle +files="src tests": (fix-lint files) (isort files) (format files)
alias codestyle := fix-codestyle

# Check formatting, linters, imports sorting
check-codestyle +files="src tests": (lint files) (check-isort files) (check-format files) (mypy files)
alias check := check-codestyle

docs:
	{{python}} -m sphinx -j auto -T -b html -d docs/_build/doctrees \
		--color -D language=en docs docs/_build/html

test +files="src tests": _install-defusedxml
	{{python}} -m pytest {{files}}

_check-commit-mesg file:
	{{python}} -m commitizen check --allow-abort --commit-msg-file {{file}}

_check-commit-range range:
	{{python}} -m commitizen check --rev-range {{range}}
