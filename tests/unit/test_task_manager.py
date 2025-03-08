import json
import pytest
from task_flow.task_manager import TaskManager
from task_flow.task import Task


class TestTaskManager:
    @pytest.fixture(autouse=True)
    def setup_test(self, tmp_path, mocker):
        print("Setting up test")

        self.mock_logger = mocker.patch("task_flow.task_manager.get_logger")
        self.mock_logger_task = mocker.patch("task_flow.task.get_task_logger")

        result_file_data = {
            "task_type": "TestTaskType",
            "status": "PENDING",
            "exit_message": None,
            "created_at": "2021-01-01T00:00:00",
            "start_at": None,
            "end_at": None,
            "data": {},
            "artifacts": {},
        }

        results_path = tmp_path / "results"
        results_path.mkdir()

        file1 = results_path / "file1.txt"
        with open(file1, "w") as f:
            json.dump(result_file_data, f)

        file2 = results_path / "file2.txt"
        with open(file2, "w") as f:
            json.dump(result_file_data | {"task_type": "TestTaskType2"}, f)

        yield

        print("Tearing down test")

    def test_task_manager_initialization(self):
        task_manager = TaskManager()
        assert task_manager.tasks == {}
        assert task_manager.path_artifact == "artifacts/"
        assert task_manager.path_result == "results/"

    def test_task_manager_initialization_with_params(self):
        task_manager = TaskManager(
            max_threads=5, path_artifact="test/", path_result="test2/"
        )
        assert task_manager.tasks == {}
        assert task_manager.path_artifact == "test/"
        assert task_manager.path_result == "test2/"

    def test_load_from_disk(self, tmp_path, mocker):
        task_manager = TaskManager()
        task_manager.path_result = tmp_path / "results"

        task_manager.load_from_disk()

        assert len(task_manager.tasks) == 2

    def test_load_from_disk_with_error(self, tmp_path, mocker):
        task_manager = TaskManager()
        task_manager.path_result = tmp_path / "results"

        mocker.patch(
            "task_flow.task.Task.load_from_file",
            side_effect=[
                json.JSONDecodeError("Expecting value", "", 0),
                Task(),
            ],
        )

        task_manager.load_from_disk()

        assert len(task_manager.tasks) == 1

    def test_add_task(self, mocker):
        task_manager = TaskManager()
        start_task_mock = mocker.patch.object(task_manager, "_start_task")

        assert "task-" in task_manager.add_task(Task)
        assert "task-" in task_manager.add_task(Task)

        assert len(task_manager.tasks) == 2
        assert start_task_mock.call_count == 2

    def test_start_task(self, mocker):
        task_manager = TaskManager()
        task = Task()
        task_manager.tasks[task.task_id] = task

        task_exec_mock = mocker.patch.object(task, "execute")
        task_manager._start_task(task.task_id)

        task_exec_mock.assert_called_once()

    def test_start_task_not_found(self, mocker):
        task_manager = TaskManager()
        with pytest.raises(ValueError):
            task_manager._start_task("task-123")

    def test_get_task_status(self):
        task_manager = TaskManager()
        task = Task()
        task_manager.tasks[task.task_id] = task

        assert task_manager.get_task_status(
            task.task_id
        ) == task.result.to_dict() | {"logs": []}

    def test_get_task_status_with_logs(self, tmp_path):
        task_manager = TaskManager()
        task = Task()
        task_manager.tasks[task.task_id] = task

        logs_folder = tmp_path / "logs"
        logs_folder.mkdir()
        file = logs_folder / f"{task.task_id}.log"
        with open(file, "w") as f:
            f.write("log1\nlog2")

        assert task_manager.get_task_status(
            task.task_id, logs_folder_path=logs_folder
        ) == task.result.to_dict() | {"logs": ["log1\n", "log2"]}

    def test_get_task_status_not_found(self):
        task_manager = TaskManager()
        with pytest.raises(ValueError):
            task_manager.get_task_status("task-123")

    def test_list_tasks(self):
        task_manager = TaskManager()

        task1 = Task()
        task2 = Task()
        task1.result.created_at = "2021-01-01T00:00:00"
        task2.result.created_at = "2021-01-02T00:02:00"

        task_manager.tasks[task1.task_id] = task1
        task_manager.tasks[task2.task_id] = task2

        assert task_manager.list_tasks() == [
            {
                "task_id": task2.task_id,
                "task_type": "Task",
                "status": "PENDING",
                "created_at": "2021-01-02T00:02:00",
                "start_at": None,
                "end_at": None,
            },
            {
                "task_id": task1.task_id,
                "task_type": "Task",
                "status": "PENDING",
                "created_at": "2021-01-01T00:00:00",
                "start_at": None,
                "end_at": None,
            },
        ]

    def test_list_tasks_with_filter(self):
        task_manager = TaskManager()

        task1 = Task()
        task2 = Task()

        task1.result.task_type = "customTask"

        task_manager.tasks[task1.task_id] = task1
        task_manager.tasks[task2.task_id] = task2

        assert task_manager.list_tasks(task_type="customTask") == [
            {
                "task_id": task1.task_id,
                "task_type": "customTask",
                "status": "PENDING",
                "created_at": task1.result.created_at,
                "start_at": None,
                "end_at": None,
            },
        ]

    def test_shutdown(self, mocker):
        task_manager = TaskManager()
        executor_shutdown_mock = mocker.patch.object(
            task_manager.executor, "shutdown"
        )

        task_manager.shutdown()
        executor_shutdown_mock.assert_called_once()
