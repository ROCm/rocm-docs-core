from __future__ import annotations

import logging

import pytest

from .log_fixtures import ExpectLogFixture

logger = logging.getLogger(__name__)


def test_log_stack(expect_log: ExpectLogFixture) -> None:
    with expect_log(logger.name, "WARNING", "Foo"):
        logger.warning("Foo")
        with expect_log(logger.name, "WARNING", "Bar"):
            logger.warning("Bar")
            with expect_log(logger.name, "ERROR", "Baz"):
                logger.error("Baz")
        with expect_log(logger.name, "ERROR", "Qux"):
            logger.error("Qux")


def test_scope_of_log_stack(expect_log: ExpectLogFixture) -> None:
    logger.info("Foo")
    with expect_log(logger.name, "INFO", "Foo", required=False) as res:
        pass
    logger.info("Foo")
    assert not res.found


@pytest.mark.usefixtures("_no_unexpected_warnings")
@pytest.mark.meta_invert_fixture
def test_unexpected_warnings() -> None:
    logger.warning("An unexpected warning")


@pytest.mark.usefixtures("_no_unexpected_warnings")
def test_expected_warning(
    caplog: pytest.LogCaptureFixture, expected_logs: set[logging.LogRecord]
) -> None:
    logger.warning("An expected warning")
    records = caplog.get_records("call")
    assert len(records) == 1
    expected_logs.add(records[0])
