from fairbench.core.integrity import audit_report, demo_results


def test_demo_audit_flags_review():
    report = audit_report(demo_results())
    assert "REVIEW" in report["verdict"]
    fairness = report["fairness"]["accent"]
    assert fairness["spanish_accented"]["adverse_impact"]
    assert report["asr_bias"]


def test_good_anglo_passes_demo():
    results = demo_results()
    by_id = {r.persona_id: r for r in results}
    assert by_id["good__anglo_m"].passed
    assert not by_id["good__spanish_f"].passed
