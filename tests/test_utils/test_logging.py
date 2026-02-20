"""Tests for ecproc.utils.logging — structured logging with Rich."""

from __future__ import annotations

import logging

from rich.logging import RichHandler

from ecproc.utils.logging import get_logger


class TestGetLogger:
    """Tests for get_logger()."""

    def test_returns_logger_instance(self):
        logger = get_logger("test.returns_logger")
        assert isinstance(logger, logging.Logger)

    def test_logger_has_expected_name(self):
        logger = get_logger("test.named_logger")
        assert logger.name == "test.named_logger"

    def test_logger_has_rich_handler(self):
        logger = get_logger("test.rich_handler")
        assert any(isinstance(h, RichHandler) for h in logger.handlers)

    def test_idempotent_same_logger(self):
        logger_a = get_logger("test.idempotent")
        logger_b = get_logger("test.idempotent")
        assert logger_a is logger_b

    def test_idempotent_single_handler(self):
        name = "test.single_handler"
        # Remove any prior handlers left from other tests
        existing = logging.getLogger(name)
        existing.handlers.clear()

        get_logger(name)
        get_logger(name)
        logger = logging.getLogger(name)
        assert len(logger.handlers) == 1

    def test_default_level_is_info(self):
        logger = get_logger("test.default_level")
        assert logger.level == logging.INFO

    def test_custom_level(self):
        name = "test.custom_level"
        existing = logging.getLogger(name)
        existing.handlers.clear()

        logger = get_logger(name, level=logging.DEBUG)
        assert logger.level == logging.DEBUG

    def test_handler_level_matches(self):
        name = "test.handler_level"
        existing = logging.getLogger(name)
        existing.handlers.clear()

        logger = get_logger(name, level=logging.WARNING)
        rich_handlers = [h for h in logger.handlers if isinstance(h, RichHandler)]
        assert len(rich_handlers) == 1
        assert rich_handlers[0].level == logging.WARNING
