# Neon Postgres Setup

## 1. Create a Neon Project

1. Go to [console.neon.tech](https://console.neon.tech)
2. Sign in (or create a free account)
3. Click **New Project**
4. Choose a project name (e.g., `nlp-mentor-matching`)
5. Select the region closest to your Render deployment (e.g., `us-east-1`)
6. Click **Create Project**

## 2. Get the Connection String

1. In your Neon project dashboard, click **Connection Details** (or the "Connect" button)
2. Select **Connection string** tab
3. Make sure **sslmode=require** is included
4. Copy the string — it looks like:
   ```
   postgresql://neondb_owner:AbCdEfGh@ep-cool-name-12345678.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```

## 3. Set the Environment Variable

**Local `.env` file** (`wrapper/backend/.env`):
```env
DATABASE_URL=postgresql://neondb_owner:YOUR_PASS@YOUR_HOST/neondb?sslmode=require
WRAPPER_MENTOR_STORAGE_MODE=postgres
```

**Render dashboard** (for production):
- Go to your Render service → Environment → Add Environment Variable
- Key: `DATABASE_URL`
- Value: the full connection string
- Also add: `WRAPPER_MENTOR_STORAGE_MODE=postgres`

## 4. Initialize the Schema

Run this once (safe to re-run — uses `CREATE TABLE IF NOT EXISTS`):

```bash
# From repo root, with venv activated
python wrapper/backend/scripts/init_schema.py \
  --database-url "postgresql://..."
```

Or use the env var:
```bash
export DATABASE_URL="postgresql://..."
python wrapper/backend/scripts/init_schema.py
```

**Expected output:**
```
Connecting to database…
Schema initialized successfully.
Tables created (or already existed): mentors, config_lists, match_results
```

## 5. Seed Config Lists from .txt Files

Run once to populate config lists from the source `.txt` files:

```bash
python wrapper/backend/scripts/seed_config_lists.py \
  --database-url "postgresql://..."
```

**Expected output:**
```
Connecting to database…
  OK   ncsu_orgs: 612 lines from ncsu_orgs.txt
  OK   concentrations: 12 lines from concentrations.txt
  OK   grad_programs: 8 lines from grad_programs.txt
  OK   abm_programs: 3 lines from abm_programs.txt
  OK   phd_programs: 5 lines from phd_programs.txt

Seeding complete. Verify with:
  SELECT list_key, label, length(content) FROM config_lists;
```

This script is idempotent — running it again will overwrite the rows with the same content.

## 6. Verify Tables Were Created

In the Neon console, open the **SQL Editor** and run:

```sql
-- List all tables
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
-- → config_lists, match_results, mentors

-- Verify config lists seeded
SELECT list_key, label, length(content) AS chars FROM config_lists;

-- Check mentor table structure
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'mentors'
ORDER BY ordinal_position;
```

## 7. Verify the Backend Connects

With `DATABASE_URL` set and backend running locally:

```bash
curl http://localhost:8000/config/orgs | head -c 200
# → ["1911 Consulting","Acappology","Accounting Society",...]
```

If you get `[]`, the DB row may be empty — run the seed script.

If you get a connection error, check:
- The connection string is correct (no extra spaces/quotes)
- `sslmode=require` is appended
- Your IP is allowed (Neon allows all IPs by default for new projects)

## 8. Managing the Database

**Neon SQL Editor** — quick queries:
```sql
SELECT count(*) FROM mentors;
SELECT list_key, updated_at FROM config_lists;
SELECT id, run_at, run_by FROM match_results ORDER BY run_at DESC LIMIT 5;
```

**psql** — from a terminal:
```bash
psql "postgresql://user:pass@host/dbname?sslmode=require"
\dt        -- list tables
\d mentors -- describe mentor table
```

## 9. Resetting the Database

To start clean (drops all data):
```sql
DROP TABLE IF EXISTS match_results;
DROP TABLE IF EXISTS config_lists;
DROP TABLE IF EXISTS mentors;
```

Then re-run `init_schema.py` and `seed_config_lists.py`.
