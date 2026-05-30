from fairbench.battery import build_battery


def test_battery_counts():
    full = build_battery(slim=False)
    slim = build_battery(slim=True)
    assert len(full) == 240
    assert len(slim) == 30


def test_battery_cell_fields():
    case = build_battery(slim=True)[0]
    assert "persona_id" in case
    assert "expert_label" in case
    assert "group" in case
    assert "voice" in case
