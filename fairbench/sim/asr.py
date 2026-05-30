"""
Accent-correlated ASR-degradation model (synthetic).

Word-error rates are keyed on *accent*, not on name or gender — mirroring the
documented reality that ASR systems transcribe accented speech less accurately
(and Cekura's own "Transcription Accuracy" metric, which weights names/nouns/
numbers most heavily). We degrade the transcript the grader actually sees, so an
identical good performance can lose a rubric keyword and fail — surfacing as
adverse impact downstream. Deletions/substitutions are deterministic per seed.

These numbers are illustrative synthetic priors for the demo, not measured WERs.
"""

from __future__ import annotations

import random
import string

# Baseline word-error rate per accent. general_american is the reference floor.
ACCENT_WER: dict[str, float] = {
    "general_american": 0.04,
    "aave": 0.10,
    "vietnamese_accented": 0.13,
    "indian_english": 0.15,
    "spanish_accented": 0.18,
}
DEFAULT_WER = 0.08

# ASR errors concentrate on content/domain words (Cekura: "highest weight on
# names, nouns, and numbers"). Boost the per-word error probability for the
# rubric keyword tokens the grader keys on, so degradation realistically eats
# competency evidence rather than filler words.
KEYWORD_ERROR_BOOST = 1.6
LONGWORD_ERROR_BOOST = 1.25
_LONGWORD_LEN = 7


def accent_wer(accent: str | None) -> float:
    return ACCENT_WER.get(accent or "", DEFAULT_WER)


def _norm(token: str) -> str:
    return token.strip(string.punctuation).lower()


def _garble(token: str, rng: random.Random) -> str:
    """Substitution error: corrupt the word so keyword matching misses it."""
    core = token.strip(string.punctuation)
    if len(core) < 3:
        return token
    chars = list(core)
    # swap two adjacent characters and drop the tail vowel-ish letter
    i = rng.randrange(len(chars) - 1)
    chars[i], chars[i + 1] = chars[i + 1], chars[i]
    if len(chars) > 4 and rng.random() < 0.5:
        chars.pop()
    return "".join(chars)


def degrade(
    text: str,
    wer: float,
    rng: random.Random,
    keywords: set[str] | None = None,
) -> tuple[str, float]:
    """
    Apply deletions/substitutions to ``text`` at roughly ``wer`` word-error rate.

    Returns ``(degraded_text, realized_wer)``. ``keywords`` (normalized, lowercase)
    receive a higher error probability to model ASR dropping domain terms.
    """
    keywords = keywords or set()
    tokens = text.split()
    if not tokens:
        return text, 0.0

    out: list[str] = []
    errors = 0
    for tok in tokens:
        norm = _norm(tok)
        p = wer
        if norm in keywords or any(norm in kw or kw in norm for kw in keywords):
            p *= KEYWORD_ERROR_BOOST
        elif len(norm) >= _LONGWORD_LEN:
            p *= LONGWORD_ERROR_BOOST
        p = min(p, 0.9)

        if rng.random() < p:
            errors += 1
            if rng.random() < 0.45:
                continue  # deletion — token vanishes from the transcript
            out.append(_garble(tok, rng))  # substitution
        else:
            out.append(tok)

    realized = errors / len(tokens)
    return " ".join(out), round(realized, 3)
