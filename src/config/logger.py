"""
This module provides a Logger class that configures a structlog logger as a singleton.
Usage:

from config.logger import logger

# Use the configured logger
logger.info("This is an info message")
"""

import structlog


class Logger:
    """Logger class. Configure the structlog logger and make it a singleton."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.configure()
        return cls._instance

    def configure(self):
        """Configure the logger"""
        structlog.configure(
            processors=[
                structlog.processors.add_log_level,
                structlog.dev.ConsoleRenderer(
                    level_styles={
                        "debug": "0;36",
                        "info": "0;37",
                        "warning": "0;33",
                        "error": "0;31",
                        "critical": "0;31",
                    },
                ),
            ]
        )
        self.logger = structlog.get_logger()


"""
You should just import the bellow line instead of the whole module.
It already abstracts enough to be used as a singleton.
"""
logger = Logger()
