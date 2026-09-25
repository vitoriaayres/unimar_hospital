from __future__ import annotations

import logging
import sys
from datetime import datetime

import structlog
from structlog.types import EventDict, WrappedLogger

from app.config import settings


def add_severity_level(logger: WrappedLogger, method_name: str, event_dict: EventDict) -> EventDict:
    event_dict['level'] = method_name.upper()
    return event_dict


def add_timestamp(logger: WrappedLogger, method_name: str, event_dict: EventDict) -> EventDict:
    event_dict['timestamp'] = datetime.utcnow().isoformat() + 'Z'
    return event_dict


def drop_color_message_key(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    event_dict.pop('color_message', None)
    return event_dict


def setup_logging() -> None:
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt='iso', utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        drop_color_message_key,
    ]

    if settings.LOG_FORMAT == 'json':
        processors = shared_processors + [structlog.processors.JSONRenderer()]
    else:
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure stdlib logging
    logging.basicConfig(
        format='%(message)s',
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL.upper()),
    )

    # Reduce noise from third-party loggers
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
