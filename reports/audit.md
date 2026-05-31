# FairBench Integrity Audit

Performances: 1920 | Fairness cohort (qualified): 640 | Synthetic only: True

## Verdict: REVIEW - bias flagged

## Grader reliability

n = 1920 | agreement = 0.847 | false_pass = 0.0 | false_fail = 0.153

## Fairness — accent

| Group | Pass rate | Impact ratio | N | Flag |
|-------|-----------|--------------|---|------|
| aave | 57.8% | 0.661 | 128 | YES |
| general_american | 87.5% | 1.000 | 128 |  |
| indian_english | 48.4% | 0.554 | 128 | YES |
| spanish_accented | 25.0% | 0.286 | 128 | YES |
| vietnamese_accented | 51.6% | 0.589 | 128 | YES |

## Fairness — gender

| Group | Pass rate | Impact ratio | N | Flag |
|-------|-----------|--------------|---|------|
| female | 54.1% | 1.000 | 320 |  |
| male | 54.1% | 1.000 | 320 |  |

## Fairness — name_origin

| Group | Pass rate | Impact ratio | N | Flag |
|-------|-----------|--------------|---|------|
| anglo | 48.7% | 0.848 | 160 |  |
| east_asian | 57.5% | 1.000 | 160 |  |
| latino | 56.2% | 0.978 | 160 |  |
| south_asian | 53.7% | 0.935 | 160 |  |

## ASR bias

- spanish_accented: avg WER 0.219, gap vs best 0.168
- indian_english: avg WER 0.185, gap vs best 0.134
- vietnamese_accented: avg WER 0.159, gap vs best 0.108
