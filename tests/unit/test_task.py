import pytest
import os
import json
from datetime import datetime
from task_flow.task import Task, TaskResult
from task_flow.constants import STATUS
from task_flow.step import StepResult, step


class TestTaskResult:
    def test_task_result_initialization(self):
        task_result = TaskResult(task_type="TestTask")
        assert task_result.task_type == "TestTask"
        assert task_result.status == STATUS.PENDING
        assert task_result.exit_message is None
        assert task_result.data == {}
        assert task_result.created_at is not None
        assert task_result.start_at is None
        assert task_result.end_at is None
        assert task_result.artifacts == {}

    @pytest.mark.parametrize(
        "step_status, expected",
        [
            pytest.param(STATUS.PENDING, 0, id="stepPending"),
            pytest.param(STATUS.SUCCESS, 0, id="stepSuccess"),
            pytest.param(STATUS.RUNNING, 0, id="stepRunning"),
            pytest.param(STATUS.ERROR, 1, id="stepError"),
            pytest.param(None, 1, id="noSteps"),
        ],
    )
    def test_task_result_exit_code(self, step_status, expected, request):
        if step_status is not None:
            task_result = TaskResult(
                data={request.node.name: StepResult(status=step_status)}
            )
        else:
            task_result = TaskResult()
        assert task_result.exit_code == expected

    @pytest.mark.parametrize(
        "start_at, end_at, expected",
        [
            pytest.param(
                datetime(2021, 1, 1, 0, 0, 0).isoformat(),
                datetime(2021, 1, 1, 0, 0, 10).isoformat(),
                10,
                id="10Seconds",
            ),
            pytest.param(
                datetime(2021, 1, 1, 0, 0, 0).isoformat(),
                datetime(2021, 1, 1, 0, 10, 0).isoformat(),
                600,
                id="10Minutes",
            ),
            pytest.param(
                datetime(2021, 1, 1, 0, 0, 0).isoformat(),
                datetime(2021, 1, 1, 10, 0, 0).isoformat(),
                36000,
                id="10Hours",
            ),
            pytest.param(
                datetime(2021, 1, 1, 0, 0, 0).isoformat(),
                datetime(2021, 1, 2, 0, 0, 0).isoformat(),
                86400,
                id="1Day",
            ),
            pytest.param(
                None,
                datetime(2021, 1, 1, 0, 0, 0).isoformat(),
                None,
                id="NoStart",
            ),
            pytest.param(
                datetime(2021, 1, 1, 0, 0, 0).isoformat(),
                None,
                None,
                id="NoEnd",
            ),
            pytest.param(None, None, None, id="NoStartEnd"),
        ],
    )
    def test_task_result_duration(self, start_at, end_at, expected):
        task_result = TaskResult(start_at=start_at, end_at=end_at)
        assert task_result.duration == expected

    def test_task_result_to_dict(self):
        task_result = TaskResult(task_type="TestTask")
        result_dict = task_result.to_dict()
        assert result_dict == {
            "task_type": "TestTask",
            "status": "PENDING",
            "exit_code": 1,
            "exit_message": None,
            "data": {},
            "created_at": task_result.created_at,
            "start_at": None,
            "end_at": None,
            "duration": None,
            "artifacts": {},
        }


