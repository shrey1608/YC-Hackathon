"""Adapter contract tests — all offline (no network, no keys)."""


from fairbench.adapters.eval.cekura import map_runs
from fairbench.adapters.llm.nemotron import NemotronLLM
from fairbench.adapters.pipeline import make_eval
from fairbench.adapters.stt.gradium import word_error_rate
from fairbench.sim.eval import SimulatedEval


def test_cekura_map_runs_to_integrity_rows():
    payload = {
        "runs": {
            "101": {
                "id": 101,
                "success": True,
                "personality_name": "spanish_accented",
                "scenario_name": "pharmacy",
                "expected_outcome": {"score": True},
                "evaluation": {"metrics": [{"name": "Transcription Accuracy", "score": 82}]},
                "status": "completed",
            },
            "102": {
                "id": 102,
                "success": False,
                "personality_name": "general_american",
                "expected_outcome": {"score": True},
                "evaluation": {"metrics": [{"name": "Transcription Accuracy", "score": 0.97}]},
                "status": "completed",
            },
        }
    }
    rows = map_runs(payload)
    by_id = {r["persona_id"]: r for r in rows}
    assert by_id["101"]["group"]["accent"] == "spanish_accented"
    assert by_id["101"]["passed"] is True
    assert by_id["101"]["expert_label"] is True
    assert by_id["101"]["asr_wer"] == 0.18          # 1 - 82/100
    assert by_id["102"]["asr_wer"] == 0.03          # 1 - 0.97
    assert by_id["102"]["passed"] is False


def test_word_error_rate():
    assert word_error_rate("take it with food", "take it with food") == 0.0
    assert word_error_rate("take it with food", "take with food") == 0.25  # one deletion / 4
    assert word_error_rate("hello", "") == 1.0


async def test_nemotron_offline_mock():
    llm = NemotronLLM(endpoint="", api_key=None)
    text = await llm.complete([{"role": "user", "content": "hi"}])
    assert "pharmacist" in text.lower()
    streamed = "".join([tok async for tok in llm.stream([{"role": "user", "content": "hi"}])])
    assert streamed == text


def test_make_eval_falls_back_to_simulator(monkeypatch):
    monkeypatch.delenv("CEKURA_API_KEY", raising=False)
    assert isinstance(make_eval(), SimulatedEval)
