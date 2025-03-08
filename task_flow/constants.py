"""Constants for task_flow package."""

from enum import Enum


class STATUS(str, Enum):
    """Enum class for task status"""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
