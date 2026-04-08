# NLP Mentor Matcher Wrapper: Full System Blueprint

## 1) Required Folder Layout

All wrapper integration work is isolated under one folder, while matching logic stays in `nlp_project`.

```text
NLP_Matching/
  nlp_project/
    main.py
    mentor_matching/
    ...
  wrapper/
    FULL_SYSTEM_BLUEPRINT.md
    backend/
      app/
        main.py
        models.py
      data/
        majors.txt
      requirements.txt
      README.md
    flutter_wrapper/
      lib/
        main.dart
        constants/
          ncsu_theme.dart
        models/
          match_models.dart
        services/
          api_client.dart
        screens/
          login_screen.dart
          matching_dashboard_screen.dart
          dev_dashboard_screen.dart
      pubspec.yaml
      README.md
```

The only source of matching truth remains `nlp_project/main.py`.

## 2) Runtime Architecture

- Flutter Web is the UI layer.
- FastAPI is the transport/orchestration layer.
- `nlp_project/main.py` is the matching engine.

Flow:

1. Flutter sends files + constraints to FastAPI `/run_match`.
2. FastAPI writes temp files and temp state JSON.
3. FastAPI runs `python nlp_project/main.py ... run`.
4. FastAPI reads generated `latest_matches.json` and returns it to Flutter.
5. Flutter renders cards and supports drag/drop/manual edits.
6. Flutter submits final board state to `/export_assignments` for XLSX output.

## 3) Visual System (same style family as existing apps)

Use the same NC State palette approach as `flutter_mentee` and `flutter_mentor`:

- Primary red: `#CC0000`
- Black: `#000000`
- White: `#FFFFFF`
- Secondary accents already present in existing code (Aqua/Blue/Indigo etc.)

Recommended usage in wrapper UI:

- Header / primary action: Wolfpack red
- Warning / break actions (`X`): Pyroman/reduced red shades
- Locked state: Bio indigo
- Unmatched pool panel: light neutral background with red top border

## 4) Authentication Gate (Flutter + FastAPI)

Credentials are validated on backend only.

- Flutter collects username/password and calls `POST /login`.
- FastAPI verifies PBKDF2 password hashes from backend environment variables.
- FastAPI returns bearer token + `is_dev`.
- Flutter stores token in `flutter_secure_storage`.
- Backend issues short-lived access tokens and supports rotation via `POST /token/refresh`.
- Backend enforces login rate limits (IP + username buckets).
- Role routing (`isDev`) is derived from backend response, not hardcoded client credentials.

## 5) Matching Dashboard: UX + State Model

### 5.1 Pre-run controls

- `Upload Mentor File` button (`file_picker`)
- `Upload Mentee File` button (`file_picker`)
- Exclusion builder:
  - Mentee dropdown
  - Mentor dropdown
  - `Add to Exclusion List` button
  - Shows chips/list of blocked pairs

### 5.2 Board model

Maintain a local board state object:

```dart
class MatchBoardState {
  Map<String, MentorCardState> mentorsById;
  Map<String, MenteeRecord> menteesById;
  Set<String> unmatchedMenteeIds;
  Set<PairKey> lockedPairs;
  Set<PairKey> rejectedPairs;
}
```

Each `MentorCardState` contains:

- mentor identity
- list of assigned mentee IDs (capacity-aware)
- UI flags (`isDropHover`, `isExpanded`)

### 5.3 Rendering cards

- Mentor cards are `DragTarget<MenteeRecord>`
- Mentee chips/cards are `Draggable<MenteeRecord>`

Event cycle:

1. User starts drag on mentee widget (`Draggable`).
2. Mentor card highlights in `onWillAcceptWithDetails`.
3. On `onAcceptWithDetails`, remove mentee from old location and insert into new mentor slot.
4. Update `rejectedPairs` if needed (if user had explicitly broken that pair).
5. Trigger `setState`/state notifier update.

## 6) Lock and Break Controls

Each mentee assignment row inside a mentor card has:

- `Lock` toggle button
- `X` break button

### 6.1 Lock behavior

When locked:

- Add pair to `lockedPairs` set.
- Show lock icon filled/high-contrast.
- During rerun, backend receives locked pair list.
- Matcher must preserve locked pairs.

### 6.2 Break (`X`) behavior

When user breaks pair:

- Remove mentee from mentor card.
- Add mentee to `unmatchedMenteeIds` pool.
- Add pair to `rejectedPairs` so rerun avoids re-forming that exact pair.

This is the direct implementation of “do not put these together.”

## 7) Unmatched Pool + Rerun

### 7.1 Unmatched pool

Right sidebar list of mentees not currently assigned.

Capabilities:

- Drag from unmatched pool into any mentor card.
- Show origin reason tags (`unassigned`, `broken`, `excluded`).

### 7.2 Rerun payload construction

On `Rerun` click, Flutter builds:

