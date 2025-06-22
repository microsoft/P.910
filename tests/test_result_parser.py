import sys
import os

# Ensure that 'src' directory is on sys.path so that we can import from src.result_parser
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.result_parser import outliers_modified_z_score


def test_outliers_modified_z_score():
    values = [1, 2, 3, 50]
    result = outliers_modified_z_score(values)
    assert result == [1, 2, 3]

