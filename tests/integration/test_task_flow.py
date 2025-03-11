import json
import os
import shutil
import time
import pytest

from task_flow import TaskManager, step, Task


class TestAddTaskAndRun:
    @pytest.fixture(autouse=True)
    def setup_test(self):
        print("Setting up test")
        self.taskManager = TaskManager(
            path_artifact="tests/integration/tmp/artifacts",
            path_result="tests/integration/tmp/results",
            path_logs="tests/integration/tmp/logs",
        )

        yield
        print("Tearing down test")
        shutil.rmtree("tests/integration/tmp/")

    def test_one_task(self):
        class CustomTask(Task):
            @step
            def start(self):
                time.sleep(1)
                return {"toto": "tata"}

        task_id = self.taskManager.add_task(CustomTask)
        self.taskManager.shutdown()
        assert len(self.taskManager.tasks) == 1
        assert self.taskManager.tasks[task_id].result.duration > 1

        with open(
            os.path.join(self.taskManager.path_result, f"{task_id}.json"), "r"
        ) as f:
            data = json.load(f)
        assert data == {
            "task_type": "CustomTask",
            "status": "SUCCESS",
            "exit_code": 0,
            "exit_message": None,
            "data": {
                "start": {
                    "message": "",
                    "status": "SUCCESS",
                    "data": {"toto": "tata"},
                }
            },
            "created_at": self.taskManager.tasks[task_id].result.created_at,
            "start_at": self.taskManager.tasks[task_id].result.start_at,
            "end_at": self.taskManager.tasks[task_id].result.end_at,
            "duration": self.taskManager.tasks[task_id].result.duration,
            "artifacts": {},
        }

    def test_two_tasks(self):
        class CustomTask(Task):
            @step
            def start(self):
                time.sleep(1)
                return {"toto": "tata"}

        task_id_1 = self.taskManager.add_task(CustomTask)
        task_id_2 = self.taskManager.add_task(CustomTask)

        self.taskManager.shutdown()
        assert len(self.taskManager.tasks) == 2
        assert self.taskManager.tasks[task_id_1].result.duration > 1
        assert self.taskManager.tasks[task_id_2].result.duration > 1

        with open(
            os.path.join(self.taskManager.path_result, f"{task_id_1}.json"), "r"
        ) as f:
            data = json.load(f)
        assert data == {
            "task_type": "CustomTask",
            "status": "SUCCESS",
            "exit_code": 0,
            "exit_message": None,
            "data": {
                "start": {
                    "message": "",
                    "status": "SUCCESS",
                    "data": {"toto": "tata"},
                }
            },
            "created_at": self.taskManager.tasks[task_id_1].result.created_at,
            "start_at": self.taskManager.tasks[task_id_1].result.start_at,
            "end_at": self.taskManager.tasks[task_id_1].result.end_at,
            "duration": self.taskManager.tasks[task_id_1].result.duration,
            "artifacts": {},
        }

        with open(
            os.path.join(self.taskManager.path_result, f"{task_id_2}.json"), "r"
        ) as f:
            data = json.load(f)
        assert data == {
            "task_type": "CustomTask",
            "status": "SUCCESS",
            "exit_code": 0,
            "exit_message": None,
            "data": {
                "start": {
                    "message": "",
                    "status": "SUCCESS",
                    "data": {"toto": "tata"},
                }
            },
            "created_at": self.taskManager.tasks[task_id_2].result.created_at,
            "start_at": self.taskManager.tasks[task_id_2].result.start_at,
            "end_at": self.taskManager.tasks[task_id_2].result.end_at,
            "duration": self.taskManager.tasks[task_id_2].result.duration,
            "artifacts": {},
        }

        assert task_id_1 != task_id_2
        assert (
            self.taskManager.tasks[task_id_1].result.created_at
            < self.taskManager.tasks[task_id_2].result.created_at
        )
        assert (
            self.taskManager.tasks[task_id_1].result.start_at
            < self.taskManager.tasks[task_id_2].result.start_at
        )
        assert (
            self.taskManager.tasks[task_id_1].result.end_at
            < self.taskManager.tasks[task_id_2].result.end_at
        )
