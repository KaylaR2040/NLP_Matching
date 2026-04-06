# nlp_project

`nlp_project` is a modular mentor-mentee matching system with persistent rerun state.

## What It Supports

- Parses mentor and mentee CSV data
- Computes weighted match scores across:
  - industry semantic similarity (technical vetting)
  - degree/major semantic similarity
  - personality semantic similarity
  - identity match
  - student organization overlap
  - graduation-year distance
- Uses mentee-provided ranking fields (1-4) to dynamically reweight each factor
- Applies an industry hard floor penalty for low technical alignment
- Generates ranked pairs and one-to-one assignments
- Persists state for:
  - rejected pairs
  - excluded users
  - locked pairs
  - global and per-mentee weight overrides
- Reruns cleanly with constraints applied

## Structure

- `main.py`: CLI entrypoint
- `mentor_matching/`: modular matching package
  - `parsing.py`: CSV parsing
  - `text_processing.py`: NLP preprocessing
  - `embeddings.py`: segmented semantic embeddings (`all-mpnet-base-v2`)
  - `scoring.py`: weighted scoring
  - `matching.py`: ranked pair generation + greedy assignment
  - `constraints.py`: exclusions/rejections/lock handling
  - `state_store.py`: persisted state
  - `pipeline.py`: orchestration and outputs
  - `reporting.py`: CLI display helpers
- `data/`: default sample CSVs
- `state/`: persisted state JSON
- `output/`: generated JSON/CSV output
- `scoring.csv`: ranking priority config for interactive weight controls

## Run

```bash
python nlp_project/main.py run --preview
```

## Common Commands

```bash
# Show current state
python nlp_project/main.py show-state

# Reject a pair and rerun
python nlp_project/main.py reject --mentee-id T001 --mentor-id M001 --rerun

# Exclude a mentor and rerun
python nlp_project/main.py exclude --role mentor --user-id M002 --rerun

# Set global weight and rerun
python nlp_project/main.py set-weight --scope global --factor industry --value 2.0 --rerun

# Set mentee-specific weight and rerun
python nlp_project/main.py set-weight --scope mentee --mentee-id T001 --factor identity --value 3.0 --rerun
```

## Scoring Config

[scoring.csv](./scoring.csv) controls:

- rank priority values used by state commands and weight overrides
- available direct-match sections (including `personality`)

## Output Files

- `nlp_project/output/latest_matches.json`
- `nlp_project/output/latest_assignments.csv`
