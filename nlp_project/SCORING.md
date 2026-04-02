# Matching Scoring

This document explains how mentor/mentee match scores are calculated, how weights are derived from `scoring.csv`, and where to add a worked explain-run example.

## Overview

Each mentor/mentee pair gets a final score made from two pieces:

- `nlp_weight` from NLP similarity
- `1 - nlp_weight` from direct-match categories combined

The direct-match categories are:

- `industry`
- `degree`
- `orgs`
- `identity`
- `grad_year`

The values come from [scoring.csv](/home/connor/ECE495_IndepStudy/Content/Code/nlp_project/scoring.csv).

## Scoring CSV

The scoring configuration file lives at [scoring.csv](/home/connor/ECE495_IndepStudy/Content/Code/nlp_project/scoring.csv).

It controls two things:

- the priority value assigned to student rankings `1`, `2`, `3`, and `4` for each direct-match section
- the global `nlp_weight` used by both the CLI matching pipeline and the backend API matcher

The file format is:

```csv
section,rank_1,rank_2,rank_3,rank_4,nlp_weight
industry,0,11,44,100,
degree,0,11,44,100,
orgs,0,11,44,100,
identity,0,11,44,100,
grad_year,0,11,44,100,
nlp,,,,,0.5
```

Rules:

- each direct-match section must have one row: `industry`, `degree`, `orgs`, `identity`, `grad_year`
- the `nlp` row must define `nlp_weight`
- `nlp_weight` must be between `0.0` and `1.0`
- direct-match rows use `rank_1` through `rank_4`
- the `nlp` row does not use `rank_1` through `rank_4`

Changing this file changes scoring behavior without editing Python code.

## Final Score Formula

The final score is:

```text
final_score =
  (industry_score  * industry_weight) +
  (degree_score    * degree_weight) +
  (orgs_score      * orgs_weight) +
  (identity_score  * identity_weight) +
  (grad_year_score * grad_year_weight) +
  (nlp_score       * nlp_weight)
```

Where:

- `nlp_weight` comes from `scoring.csv`
- the five direct-match weights together sum to at most `1 - nlp_weight`

If the direct-match priorities all map to `0`, then:

- all five direct-match weights become `0`
- `nlp_weight` stays whatever is defined in `scoring.csv`
- the unused direct-match half is intentionally left unused

## Component Scores

Each category produces a score from `0.0` to `1.0`:

- `industry_score`: overlap similarity between mentee interests and mentor industry/domain data
- `degree_score`: overlap similarity between degree programs
- `orgs_score`: overlap similarity between organizations
- `identity_score`: identity/pronoun match score
- `grad_year_score`: closeness of graduation years
- `nlp_score`: cosine similarity from the NLP embedding pipeline

Higher is better in every case.

## How Rankings Become Weights

Students rank each direct-match category from `1` to `4` for importance.

These rankings are converted to priority values using `scoring.csv`.

With the default `scoring.csv`, the mapping is:

| Ranking | Priority value |
| --- | ---: |
| `1` | `0` |
| `2` | `11` |
| `3` | `44` |
| `4` | `100` |

These are not percentages. They are only relative priority values used to divide up the direct-match half of the final score.

## Direct-Match Weight Calculation

### Step 1: Convert rankings to priorities

For each direct-match category:

```text
priority = ranking_to_priority_value(ranking)
```

### Step 2: Sum direct priorities

```text
total_priority =
  industry_priority +
  degree_priority +
  orgs_priority +
  identity_priority +
  grad_year_priority
```

### Step 3: Reserve the score shares

```text
nlp_weight = value from scoring.csv
direct_match_share = 1.0 - nlp_weight
```

### Step 4: Split the direct-match half

For each direct-match category:

```text
direct_weight = direct_match_share * (category_priority / total_priority)
```

If `total_priority == 0`, then:

```text
industry_weight = 0
degree_weight = 0
orgs_weight = 0
identity_weight = 0
grad_year_weight = 0
nlp_weight = value from scoring.csv
```

## Example

Given rankings:

- `industry = 1`
- `degree = 2`
- `orgs = 2`
- `identity = 4`
- `grad_year = 3`

Mapped priorities:

- `industry = 0`
- `degree = 11`
- `orgs = 11`
- `identity = 100`
- `grad_year = 44`

Total priority:

```text
0 + 11 + 11 + 100 + 44 = 166
```

Final weights:

```text
industry_weight  = 0.5 * (0   / 166) = 0.000000
degree_weight    = 0.5 * (11  / 166) = 0.033133
orgs_weight      = 0.5 * (11  / 166) = 0.033133
identity_weight  = 0.5 * (100 / 166) = 0.301205
grad_year_weight = 0.5 * (44  / 166) = 0.132530
nlp_weight       = 0.5
```

Printed as percentages:

- `industry = 0.0%`
- `degree = 3.3%`
- `orgs = 3.3%`
- `identity = 30.1%`
- `grad_year = 13.3%`
- `nlp = 50.0%`

The displayed weights are formatted to one decimal place. The underlying stored weights still sum exactly as calculated.

## Explanation Output Format

For debugging and explainability, the printed explanation output should follow this format:

```text
- industry   score=... weight=...
- degree     score=... weight=...
- orgs       score=... weight=...
- identity   score=... weight=...
- grad_year  score=... weight=...
- nlp        score=... weight=50.0%
```

The displayed weight is the final scoring weight, shown as a percentage out of `100%`.

## Code Locations

Current scoring logic lives in:

- `nlp_project/scoring.csv`
- `nlp_project/mentor_matching/scoring.py`
- `nlp_project/mentor_matching/scoring_config.py`
- `nlp_project/mentor_matching/reporting.py`
- `backend/api/models/mentee.py`
- `backend/api/scoring_config.py`
- `backend/api/matcher.py`

## Explain Run

Use this section later to paste a real explain-run output for one mentee/mentor pair.

### Inputs

```text
[Add mentee inputs here]
[Add mentor inputs here]
[Add ranking values here]
```

### Derived Weights

```text
[Add mapped priorities here]
[Add total priority here]
[Add final weights here]
```

### Component Scores

```text
[Add industry_score here]
[Add degree_score here]
[Add orgs_score here]
[Add identity_score here]
[Add grad_year_score here]
[Add nlp_score here]
```

### Final Explanation Output

```text
[Paste explanation output here]
```

### Notes

```text
[Add observations here]
```
