"""Task manager module"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from json import JSONDecodeError
import os
import threading
from typing import Dict, List

from task_flow.setup_logger import get_logger
from task_flow.task import Task


class TaskManager:
    """This class is responsible for managing tasks

    Args:
        max_threads (int): Maximum number of threads to use for task execution
        path_artifact (str): Path to store artifacts (default: "artifacts/")
        path_result (str): Path to store results (default: "results/")
    """

    def __init__(
        self,
        max_threads: int = 10,
        path_artifact: str = "artifacts/",
        path_result: str = "results/",
    ):
        self.tasks: Dict[str, Task] = {}
        self.executor = ThreadPoolExecutor(max_threads)
        self.lock = threading.Lock()
        self.logger = get_logger()
        self.path_artifact = path_artifact
        self.path_result = path_result

    def load_from_disk(self):
        """Load tasks from disk

        Args:
            path (str): Path to the directory where the tasks are stored

        """
        for file in os.listdir(self.path_result):
            task_id = file.split(".")[0]
            self.logger.info("Loading task %s from disk", task_id)
            try:
                task = Task.load_from_file(os.path.join(self.path_result, file))
            except JSONDecodeError:
                self.logger.error("Error loading task %s from disk", task_id)
            else:
                self.tasks[task_id] = task

    def add_task(self, task_class: Task) -> str:
        """Add a task to the task manager and add it to the execution queue

        Args:
            task_class (Task): Task class to be added

        Returns:
            str: Task ID
        """
        task: Task = task_class()
        self.logger.info(
            "Adding task %s with id %s", task_class.__name__, task.task_id
        )
        self.tasks[task.task_id] = task
        self._start_task(task.task_id)
        return task.task_id

    def _start_task(self, task_id: str):
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")

        self.logger.info("Starting task %s", task_id)
        task = self.tasks[task_id]
        task_executor = self.executor.submit(task.execute)
        task_executor.add_done_callback(
            lambda f: self.logger.info("Task %s finished", task_id)
        )

    def get_task_status(
        self, task_id: str, logs_folder_path: str = None
    ) -> Dict:
        """Get the status of a task

        Args:
            task_id (str): Task ID
            logs_folder_path (str): Path to the folder where the logs are stored,
            if None logs will not be returned (default: None)

        Returns:
            Dict: Task status

        """
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")

        task = self.tasks[task_id]

        logs_task = []

        if logs_folder_path and os.path.exists(
            os.path.join(logs_folder_path, f"{task_id}.log")
        ):
            with open(
                os.path.join(logs_folder_path, f"{task_id}.log"),
                "r",
                encoding="utf-8",
            ) as file:
                logs_task = file.readlines()

        return task.result.to_dict() | {"logs": logs_task}

    def list_tasks(self, task_type: str = None) -> List[Dict]:
        """List tasks in the task manager sorted by creation date

        Args:
            task_type (str): Filter tasks by type, if None return all tasks (default: None)

        Returns:
            List[Dict]: List of tasks

        """
        return sorted(
            [
                {
                    "task_id": task.task_id,
                    "task_type": task.result.task_type,
                    "status": task.result.status,
                    "created_at": task.result.created_at,
                    "start_at": task.result.start_at,
                    "end_at": task.result.end_at,
                }
                for _, task in self.tasks.items()
                if task_type is None or task.result.task_type == task_type
            ],
            key=lambda x: datetime.fromisoformat(x["created_at"]),
            reverse=True,
        )

    def shutdown(self):
        """Shutdown the task manager properly

        Waits for all tasks to finish before shutting down
        """
        self.logger.info(
            "Shutting down task manager, waiting for tasks to finish"
        )
        self.executor.shutdown(wait=True)
        self.logger.info("All tasks finished, shutting down")
