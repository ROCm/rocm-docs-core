venvdir := ".venv"
base-python := "python3"
bindir := if os_family() == "windows" {"Scripts"} else {"bin"}
python := venvdir / bindir / "python3"

set windows-shell := ["powershell.exe", "-c"]

[unix]
_virtualenv:
	[ -d {{venvdir}} ] || {{base-python}} -m virtualenv {{venvdir}}

[windows]
_virtualenv:
	if (-Not Test-Path {{venvdir}} -PathType Container) { {{base-python}} -m virtualenv {{venvdir}} }

_install-pip-tools: _virtualenv
	{{python}} -m pip install pip-tools

# Install development and runtime dependencies
deps: _install-pip-tools
	{{python}} -m piptools sync requirements.txt
	{{python}} -m mypy --non-interactive --install-types src

# (Re-)lock the dependencies with pip-compile
lock-deps:
	{{python}} -m piptools compile --all-extras pyproject.toml

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

format +files="src docs": (_format "" files)
check-format +files="src docs": (_format "--check" files)

_isort extra_args +files:
	{{python}} -m isort --settings-path pyproject.toml {{extra_args}} {{files}}

# Sort imports
isort +files="src docs": (_isort "" files)
# Check if imports are correctly sorted
check-isort +files="src docs": (_isort "--check" files)

_ruff extra_args +files:
	ruff --config pyproject.toml {{extra_args}} {{files}}

_run-hook hook:
	@{{python}} -m pre_commit run --all-files {{hook}}

# Run basic pre-commit hooks
hooks: (_run-hook "check-yaml ") (_run-hook "check-json") (_run-hook "check-toml") (_run-hook "end-of-file-fixer") (_run-hook "trailing-whitespace")

# Run linters, no files are modified
lint +files="src": (_ruff "" files) hooks
# Run linters, trying to fix errors automatically
fix-lint +files="src": (_ruff "--fix --exit-non-zero-on-fix" files) hooks

# Run type-checking
mypy +files="src":
	{{python}} -m mypy --config-file pyproject.toml {{files}}

# Run formatting, linters, imports sorting, fixing errors if possible
fix-codestyle +files="src": (fix-lint files) (isort files) (format files)
alias codestyle := fix-codestyle

# Check formatting, linters, imports sorting
check-codestyle +files="src": (lint files) (check-isort files) (check-format files) (mypy files)
alias check := check-codestyle

docs:
	{{python}} -m sphinx -j auto -T -b html -d docs/_build/doctrees \
		--color -D language=en docs docs/_build/html
