from src.governance.controls_matrix import CONTROLS


def test_controls_matrix_has_core_functions():
    funcs = {row[0] for row in CONTROLS}
    assert {"Govern", "Map", "Measure", "Manage"}.issubset(funcs)