class TestTask:

    @pytest.fixture(autouse=True)
    def setup(self, mocker):
        print("Setting up")
        self.mock_logger = mocker.patch("task_flow.task.get_task_logger")
        yield
        print("Tearing down")

    def test_task_initialization(self):
        task = Task()
        assert task.task_id.startswith("task-")
        assert task.logger == self.mock_logger.return_value
        assert task.is_executable is True
        assert isinstance(task.result, TaskResult)

    def test_load_from_file(self, tmp_path):
        test_file = tmp_path / "task-123456.json"
        json_data = {
            "task_type": "TestTask",
            "status": STATUS.SUCCESS.value,
            "exit_message": "Test",
            "created_at": datetime.now().isoformat(),
            "start_at": datetime.now().isoformat(),
            "end_at": datetime.now().isoformat(),
            "data": {},
            "artifacts": {},
        }
        test_file.write_text(json.dumps(json_data))

        task = Task.load_from_file(str(test_file))
        assert task.task_id == "task-123456"
        assert task.result.task_type == "TestTask"
        assert task.result.status == STATUS.SUCCESS
        assert task.result.exit_message == "Test"
        assert task.result.created_at == json_data["created_at"]
        assert task.result.start_at == json_data["start_at"]
        assert task.result.end_at == json_data["end_at"]
        assert task.result.data == {}
        assert task.result.artifacts == {}
        assert task.is_executable is False
        assert task.logger == self.mock_logger.return_value

    def test_execute_not_executable(self):
        task = Task()
        task.is_executable = False
        with pytest.raises(ValueError):
            task.execute()

    def test_execute_no_steps(self, mocker):
        task = Task()
        mock_save_result = mocker.patch.object(task, "save_result")
        task.execute()
        assert task.result.status == STATUS.ERROR
        assert task.result.exit_message == "No steps to execute"
        mock_save_result.assert_called_once()

    def test_execute_success(self, mocker):
        class CustomTask(Task):
            @step
            def step1(self):
                return {"result": "step1"}

        task = CustomTask()
        mock_save_result = mocker.patch.object(task, "save_result")

        task.execute()
        assert task.result.status == STATUS.SUCCESS
        mock_save_result.assert_called_once()
        assert task.result.data.get("step1") is not None

    def test_execute_error(self, mocker):
        class CustomTask(Task):
            @step
            def step1(self):
                raise ValueError("Test error")

        task = CustomTask()
        mock_save_result = mocker.patch.object(task, "save_result")

        task.execute()
        assert task.result.status == STATUS.ERROR
        assert task.result.exit_message == "Test error"
        assert task.result.data.get("step1") is not None
        assert task.result.data["step1"].status == STATUS.ERROR
        mock_save_result.assert_called_once()

    def test_execute_step(self):
        task = Task()
        task.result.data = {"test_step": StepResult()}
        step_name = "test_step"

        def test_step():
            return "test"

        task._execute_step(step_name, test_step)
        assert task.result.data[step_name].status == STATUS.SUCCESS
        assert task.result.data[step_name].data == "test"

    def test_execute_step_error(self):
        task = Task()
        task.result.data = {"test_step": StepResult()}
        step_name = "test_step"

        def test_step():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            task._execute_step(step_name, test_step)

        assert task.result.data[step_name].status == STATUS.ERROR
        assert task.result.data[step_name].data == {}

    def test_add_artifact(self, tmp_path):
        file_path = tmp_path / "test.txt"
        file_path.write_text("test")

        base_path_artifacts = tmp_path / "artifacts"

        assert not os.path.exists(str(base_path_artifacts))

        task = Task()
        task.task_id = "task-123456"
        task.add_artifact(str(file_path), str(base_path_artifacts))

        assert os.path.exists(str(base_path_artifacts))
        assert os.path.isfile(str(base_path_artifacts / "task-123456_test.txt"))

        assert task.result.artifacts == {
            "test.txt": str(base_path_artifacts / "task-123456_test.txt")
        }

    def test_add_artifact_no_exist(self, tmp_path):
        file_path = tmp_path / "test.txt"
        base_path_artifacts = tmp_path / "artifacts"

        task = Task()
        task.task_id = "task-123456"

        with pytest.raises(FileNotFoundError):
            task.add_artifact(str(file_path), str(base_path_artifacts))

        assert not os.path.exists(
            str(base_path_artifacts / "task-123456_test.txt")
        )
        assert task.result.artifacts == {}

    def test_save_result(self, tmp_path):
        task = Task()
        task.task_id = "task-123456"
        base_path_results = tmp_path / "results"
        assert not os.path.exists(str(base_path_results))

        task.save_result(str(base_path_results))

        assert os.path.exists(str(base_path_results))
        assert os.path.isfile(str(base_path_results / "task-123456.json"))

        with open(base_path_results / "task-123456.json", "r") as f:
            result = json.load(f)

        assert result == task.result.to_dict()
