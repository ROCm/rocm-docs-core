"""Pytest Configuration"""

from .logging import *  # noqa: F403
from .sphinx import *  # noqa: F403

pytest_plugins = ["sphinx.testing.fixtures"]