- `locked_pairs`
- `rejected_pairs`
- `excluded_mentee_ids`
- `excluded_mentor_ids`
- optional weight overrides

Then sends files + payload to `/run_match`.

## 8) Dev Dashboard (dev-role only)

Visible only when `isDev == true`.

### 8.1 Trigger buttons

- `Update NCSU Orgs`
  - POST `/update_orgs`
  - Rewrites `data/ncsu_orgs.txt`
- `Update Concentrations`
  - POST `/update_concentrations`
  - Rewrites `data/concentrations.txt`

UI behavior:

- Disable button while request in-flight.
- Show spinner + status result (`done` or error text).

### 8.2 `majors.txt` editor

- On screen load: call `GET /get_majors`.
- Populate multiline text field with server text.
- On save: `POST /save_majors` with full text.
- Display “saved” timestamp.

### 8.3 Manual file editors

- `NCSU Orgs` tab:
  - load with `GET /get_orgs`
  - save with `POST /save_orgs`
- `Concentrations` tab:
  - load with `GET /get_concentrations`
  - save with `POST /save_concentrations`
- `Majors` tab:
  - load with `GET /get_majors`
  - save with `POST /save_majors`

## 9) Backend API Contracts

### 9.0 Auth endpoints

- `POST /login`
  - Input: `username`, `password`
  - Output: `token`, `token_type`, `expires_in`, `is_dev`
  - Generic auth failure text to reduce account-enumeration risk
  - Rate-limited
- `GET /me`
  - Requires bearer token
  - Returns active user role/session metadata
- `POST /token/refresh`
  - Requires bearer token
  - Rotates access token and invalidates prior token
- `POST /logout`
  - Requires bearer token
  - Invalidates current user sessions

### 9.1 `/run_match` (multipart)

Parts:

- `mentee_file`: file
- `mentor_file`: file
- `payload_json`: serialized JSON

`payload_json` fields:

- `excluded_mentee_ids: string[]`
- `excluded_mentor_ids: string[]`
- `rejected_pairs: [{ mentee_id, mentor_id }]`
- `locked_pairs: [{ mentee_id, mentor_id }]`
- `global_weights: { [factor]: number }`
- `mentee_weight_overrides: { [mentee_id]: { [factor]: number } }`
- `top_n: number`

Response:

- `status`
- `result` (raw content from `latest_matches.json`)
- `stdout` (for debugging)

Auth:

- Requires `Authorization: Bearer <token>`

### 9.2 `/export_assignments`

Input:

- final rows from board state
- optional filename

Output:

- streamed `.xlsx` file download

### 9.3 Dev file APIs

- `POST /update_orgs`: execute pull script and refresh `data/ncsu_orgs.txt`
- `POST /update_concentrations`: execute pull script and refresh `data/concentrations.txt`
- `GET /get_orgs` + `POST /save_orgs`
- `GET /get_concentrations` + `POST /save_concentrations`
- `GET /get_majors` + `POST /save_majors`

Auth:

- All dev file APIs require dev-role bearer token.

## 10) File Type Handling

`/run_match` accepts:

- `.csv`
- `.xlsx`
- `.xls`

For Excel, backend converts to CSV before calling matcher.

## 11) Important Operational Notes

- Backend does not re-implement scoring logic.
- Backend only calls `nlp_project/main.py` with temporary inputs.
- If sentence-transformers dependencies are missing in runtime env, matcher may fall back to lexical mode; deploy environment should include `nlp_project` dependencies.
- For deployment, enable HTTPS enforcement (`WRAPPER_REQUIRE_HTTPS=true`), keep short token TTL, and rotate any credentials previously exposed in history.
- Auth audit events (login success/failure, rate limits, logout, denied dev access) should be monitored in server logs.

## 12) Flutter Interaction Details (implementation rules)

- Drag move should be optimistic and instant in UI.
- If rerun is requested, local board can be replaced by backend response.
- Manual board edits should remain local until:
  - rerun,
  - or export.
- Locked pairs should visually persist across reruns.

## 13) Suggested Build Sequence

1. Stand up FastAPI and verify `/health`.
2. Wire file uploads and `/run_match`.
3. Render initial board from result JSON.
4. Add drag/drop reassignment.
5. Add lock and break semantics.
6. Add unmatched pool.
7. Add rerun payload wiring.
8. Add dev dashboard endpoints.
9. Add export endpoint integration.

## 14) Acceptance Criteria

- Backend-authenticated login works via `/login`, and Flutter stores only bearer token.
- `/login` rate limits repeated failures and returns generic invalid-credential errors.
- Access tokens expire and can be rotated through `/token/refresh`.
- Upload mentor+mentee files and run matching from UI.
- Drag/drop reassignment works across mentor cards.
- `X` moves mentee to unmatched and blocks prior pair on rerun.
- Lock guarantees pair persistence on rerun.
- Dev dashboard updates orgs/concentrations and edits majors text.
- Export returns final board state as `.xlsx`.
