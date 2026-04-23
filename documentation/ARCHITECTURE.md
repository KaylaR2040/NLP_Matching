# Architecture

## Folder Roles

| Folder | Role |
|---|---|
| `nlp_project/` | Python matching engine. Standalone CLI + importable package. Uses `sentence-transformers` to score mentor–mentee pairs. |
| `wrapper/backend/` | FastAPI REST API. Orchestrates the matching engine, manages mentor data, serves config lists, handles auth. |
| `wrapper/flutter_wrapper/` | Admin Flutter Web UI. Login, matching dashboard, mentor manager, dev dashboard, match history. |
| `flutter_mentor/` | Public Flutter Web form for mentor registration. Submits to a Node.js Vercel function → Google Form. |
| `flutter_mentee/` | Public Flutter Web form for mentee registration. Same pattern as flutter_mentor. |
| `data/` | Source-of-truth `.txt` files for config lists (orgs, concentrations, programs). Seeded into Neon on first setup. |
| `documentation/` | This folder. Architecture, setup, and troubleshooting guides. |

## Data Flow

```
[flutter_mentor / flutter_mentee]
        │  Registration form submit
        ▼
[Vercel Node.js function] ──────► Google Forms
        │  Config lists (orgs, concentrations, programs)
        ▲
        │  GET /config/*
[Render FastAPI backend]
        │
        ├── Neon Postgres ──────► mentors, config_lists, match_results tables
        │
        └── nlp_project/ ───────► sentence-transformers matching engine
                                   (called via subprocess, results stored in Neon)

[wrapper/flutter_wrapper admin UI]
        │  All admin operations
        ▼
[Render FastAPI backend]
```

## What Is Deployed Where

| Service | Host | Root Directory |
|---|---|---|
| FastAPI backend | **Render** (Docker) | `wrapper/backend/` |
| Admin Flutter UI | **Vercel** | `wrapper/flutter_wrapper/` |
| Mentor registration | **Vercel** | `flutter_mentor/` |
| Mentee registration | **Vercel** | `flutter_mentee/` |
| Database | **Neon** | — |

## Why Render for the Backend (Not Vercel)

The NLP matching engine (`nlp_project/`) uses `sentence-transformers` which loads the `all-mpnet-base-v2` model (~420 MB) at runtime. Vercel serverless functions have a **60-second maximum duration** on the Pro plan (10 seconds on Hobby). The model download and first inference easily exceed 60 seconds on a cold container.

Render web services run as persistent Docker containers with no request timeout cap. The model is pre-downloaded during the Docker build (`RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-mpnet-base-v2')"`) so it is cached in the image layer — cold starts are fast.

All other backend routes (mentor CRUD, config management, auth) are lightweight and would work fine on Vercel, but consolidating everything on Render simplifies deployment and avoids split-brain CORS configuration.

## Config Lists: From .txt Files to Neon

The five config lists (`ncsu_orgs`, `concentrations`, `grad_programs`, `abm_programs`, `phd_programs`) were originally flat `.txt` files in `data/` and bundled as Flutter assets. The new architecture:

1. `data/*.txt` files remain as local source-of-truth and asset fallback.
2. On first Neon setup, run `seed_config_lists.py` to load them into the `config_lists` table.
3. Backend reads from `config_lists` table when `WRAPPER_MENTOR_STORAGE_MODE=postgres`.
4. Admin UI edits via `/save_orgs`, `/save_concentrations`, `/save_majors` write to both the file and Neon.
5. Public endpoints `GET /config/*` serve the lists to flutter_mentor and flutter_mentee without requiring auth.
6. flutter_mentor and flutter_mentee try the backend first, fall back to bundled assets if unreachable.

## NLP Project Integration

`wrapper/backend/` calls `nlp_project/` via **subprocess** (not Python import). At build time, `prepare_vercel_bundle.py` copies `nlp_project/` into `wrapper/backend/nlp_project/`. The Docker image is built from `wrapper/backend/`, so `nlp_project/` is at `/app/nlp_project/` in the container. The env var `WRAPPER_NLP_PROJECT_DIR=/app/nlp_project` tells the backend where to find it.

The subprocess approach keeps the matching engine isolated — if it crashes or times out, only the `/run_match` request fails; the rest of the API stays up.

## Authentication

The admin UI uses bearer token auth. Two roles:
- **user** — can run matches and export results
- **dev** — can also edit config lists, manage mentors, view match history

Credentials are PBKDF2 hashes set in Render environment variables. The `WRAPPER_TOKEN_SECRET` ensures tokens survive container restarts.

The public registration apps (`flutter_mentor`, `flutter_mentee`) and the public `/config/*` endpoints require no authentication.
