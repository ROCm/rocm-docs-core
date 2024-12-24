"""Defines Helpers for capturing and working with logs in tests"""

from __future__ import annotations

import types
from typing import Literal, NamedTuple

import contextlib
import copy
import itertools
import logging
import unittest.mock
from collections.abc import Callable, Iterable, Iterator

import pytest

TestPhase = Literal["setup", "call", "teardown"]


class LogHandlerStackToken(NamedTuple):
    when: TestPhase
    stacklevel: int


class LogStackFixture:
    def __init__(self, caplog: pytest.LogCaptureFixture):
        self._caplog: pytest.LogCaptureFixture = caplog
        self._log_stack: list[list[logging.LogRecord]] = []

    def push(self, *, when: TestPhase = "call") -> LogHandlerStackToken:
        # This should be a single atomic operation
        records = self._caplog.get_records(when)
        if len(records) > 0:
            self._log_stack.append(copy.copy(records))
            self._caplog.clear()
        return LogHandlerStackToken(when, len(self._log_stack))

    def pop(self, token: LogHandlerStackToken) -> Iterable[logging.LogRecord]:
        return itertools.chain(
            *self._log_stack[token.stacklevel :],
            self._caplog.get_records(token.when),
        )

    class Scope:
        def __init__(
            self,
            fixture: LogStackFixture,
            token: LogHandlerStackToken,
            callbacks: contextlib.ExitStack,
        ) -> None:
            self._fixture = fixture
            self._token = token
            self._callbacks = callbacks

        def add(
            self, callback: Callable[[Iterable[logging.LogRecord]], None]
        ) -> None:
            self._callbacks.callback(
                lambda: callback(self._fixture.pop(self._token))
            )

        def pop_all(self) -> LogStackFixture.Scope:
            return LogStackFixture.Scope(
                self._fixture, self._token, self._callbacks.pop_all()
            )

        def close(self) -> None:
            self._callbacks.close()

        def __enter__(self) -> LogStackFixture.Scope:
            return self

        def __exit__(
            self,
            type: type,
            value: BaseException,
            traceback: types.TracebackType,
        ) -> bool | None:
            return self._callbacks.__exit__(type, value, traceback)

    def new_scope(self, *, when: TestPhase = "call") -> Scope:
        return self.Scope(self, self.push(when=when), contextlib.ExitStack())


@pytest.fixture
def log_handler_stack(
    caplog: pytest.LogCaptureFixture, _with_sphinx_logs: None
) -> LogStackFixture:
    """A fixture allowing scoped log handling"""
    return LogStackFixture(caplog)


@pytest.fixture
def expected_logs_impl() -> set[logging.LogRecord]:
    """Implementation of expected_logs"""
    return set()


@pytest.fixture
def _no_unexpected_warnings_impl(
    request: pytest.FixtureRequest,
    log_handler_stack: LogStackFixture,
    expected_logs_impl: set[logging.LogRecord],
) -> Iterator[None]:
    if "_no_unexpected_warnings" not in request.fixturenames:
        yield
        return

    class Validator:
        def __init__(self) -> None:
            self.logrecord: tuple[str, str, str] | None = None

        def validate(self, records: Iterable[logging.LogRecord]) -> None:
            for r in records:
                if r.levelno < logging.WARNING:
                    continue
                if r not in expected_logs_impl:
                    self.logrecord = (
                        r.name,
                        r.levelname,
                        r.getMessage(),
                    )
                    return

    validator = Validator()
    with log_handler_stack.new_scope() as scope:
        scope.add(validator.validate)
        yield

    invert = request.node.get_closest_marker("meta_invert_fixture") is not None
    if validator.logrecord is None:
        if not invert:
            return

        pytest.fail("Did not find any unexpected logs")

    if not invert:
        pytest.fail(f"Unexpected log: {validator.logrecord}")


# Must request no_unexpected_warnings_ to ensure its teardown runs *after*
# other fixtures that request expected_logs
@pytest.fixture
def expected_logs(
    _no_unexpected_warnings_impl: None,
    expected_logs_impl: set[logging.LogRecord],
) -> set[logging.LogRecord]:
    """The set of expected logs, see no_unexpected_warnings"""
    return expected_logs_impl


@pytest.fixture
def _no_unexpected_warnings(
    _no_unexpected_warnings_impl: None,
) -> None:
    """Raise an error if an unexpected log is found

    all expected warnings should be added to `expected_logs`
    """
    return


class ExpectLogFixture:
    """Fixture class for expect_log"""

    def __init__(
        self,
        log_handler_stack: LogStackFixture,
        expected_logs: set[logging.LogRecord],
    ) -> None:
        """Initialize the fixture"""
        self._log_handler_stack = log_handler_stack
        self._expected_logs = expected_logs

    class Validator:
        def __init__(
            self,
            scope: LogStackFixture.Scope,
            expected: tuple[str, int, str],
            *,
            required: bool,
            capture_all: bool,
            expected_logs: set[logging.LogRecord],
        ) -> None:
            self._scope = scope
            self._expected = expected
            self._expected_logs = expected_logs
            self.required = required
            self.capture_all = capture_all
            self._found = False

            self._scope.add(self._validate_logs)

        @property
        def found(self) -> bool:
            return self._found

        def __enter__(self) -> ExpectLogFixture.Validator:
            self._scope.__enter__()
            return self

        def __exit__(
            self,
            type: type,
            value: BaseException,
            traceback: types.TracebackType,
        ) -> bool | None:
            return self._scope.__exit__(type, value, traceback)

        def _validate_logs(
            self,
            records: Iterable[logging.LogRecord],
        ) -> None:
            self._found = False
            for r in records:
                if self._expected != (r.name, r.levelno, r.getMessage()):
                    continue

                self._found = True
                self._expected_logs.add(r)
                if not self.capture_all:
                    return

            if not self.required or self._found:
                return

            lvl = logging.getLevelName(self._expected[1])
            pytest.fail(
                f"Expected log {(self._expected[0], lvl, self._expected[2])}, but it wasn't found"
            )

    def __call__(
        self,
        name: str,
        level: str,
        msg: str,
        *,
        required: bool = True,
        capture_all: bool = False,
        when: TestPhase = "call",
    ) -> ExpectLogFixture.Validator:
        """Register a new handler. See expect_log for more details"""
        levelno = logging.getLevelName(level)
        if not isinstance(levelno, int):
            raise ValueError(f'Unknown log level "{level}"')

        return self.Validator(
            self._log_handler_stack.new_scope(when=when),
            (name, levelno, msg),
            required=required,
            capture_all=capture_all,
            expected_logs=self._expected_logs,
        )


@pytest.fixture
def expect_log(
    log_handler_stack: LogStackFixture, expected_logs: set[logging.LogRecord]
) -> ExpectLogFixture:
    """Register a verifier for a log message

    Each call to expect_log(name, level, msg) will verify that such a log is
    emitted at least once. This log will not trigger unknown warning checks.
    Set capture_all to True to capture all warnings that match, not just the first.
    """
    return ExpectLogFixture(log_handler_stack, expected_logs)


@pytest.fixture
def _with_sphinx_logs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fixture to enable capturing sphinx logs in pytest"""
    monkeypatch.setattr("sphinx.util.logging.setup", unittest.mock.Mock())


__all__ = [
    "_no_unexpected_warnings",
    "_no_unexpected_warnings_impl",
    "_with_sphinx_logs",
    "expect_log",
    "expected_logs",
    "expected_logs_impl",
    "log_handler_stack",
]
