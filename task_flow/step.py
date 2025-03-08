"""This module contains the step decorator and StepResult class."""

from dataclasses import dataclass, field
from typing import Callable

from task_flow.constants import STATUS


def step(func: Callable):
    """Decorator to mark a function as a step in a task flow."""
    func.is_step = True
    return func


@dataclass
class StepResult:
    """Class to represent the result of a step in a task flow.

    Attributes:
        message (str): Message from the step
        status (STATUS): Status of the step
        data (dict): Additional data from the step
    """

    message: str = ""
    status: STATUS = STATUS.PENDING
    data: dict = field(default_factory=dict)

    def __post_init__(self):
        if isinstance(self.status, str):
            self.status = STATUS(self.status)

    def to_dict(self):
        """Convert the object to a dictionary."""
        return {
            "message": self.message,
            "status": self.status.value,
            "data": self.data,
        }
