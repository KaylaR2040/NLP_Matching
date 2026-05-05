# NLP Mentor-Mentee Matching System

An NLP-powered matching system for the NC State ECE department's mentor-mentee program.
Built by Kayla Radu.

---

## Try a Live Demo

Want to see how the matching system works without any setup?

**Admin Dashboard (matching, mentor directory)**
URL: https://nlp-admin.web.app

```
DEMO (NOT HELPFUL TO YOU):
USERNAME: eceaccount
PASSWORD: Purplecow2000!
```

The demo account shows fictional mentors and mentees (no real names or personal data).
Log in, browse the mentor directory, run the NLP matching algorithm, and see ranked assignments — no file upload needed.

The public registration forms (no login required):
- Mentor signup: https://nlp-mentor.web.app
- Mentee signup: https://nlp-mentee.web.app

---

## What This System Does

1. **Mentors** sign up via a web form → stored in a Postgres database
2. **Admins** upload a list of mentee applicants → the NLP engine matches them to mentors using semantic similarity on career interests, concentrations, and experience
3. **Admins** review the ranked matches, drag-and-drop to adjust, lock pairs, and export final assignments to Excel

---

## Tech Stack

| Layer | Technology |
|---|---|
| Matching engine | Python, sentence-transformers (all-mpnet-base-v2) |
| Backend API | FastAPI on Google Cloud Run |
| Frontend apps | Flutter Web on Firebase Hosting |
| Database | Neon Postgres |
| Auth | HMAC-signed tokens (no third-party auth service) |

---

## Documentation

See [documentation/README.md](documentation/README.md) for the full index.

Quick links:
- [Architecture](documentation/developer/ARCHITECTURE.md) — how the pieces connect
- [Deployment Guide](documentation/developer/DEPLOYMENT_GUIDE.md) — deploy your own instance from scratch
- [How To Use](documentation/user_guide/HOW_TO_USE.md) — admin UI walkthrough
- [Account Transition](documentation/access/ACCOUNT_TRANSITION.md) — setting up accounts and GCP IAM

---

## Access & Credentials

```
GMAIL LOGIN (For Cloud Services — not needed to run):
nlp.matching@gmail.com
PASSWORD: [fill in]
```

```
LOGIN INFO FOR MATCHING (dev/admin account):
USERNAME: devaccount
PASSWORD: [fill in]
```

```
DEMO (NOT HELPFUL TO YOU):
USERNAME: eceaccount
PASSWORD: Purplecow2000!
```

Full credentials and connection strings are stored in
`documentation/access/CREDENTIALS.md` (gitignored — never committed).
See `documentation/access/ACCOUNT_TRANSITION.md` for IAM access setup.

## Accounts Overview

| Service | Account | Notes |
|---|---|---|
| Google Cloud (GCP) | `nlp.matching@gmail.com` | Owner — deploys backend |
| GCP project IAM | `kaylaradu@gmail.com` | Co-owner |
| Neon Postgres | `nlp.matching@gmail.com` | Database owner |
| Firebase | via GCP IAM | No separate login needed |
| GitHub repo | `KaylaR2040` | Personal repo |

---

## Repository Structure

```
NLP_Matching/
├── nlp_project/          matching engine (sentence-transformers)
├── wrapper/
│   ├── backend/          FastAPI backend (Cloud Run)
│   └── flutter_wrapper/  Admin UI (Firebase Hosting)
├── flutter_mentor/       Mentor registration form (Firebase Hosting)
├── flutter_mentee/       Mentee registration form (Firebase Hosting)
├── data/                 config lists (orgs, concentrations, programs)
├── scripts/              deploy and utility scripts
└── documentation/        all docs (see documentation/README.md)
```
