from src import result_parser


def test_outliers_functions_remove_extreme():
    votes = [1]*10 + [2]*10 + [100]
    assert 100 not in result_parser.outliers_modified_z_score(votes)
    assert 100 not in result_parser.outliers_iqr(votes)
    assert 100 not in result_parser.outliers_z_score(votes)
