# ECE Mentor-Mentee Matching System

An NLP-powered platform that matches NC State ECE students with alumni mentors. Built by Kayla Radu for the NC State ECE department's mentor-mentee program.

The system handles the full pipeline — mentors sign up via a public form, admins run an NLP matching algorithm against a mentee list, review and adjust the ranked assignments, then export to Excel. All data is stored in a Postgres database; no spreadsheet management required.

---

## Live Demo

**Admin dashboard** — matching, mentor directory, match history:

| | |
|---|---|
| URL | https://nlp-admin.web.app |
| Username | `eceaccount` |
| Password | `Purplecow2000!` |

The demo account shows fictional mentors and mentees only — no real student data. Log in, browse the mentor directory, upload a mentee file (or use the pre-loaded demo mentees), run the NLP matching algorithm, and see ranked assignments with scores.

**Public registration forms** (no login required):
| Form | URL |
|---|---|
| Mentor signup | https://nlp-mentor.web.app |
| Mentee interest | https://nlp-mentee.web.app |

---

## What It Does

### For mentors
- Fill out a public web form with their background, career focus, and student preferences
- Duplicate email detection — if a mentor resubmits, they're offered the option to update their existing record instead of creating a duplicate

### For admins
- **Mentor Manager** — view, search, import from CSV/XLSX, and edit all mentor records
- **Matching Dashboard** — upload a mentee CSV, run the NLP algorithm, see ranked assignments, drag-and-drop to reassign, lock pairs, and export to Excel
- **Dev Dashboard** — edit the org/concentration/program dropdown lists live (changes hit the database immediately, no redeploy needed)
- **Match History** — full audit trail of every match run with timestamps and output

### For mentees
- Fill out a public interest form with their program, career interests, and goals
- Confirmation screen on submission

---

## How the Matching Works

The matching engine uses **sentence-transformers** (`all-mpnet-base-v2`) to compute semantic similarity between mentee and mentor profiles. It scores pairs across multiple dimensions — career interests, ECE concentration, student organizations, and experience level — then ranks and assigns mentees to mentors respecting capacity constraints.

Unlike keyword matching, it understands that "machine learning" and "AI/ML" are related, or that a robotics mentor is a reasonable fit for an autonomy-focused mentee.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Matching engine | Python, sentence-transformers (all-mpnet-base-v2) |
| Backend API | FastAPI, deployed on Google Cloud Run |
| Admin UI | Flutter Web, deployed on Firebase Hosting |
| Mentor / Mentee forms | Flutter Web, deployed on Firebase Hosting |
| Database | Neon Postgres (mentors, mentee submissions, config lists, match history) |
| Auth | HMAC-signed JWT tokens — no third-party auth service |
| Image build | Google Cloud Build (no local Docker required) |

---

## Repository Structure

```
NLP_Matching/
├── nlp_project/          NLP matching engine (sentence-transformers)
├── wrapper/
│   ├── backend/          FastAPI backend (Cloud Run)
│   └── flutter_wrapper/  Admin UI (Firebase Hosting)
├── flutter_mentor/       Mentor registration form (Firebase Hosting)
├── flutter_mentee/       Mentee registration form (Firebase Hosting)
├── data/                 config lists (orgs, concentrations, programs)
├── scripts/              deploy scripts (backend + frontends)
└── documentation/        architecture, schema, deployment, and usage guides
```

---

## Deploying Your Own Instance

The system is designed to be fully redeployable to a new GCP project. You need:
- A Google Cloud project with billing enabled (stays within free tier for normal academic usage)
- A Neon Postgres database (free tier)
- A Firebase project linked to the GCP project

All deploy steps are scripted — no manual Cloud Console clicking required after initial setup.

```bash
# Deploy backend (builds image on Cloud Build, no local Docker needed)
python3 scripts/redeploy_backend.py

# Deploy all three Flutter frontends to Firebase Hosting
python3 scripts/redeploy_frontends.py
```
