"""Task class and TaskResult class to define and execute tasks"""

from dataclasses import dataclass, field
from datetime import datetime
import json
import os
from typing import Callable, Dict
from unittest.mock import MagicMock
import uuid

from task_flow.constants import STATUS
from task_flow.setup_logger import get_task_logger
from task_flow.step import StepResult


@dataclass
class TaskResult:  # pylint: disable=too-many-instance-attributes
    """Class to represent the result of a task

    Attributes:
        task_type (str): Type of the task
        status (STATUS): Status of the task
        exit_message (str): Exit message of the task
        data (Dict[str, StepResult]): Results of the steps in the task
        created_at (str): Timestamp when the task was created
        start_at (str): Timestamp when the task started
        end_at (str): Timestamp when the task ended
        artifacts (Dict[str, str]): Artifacts generated by the task

    """

    task_type: str = None
    status: STATUS = STATUS.PENDING
    exit_message: str = None
    data: Dict[str, StepResult] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    start_at: str = None
    end_at: str = None
    artifacts: Dict[str, str] = field(default_factory=dict)

    @property
    def exit_code(self):
        """Exit code of the task"""
        if len(self.data) == 0:
            return 1
        return (
            1
            if all(
                step_result.status == STATUS.ERROR
                for step_result in self.data.values()
            )
            else 0
        )

    @property
    def duration(self):
        """Duration of the task"""
        if self.start_at and self.end_at:
            return (
                datetime.fromisoformat(self.end_at)
                - datetime.fromisoformat(self.start_at)
            ).total_seconds()
        return None

    def to_dict(self):
        """Convert the object to a dictionary."""
        return {
            "task_type": self.task_type,
            "status": self.status.value,
            "exit_code": self.exit_code,
            "exit_message": self.exit_message,
            "data": {
                step: step_result.to_dict()
                for step, step_result in self.data.items()
            },
            "created_at": self.created_at,
            "start_at": self.start_at,
            "end_at": self.end_at,
            "duration": self.duration,
            "artifacts": self.artifacts,
        }


class Task:
    """Task class to define and execute tasks

    You need to subclass this class and define the steps of the task as methods
    decorated with the step decorator. Each step should return a dictionary with
    the result of the step. The task will execute each step in the order they are
    defined in the class.

    Example:
    ```python
    from task_flow import Task, step

    class MyTask(Task):
        @step
        def step1(self):
            return {"result": "step1"}

        @step
        def step2(self):
            with open("file.txt", "w") as f:
                f.write("Hello, World!")
            self.add_artifact("file.txt")
            return {"result": "step2"}
    ```

    """

    def __init__(self):
        self.task_id = f"task-{uuid.uuid4()}"
        self.logger = get_task_logger(self.task_id)
        self.is_executable = True

        self.steps = [
            method
            for method in dir(self)
            if callable(getattr(self, method))
            and hasattr(getattr(self, method), "is_step")
            and not isinstance(getattr(self, method), MagicMock)
        ]

        self.result = TaskResult(
            data={step: StepResult() for step in self.steps},
            task_type=self.__class__.__name__,
        )

    @staticmethod
    def load_from_file(file_path: str) -> "Task":
        """Load a task from a file

        Args:
            file_path (str): Path to the file

        """
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        task = Task()
        task.task_id = os.path.basename(file_path).removesuffix(".json")
        task.result = TaskResult(
            task_type=data["task_type"],
            status=STATUS(data["status"]),
            exit_message=data["exit_message"],
            created_at=data["created_at"],
            start_at=data["start_at"],
            end_at=data["end_at"],
            data={
                step: StepResult(**step_result)
                for step, step_result in data["data"].items()
            },
            artifacts=data.get("artifacts", {}),
        )

        task.is_executable = False
        return task

    def execute(self):
        """Execute the task

        This method will execute the steps of the task in the order they are defined.

        Returns:
            Dict: Result of the task
        """
        if not self.is_executable:
            raise ValueError("Task is not executable")

        self.logger.info("Task started")
        self.result.status = STATUS.RUNNING
        self.result.start_at = datetime.now().isoformat()

        try:
            if not self.steps:
                raise ValueError("No steps to execute")

            for step_name in self.steps:
                step_func = getattr(self, step_name)
                self._execute_step(step_name, step_func)
        except Exception as e:  # pylint: disable=broad-except
            self.result.exit_message = str(e)
            self.result.status = STATUS.ERROR
            self.logger.error("Task failed: %s", str(e))
        else:
            self.result.status = STATUS.SUCCESS
            self.logger.info("Task finished successfully")

        self.result.end_at = datetime.now().isoformat()

        self.save_result()

        return self.result.to_dict()

    def _execute_step(self, step_name: str, step_func: Callable):
        self.logger.info("Starting step %s", step_name)
        self.result.data[step_name].status = STATUS.RUNNING
        try:
            result = step_func()
            self.result.data[step_name].data = result
            self.result.data[step_name].status = STATUS.SUCCESS
            self.logger.info("Step %s finished successfully", step_name)
        except Exception as e:
            self.result.data[step_name].status = STATUS.ERROR
            self.logger.error("Step %s failed: %s", step_name, str(e))
            raise e

    def add_artifact(self, path: str, artifact_path: str = "artifacts/"):
        """Add an artifact to the task result

        Args:
            path (str): Path file to the artifact
            artifact_path (str): Path to the directory where the artifacts will be saved
            (default: "artifacts/")

        """
        self.logger.info("Adding artifact %s", os.path.basename(path))
        os.makedirs(artifact_path, exist_ok=True)
        new_path = os.path.join(
            artifact_path, f"{self.task_id}_{os.path.basename(path)}"
        )
        os.rename(path, new_path)
        self.result.artifacts[os.path.basename(path)] = new_path

    def save_result(self, path: str = "results/"):
        """Save the task result to a file

        The result will be saved in the results directory with the task ID as the filename.

        Args:
            path (str): Path to the directory where the results will be saved

        """
        os.makedirs(path, exist_ok=True)
        with open(
            os.path.join(path, f"{self.task_id}.json"), "w", encoding="utf-8"
        ) as file:
            json.dump(self.result.to_dict(), file)
