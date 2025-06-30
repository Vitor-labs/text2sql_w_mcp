"""
Unholy singleton to use as global logger.
God and Guido van Rossum may forgive me.

use as bellow:
>>> from infra.logger impor logger
>>> logger.info("This is an info message.")
"""

import logging

import structlog


class Singleton(type):
    """Metaclass to ensure a class is treated as a singleton."""

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


class GlobalLogger(metaclass=Singleton):
    """
    Singleton class to use as a global logger.

    use as bellow:
    >>> from infra.logger impor logger
    >>> logger.info("This is an info message.")
    """

    def __init__(self):
        """Configure the logger."""
        structlog.configure(
            wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
            processors=[
                structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M.%S"),
                structlog.processors.add_log_level,
                structlog.dev.ConsoleRenderer(),
            ],
        )

    def __getattr__(self, item):
        """Delegate log methods to structlog's get_logger."""
        logger = structlog.get_logger()
        return getattr(logger, item)


# You should import this instance, it already abstracts enough
logger = GlobalLogger()
