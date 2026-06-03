from src.agents.permission_gates import permission_gate


def test_permission_gate_blocks_unsafe_auto_resolve():
    result = permission_gate("auto_resolve", 0.8, {"required_action", "policy_rule"})
    assert not result["allowed"]
