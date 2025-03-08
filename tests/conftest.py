import pytest

def pytest_collection_modifyitems(config, items):
    for item in items:
        if "tests/unit/" in item.nodeid:
            item.add_marker(pytest.mark.unit)
        elif "tests/integration/" in item.nodeid:
            item.add_marker(pytest.mark.integration)

