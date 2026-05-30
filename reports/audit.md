# FairBench Integrity Audit

Performances: 960 | Fairness cohort (qualified): 320 | Synthetic only: True

## Verdict: REVIEW - bias flagged

## Grader reliability

n = 960 | agreement = 0.829 | false_pass = 0.0 | false_fail = 0.171

## Fairness — accent

| Group | Pass rate | Impact ratio | N | Flag |
|-------|-----------|--------------|---|------|
| aave | 53.1% | 0.680 | 64 | YES |
| general_american | 78.1% | 1.000 | 64 |  |
| indian_english | 43.8% | 0.560 | 64 | YES |
| spanish_accented | 21.9% | 0.280 | 64 | YES |
| vietnamese_accented | 46.9% | 0.600 | 64 | YES |

## Fairness — gender

| Group | Pass rate | Impact ratio | N | Flag |
|-------|-----------|--------------|---|------|
| female | 48.7% | 1.000 | 160 |  |
| male | 48.7% | 1.000 | 160 |  |

## Fairness — name_origin

| Group | Pass rate | Impact ratio | N | Flag |
|-------|-----------|--------------|---|------|
| anglo | 57.5% | 1.000 | 80 |  |
| east_asian | 50.0% | 0.870 | 80 |  |
| latino | 42.5% | 0.739 | 80 | YES |
| south_asian | 45.0% | 0.783 | 80 | YES |

## ASR bias

- spanish_accented: avg WER 0.224, gap vs best 0.175
- indian_english: avg WER 0.18, gap vs best 0.131
- vietnamese_accented: avg WER 0.163, gap vs best 0.114
