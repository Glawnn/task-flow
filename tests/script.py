"""This script is used to run tests from the command line."""

import pytest
import sys


def run_tests():
    """Run the tests"""
    sys.exit(pytest.main(["-v", "tests/"]))


def run_tests_with_cov():
    """Run the tests with coverage"""
    sys.exit(pytest.main(["-v", "--cov=pdp", "--cov-fail-under=80", "tests/"]))
