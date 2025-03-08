"""This module contains the functions to create loggers for the application and tasks."""

import logging
import os

LOG_FORMATTER_FILE = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s", "%Y-%m-%d %H:%M:%S"
)
LOG_FORMATTER_CONSOLE = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s", "%Y-%m-%d %H:%M:%S"
)


def get_logger(
    name: str = "app", level: int = logging.INFO, path_to_save: str = "logs"
) -> logging.Logger:
    """Get a logger for the application

    This logger will log to the console and to a file in the specified path.

    Args:
        name (str): Name of the logger
        level (int): Log level
        path_to_save (str): Path to save the log file

    Returns:
        logging.Logger: Logger object

    Examples:
        >>> logger = get_logger("app", level=logging.DEBUG, path_to_save="logs")
        >>> logger.info("This is an info message")
        >>> logger.debug("This is a debug message")

    """
    os.makedirs(path_to_save, exist_ok=True)
    app_logger = logging.getLogger(name)

    if not app_logger.handlers:
        app_logger.setLevel(logging.DEBUG)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(LOG_FORMATTER_CONSOLE)
        console_handler.setLevel(level)
        app_logger.addHandler(console_handler)

        file_handler = logging.FileHandler(
            os.path.join(path_to_save, f"{name}.log")
        )
        file_handler.setFormatter(LOG_FORMATTER_FILE)
        file_handler.setLevel(logging.DEBUG)
        app_logger.addHandler(file_handler)

    return app_logger


def get_task_logger(
    task_id: str, path_to_save: str = "logs/tasks"
) -> logging.Logger:
    """Get a logger for a task

    This logger will log to the console and to a specific file for the task.

    Args:
        task_id (str): Task ID
        path_to_save (str): Path to save the log file

    Returns:
        logging.Logger: Logger object

    Examples:
        >>> logger = get_task_logger("task_1", path_to_save="logs/tasks")
        >>> logger.info("This is an info message")
        >>> logger.debug("This is a debug message")
    """
    return get_logger(f"{task_id}", path_to_save=path_to_save)
