# nlp_project2

`nlp_project2` is a modular mentor-mentee matching system with persistent rerun state.

## What It Supports

- Parses mentor and mentee CSV data
- Computes weighted match scores across:
  - industry/domain overlap
  - topic overlap
  - communication style overlap
  - availability overlap
  - NLP profile similarity
- Uses mentee-provided ranking fields (if present) to influence category weights
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
  - `embeddings.py`: deterministic embeddings
  - `scoring.py`: weighted scoring
  - `matching.py`: ranked pair generation + greedy assignment
  - `constraints.py`: exclusions/rejections/lock handling
  - `state_store.py`: persisted state
  - `pipeline.py`: orchestration and outputs
  - `reporting.py`: CLI display helpers
- `data/`: default sample CSVs
- `state/`: persisted state JSON
- `output/`: generated JSON/CSV output

## Run

```bash
python nlp_project2/main.py run --preview
```

## Common Commands

```bash
# Show current state
python nlp_project2/main.py show-state

# Reject a pair and rerun
python nlp_project2/main.py reject --mentee-id T001 --mentor-id M001 --rerun

# Exclude a mentor and rerun
python nlp_project2/main.py exclude --role mentor --user-id M002 --rerun

# Set global weight and rerun
python nlp_project2/main.py set-weight --scope global --factor industry --value 2.0 --rerun

# Set mentee-specific weight and rerun
python nlp_project2/main.py set-weight --scope mentee --mentee-id T001 --factor nlp --value 3.0 --rerun
```

## Output Files

- `nlp_project2/output/latest_matches.json`
- `nlp_project2/output/latest_assignments.csv`
