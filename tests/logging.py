"""Defines Helpers for capturing and working with logs in tests"""

from typing import Any, Callable, Generator, Iterable, List, Set

import logging
import unittest.mock

import pytest


class AddLogHandlerFixture:
    """Fixture for registering delayed handlers for logs"""

    def __init__(self, caplog: pytest.LogCaptureFixture) -> None:
        """Initialize the fixture"""
        self.caplog = caplog
        self._handlers: List[Callable[[Iterable[logging.LogRecord]], None]] = []

    def __call__(
        self, handler: Callable[[Iterable[logging.LogRecord]], None]
    ) -> Any:
        """Register a handler"""
        self._handlers.append(handler)

    def run_handlers(self) -> None:
        """Run all previously registered handlers"""
        for handler in self._handlers:
            handler(self.caplog.get_records("call"))


@pytest.fixture()
def add_log_handler(
    caplog: pytest.LogCaptureFixture,
    with_sphinx_logs: None,  # noqa: ARG001
) -> Generator[AddLogHandlerFixture, None, None]:
    """Factory for registering delayed log handlers"""
    fixture = AddLogHandlerFixture(caplog)
    yield fixture
    fixture.run_handlers()


@pytest.fixture()
def expected_logs() -> Set[logging.LogRecord]:
    """The set of expected logs, see no_unexpected_logs"""
    return set()


@pytest.fixture()
def no_unexpected_logs(
    add_log_handler: AddLogHandlerFixture, expected_logs: Set[logging.LogRecord]
) -> None:
    """Raise an error if an unexpected log is found

    all expected warnings should be added to `expected_logs`
    """

    def validate_logs(records: Iterable[logging.LogRecord]) -> None:
        for record in records:
            if record.levelno < logging.WARNING:
                continue
            if record not in expected_logs:
                pytest.fail(f"Unexpected log: {record.getMessage()}")

    add_log_handler(validate_logs)


@pytest.fixture()
def with_sphinx_logs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fixture to enable capturing sphinx logs in pytest"""
    monkeypatch.setattr("sphinx.util.logging.setup", unittest.mock.Mock())
