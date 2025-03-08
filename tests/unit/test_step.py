from task_flow.constants import STATUS
from task_flow.step import step
from task_flow.step import StepResult


class TestStepDecorator:

    def test_step_decorator_marks_function_as_step(self):
        @step
        def sample_function():
            pass

        assert hasattr(sample_function, "is_step")
        assert sample_function.is_step is True

    def test_step_decorator_preserves_functionality(self):
        @step
        def sample_function(x, y):
            return x + y

        result = sample_function(2, 3)
        assert result == 5


class TestStepResult:

    def test_step_result_initialization(self):
        result = StepResult()
        assert result.message == ""
        assert result.status == "PENDING"
        assert isinstance(result.status, STATUS)
        assert result.data == {}

    def test_step_result_status_conversion(self):
        result = StepResult(status="SUCCESS")
        assert result.status == "SUCCESS"
        assert isinstance(result.status, STATUS)
