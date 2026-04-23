# Database Schema

All tables are in Neon Postgres. Schema is initialized by `wrapper/backend/scripts/init_schema.py`.

## mentors

Stores mentor profiles. Managed by `wrapper/backend/app/mentor_store.py`.

| Column | Type | Description |
|---|---|---|
| `mentor_id` | TEXT (PK) | Unique identifier (UUID or email-derived) |
| `email` | TEXT | Mentor email address |
| `first_name` | TEXT | |
| `last_name` | TEXT | |
| `full_name` | TEXT | Concatenated full name |
| `linkedin_url` | TEXT | LinkedIn profile URL |
| `profile_photo_url` | TEXT | Avatar URL (unavatar.io fallback) |
| `current_company` | TEXT | Current employer |
| `current_job_title` | TEXT | |
| `current_location` | TEXT | Full location string |
| `current_city` | TEXT | |
| `current_state` | TEXT | |
| `degrees_text` | TEXT | Free-text degree summary |
| `industry_focus_area` | TEXT | Industry/domain focus |
| `professional_experience` | TEXT | Bio/work history |
| `about_yourself` | TEXT | Personal statement |
| `students_interested` | TEXT | Types of students mentor wants to work with |
| `phone` | TEXT | |
| `preferred_contact_method` | TEXT | |
| `is_active` | BOOLEAN | `TRUE` = active; `FALSE` = soft-deleted |
| `source_csv_path` | TEXT | Path of CSV used to import this mentor |
| `source_timestamp` | TIMESTAMPTZ | When the source CSV was imported |
| `last_modified_at` | TIMESTAMPTZ | Last update timestamp |
| `last_modified_by` | TEXT | Username who last modified |
| `last_enriched_at` | TIMESTAMPTZ | When LinkedIn enrichment last ran |
| `enrichment_status` | TEXT | `ok`, `failed`, `pending`, `skipped` |
| `enrichment_provider_metadata` | JSONB | Raw enrichment API response |
| `extra_fields` | JSONB | Any additional CSV columns not in the schema |

**Indexes:**
- `mentors_email_idx` on `email`
- `mentors_is_active_idx` on `is_active`

---

## config_lists

Replaces the flat `.txt` files (`ncsu_orgs.txt`, `concentrations.txt`, etc.). Each row stores one config list as newline-separated text.

| Column | Type | Description |
|---|---|---|
| `list_key` | TEXT (PK) | Identifier: `ncsu_orgs`, `concentrations`, `grad_programs`, `abm_programs`, `phd_programs` |
| `label` | TEXT | Human-readable name (e.g., "NCSU Organizations") |
| `content` | TEXT | Newline-separated list items (mirrors `.txt` file format) |
| `updated_at` | TIMESTAMPTZ | Last update timestamp (defaults to `NOW()`) |
| `updated_by` | TEXT | Username or `seed_script` |

**Known list_key values:**

| list_key | label | Source file |
|---|---|---|
| `ncsu_orgs` | NCSU Organizations | `data/ncsu_orgs.txt` |
| `concentrations` | ECE Concentrations | `data/concentrations.txt` |
| `grad_programs` | Graduate Programs (MS) | `data/grad_programs.txt` |
| `abm_programs` | ABM Degree Programs | `data/abm_programs.txt` |
| `phd_programs` | PhD Programs | `data/phd_programs.txt` |

---

## match_results

Records each `/run_match` invocation for audit trail and history display.

| Column | Type | Description |
|---|---|---|
| `id` | SERIAL (PK) | Auto-incrementing run ID |
| `run_at` | TIMESTAMPTZ | When the match was run (defaults to `NOW()`) |
| `run_by` | TEXT | Username who triggered the match |
| `mentee_source` | TEXT | Filename of the uploaded mentee CSV |
| `mentor_source` | TEXT | `mentor_manager` or uploaded filename |
| `summary` | JSONB | Match summary (mentee count, assignments count, etc.) |
| `assignments` | JSONB | Full assignments array from `latest_matches.json` |
| `top_ranked_pairs` | JSONB | Top ranked pairs array |
| `stdout` | TEXT | First 10,000 chars of nlp_project subprocess output |

**Indexes:**
- `match_results_run_at_idx` on `run_at DESC`

---

## Relationships

These tables are independent (no foreign keys):
- `mentors` ↔ `config_lists`: no relationship
- `match_results` stores match output as JSONB (denormalized) rather than linking to `mentors` rows, because the mentor data at match time may change later

---

## Useful Queries

```sql
-- Count active mentors
SELECT count(*) FROM mentors WHERE is_active = TRUE;

-- View config list row counts
SELECT list_key, label,
       array_length(string_to_array(content, E'\n'), 1) AS line_count,
       updated_at
FROM config_lists;

-- View last 10 match runs
SELECT id, run_at, run_by, mentee_source, mentor_source,
       (summary->>'assignments')::int AS assignments
FROM match_results
ORDER BY run_at DESC
LIMIT 10;

-- Get all mentors enriched in the last week
SELECT mentor_id, full_name, enrichment_status, last_enriched_at
FROM mentors
WHERE last_enriched_at > NOW() - INTERVAL '7 days';
```
