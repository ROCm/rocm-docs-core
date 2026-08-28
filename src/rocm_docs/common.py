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
import subprocess
from pathlib import Path

import sphinx.util.logging

logger = sphinx.util.logging.getLogger(__name__)

COMMON_DIR_ENV = "ROCM_DOCS_COMMON_DIR"
COMMON_DIR_CONFIG = "rocm_docs_common_dir"

# Default source for the shared build-data repo, used by
# clone_common_if_missing(). Keeping these here means consumer conf.py files do
# not hardcode the URL/branch.
COMMON_REPO_URL = "https://github.com/neon60/rocm-docs-common.git"
COMMON_REPO_BRANCH = "main"


def clone_common_if_missing(
    dest: str | os.PathLike[str],
    *,
    repo_url: str = COMMON_REPO_URL,
    branch: str = COMMON_REPO_BRANCH,
) -> str:
    """Clone rocm-docs-common to ``dest``, or refresh it if already present.

    Intended for a consumer's ``conf.py`` so a local ``sphinx-build`` works
    without a manual clone. On Read the Docs the ``post_checkout`` job usually
    provides a fresh checkout already, so this refresh is redundant there but
    harmless.

    When ``dest`` does not yet contain a checkout it is cloned (shallow). When
    it already exists, it is fast-forwarded to the tip of ``branch`` so repeated
    local builds do not read stale data from a checkout cloned days ago. The
    refresh is best-effort: a failure (offline, GitHub throttling) is logged and
    the existing checkout is used, since a slightly stale local build is better
    than a blocked one. The initial clone still raises, because without it there
    is no data to build from at all.

    Args:
        dest: Directory the repo should live in (e.g. ``<repo>/rocm-docs-common``).
        repo_url: Git URL to clone from. Defaults to :data:`COMMON_REPO_URL`.
        branch: Branch to clone/refresh (shallow). Defaults to
            :data:`COMMON_REPO_BRANCH`.

    Returns:
        ``str(dest)``, so callers can assign ``rocm_docs_common_dir`` directly.

    Raises:
        subprocess.CalledProcessError: if the initial clone fails.
    """
    dest_path = Path(dest)
    if not (dest_path / "data").is_dir():
        subprocess.run(
            [
                "git",
                "clone",
                "--depth",
                "1",
                "--branch",
                branch,
                repo_url,
                str(dest_path),
            ],
            check=True,
        )
        return str(dest_path)

    # Already checked out: pull the latest so local builds don't go stale.
    try:
        subprocess.run(
            [
                "git",
                "-C",
                str(dest_path),
                "fetch",
                "--depth",
                "1",
                repo_url,
                branch,
            ],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(dest_path), "checkout", "FETCH_HEAD"],
            check=True,
        )
    except (subprocess.CalledProcessError, OSError) as error:
        logger.warning(
            "Could not refresh the rocm-docs-common checkout at %s (%s). "
            "Building against the existing, possibly stale, copy. Delete the "
            "directory to force a fresh clone.",
            dest_path,
            error,
        )
    return str(dest_path)


def ensure_common_dir(
    confdir: str | os.PathLike[str],
    config_value: str | None = None,
) -> str | None:
    """Resolve the common dir for a build, cloning a default if needed.

    Called during extension setup so a consumer's ``conf.py`` needs no
    common-dir configuration at all. Resolution order:

    1. If ``config_value`` (the ``rocm_docs_common_dir`` config value) is set,
       use it.
    2. If the ``ROCM_DOCS_COMMON_DIR`` env var is set, defer to it (return
       ``None`` so :func:`get_common_dir` picks it up).
    3. Otherwise clone rocm-docs-common to ``<confdir>/../rocm-docs-common``
       (the repo root in the standard ``docs/`` layout, matching where the
       Read the Docs ``post_checkout`` job clones it), refreshing it to the
       branch tip if it already exists, and return that path.

    Args:
        confdir: The Sphinx conf.py directory (``app.confdir``).
        config_value: The current ``rocm_docs_common_dir`` config value.

    Returns:
        The path to assign to ``rocm_docs_common_dir``, or ``None`` when the
        env var should be used instead.
    """
    if config_value:
        return config_value
    if os.environ.get(COMMON_DIR_ENV):
        return None
    return clone_common_if_missing(Path(confdir).parent / "rocm-docs-common")


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
