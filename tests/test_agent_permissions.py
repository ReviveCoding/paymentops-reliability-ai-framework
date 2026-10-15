from src.agents.permission_gates import permission_gate


def test_permission_gate_blocks_unsafe_auto_resolve():
    result = permission_gate("auto_resolve", 0.8, {"required_action", "policy_rule"})
    assert not result["allowed"]

def test_permission_gate_rejects_nonfinite_out_of_range_and_non_numeric_scores():
    slots = {"required_action", "policy_rule"}
    for score in (float("nan"), float("inf"), -0.01, 1.01, True, None, "0.1"):
        result = permission_gate("auto_resolve", score, slots)
        assert result["allowed"] is False, f"Risk score {score!r} was allowed"


def test_permission_gate_rejects_unknown_action_and_missing_evidence():
    slots = {"required_action", "policy_rule"}
    assert not permission_gate("release_payment", 0.1, slots)["allowed"]
    assert not permission_gate("analyst_review", 0.5, set())["allowed"]


def test_permission_gate_preserves_supported_action_boundaries():
    slots = {"required_action", "policy_rule"}
    assert permission_gate("auto_resolve", 0.49, slots)["allowed"]
    assert not permission_gate("auto_resolve", 0.50, slots)["allowed"]
    assert permission_gate("block_payment", 0.65, slots)["allowed"]
    assert not permission_gate("block_payment", 0.649, slots)["allowed"]
    assert permission_gate("compliance_escalation", 0.80, slots)["allowed"]
    assert permission_gate("analyst_review", 0.50, slots)["allowed"]
