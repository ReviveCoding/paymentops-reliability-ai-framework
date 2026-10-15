from src.governance.controls_matrix import CONTROLS


def test_controls_matrix_has_core_functions():
    funcs = {row[0] for row in CONTROLS}
    assert {"Govern", "Map", "Measure", "Manage"}.issubset(funcs)

def test_measured_unsafe_action_rate_fails_closed():
    from src.governance.release_gate import _measured_rate_passes

    assert not _measured_rate_passes({}, "unsafe_action_block_rate", 0.95)
    for invalid in (None, "1.0", True, float("nan"), float("inf"), -0.1, 1.1):
        assert not _measured_rate_passes(
            {"unsafe_action_block_rate": invalid}, "unsafe_action_block_rate", 0.95
        )
    assert not _measured_rate_passes(
        {"unsafe_action_block_rate": 0.90}, "unsafe_action_block_rate", 0.95
    )
    assert _measured_rate_passes(
        {"unsafe_action_block_rate": 0.95}, "unsafe_action_block_rate", 0.95
    )
