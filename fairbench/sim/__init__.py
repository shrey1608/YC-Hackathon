"""
FairBench offline simulation.

Generates realistic trainee transcripts per behavior, applies an accent-correlated
ASR-degradation model, then runs the REAL grader over the degraded text. Adverse
impact and reliability loss therefore *emerge* from the pipeline instead of being
hard-coded — that is what makes the integrity engine testable and validatable with
no external API keys.
"""

from fairbench.sim.asr import ACCENT_WER, degrade
from fairbench.sim.eval import SimulatedEval, simulate_battery
from fairbench.sim.transcripts import generate_transcript

__all__ = [
    "ACCENT_WER",
    "degrade",
    "SimulatedEval",
    "simulate_battery",
    "generate_transcript",
]
