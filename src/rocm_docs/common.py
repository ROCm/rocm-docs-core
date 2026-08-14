"""Access to shared data files from the rocm-docs-common checkout.

Data files that used to be fetched from GitHub on every build (version files,
the intersphinx project mapping, etc.) are now read from a local checkout of
the ``rocm-docs-common`` repository.

The checkout location is resolved in this order:

1. The ``rocm_docs_common_dir`` Sphinx config value (set in ``conf.py``), when
   an explicit path is passed to these functions.
2. The ``ROCM_DOCS_COMMON_DIR`` environment variable.

There is intentionally no remote fallback: if neither is set, or a requested
file is missing, the build fails. Builds must use the pinned common data rather
than silently diverging by fetching from a moving branch.
"""

from __future__ import annotations

import os
from pathlib import Path

COMMON_DIR_ENV = "ROCM_DOCS_COMMON_DIR"
COMMON_DIR_CONFIG = "rocm_docs_common_dir"


def get_common_dir(explicit_dir: str | os.PathLike[str] | None = None) -> Path:
    """Return the rocm-docs-common checkout directory.

    Args:
        explicit_dir: An explicit path (typically the ``rocm_docs_common_dir``
            config value). Takes precedence over the environment variable when
            set. A falsy value (``None`` or empty string) is ignored so callers
            can pass an unset config value directly.

    Raises:
        RuntimeError: if no path is configured, or it does not point to an
            existing directory.
    """
    value: str | os.PathLike[str] | None = explicit_dir or os.environ.get(
        COMMON_DIR_ENV
    )
    if not value:
        raise RuntimeError(
            f"The rocm-docs-common directory is not set. Set the "
            f"'{COMMON_DIR_CONFIG}' config value in conf.py or the "
            f"{COMMON_DIR_ENV} environment variable to a checkout of "
            "rocm-docs-common so the build can read shared data files."
        )

    common_dir = Path(value)
    if not common_dir.is_dir():
        raise RuntimeError(
            f"The rocm-docs-common directory {os.fspath(value)!r} does not "
            "point to a directory."
        )
    return common_dir


def read_common_file(
    relative_path: str,
    explicit_dir: str | os.PathLike[str] | None = None,
) -> str:
    """Read a UTF-8 text file from the rocm-docs-common checkout.

    Args:
        relative_path: Path to the file relative to the checkout root, e.g.
            ``"data/latest_version.txt"``.
        explicit_dir: An explicit checkout path (typically the
            ``rocm_docs_common_dir`` config value); see :func:`get_common_dir`.

    Raises:
        RuntimeError: if the common directory or the file is missing.
    """
    path = get_common_dir(explicit_dir) / relative_path
    if not path.is_file():
        raise RuntimeError(
            f"Required shared data file not found: {path}. Ensure the "
            f"'{COMMON_DIR_CONFIG}' config value or {COMMON_DIR_ENV} "
            "environment variable points at an up-to-date rocm-docs-common "
            "checkout."
        )
    return path.read_text(encoding="utf-8")
