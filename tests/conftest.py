"""Pytest Configuration"""

from .log_fixtures import *
from .projects_fixtures import *
from .sphinx_fixtures import *

pytest_plugins = ["sphinx.testing.fixtures"]
