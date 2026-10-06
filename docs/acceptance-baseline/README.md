# Acceptance baseline — billing-investigation-specialist

- **Setup:** services started locally from the repo root, each in its own terminal:
  - `python src\mock_ledger.py` (port 8000)
  - `python src\a2a_server.py` (port 8001)

## How to compare

| Category | What |
|---|---|
| Must match | `status` values, final decision, `reason`, set of fields |
| May differ | `task_id` values |
| Must change in Phase 1 | Agent Card `url` (must reflect the environment it runs in) |

## Tests

### Test 1 — Agent Card
`GET /.well-known/agent.json` → `01_card.json`

Result: one skill, `investigate_billing_dispute`. `url` is `http://localhost:8001` (hardcoded).

### Test 2 — Straight path (A1123)
`POST /tasks` with `{"order_id": "A1123"}` → `02_a1123_post.json`
`GET /tasks/<task_id>` → `03_a1123_final.json`

Result: `status: resolve`, reason "clean history, no conflict".
The POST already returns the final result: the graph runs inside the request.

### Test 3 — Human-review path (B2001)
1. `POST /tasks` with `{"order_id": "B2001"}` → `04_b2001_post.json` — `status: ""`
2. `GET /tasks/<task_id>` → `05_b2001_waiting.json` — `status: "input-required"`
3. `POST /tasks/<task_id>/input` with `{"decision": "escalate"}` → `06_b2001_input.json`
4. `GET /tasks/<task_id>` → `07_b2001_final.json` — `status: escalate`

### Test 4 — Ledger unavailable (B2001, ledger stopped)
`POST /tasks` with `{"order_id": "B2001"}` → `08_ledger_down.json`

Result: `fetch_error: connection_failed`, `status: input-required`.
Missing ledger data leads to human review, not an automatic decision. Fails fast (2 s timeout).

## Rerunning a test (PowerShell)

```powershell
$r = Invoke-RestMethod -Uri "http://localhost:8001/tasks" -Method Post -ContentType "application/json" -Body '{"order_id": "A1123"}'
$r | ConvertTo-Json -Depth 10
Invoke-RestMethod -Uri "http://localhost:8001/tasks/$($r.task_id)" | ConvertTo-Json -Depth 10
```

## Observations (known limitations, not fixed in Project 4)

- **`status` is overloaded:** it holds both lifecycle states (`input-required`) and business decisions (`resolve`, `escalate`). Clients must know which values mean "done."
- **Agent Card is minimal:** name, description, skills, url. Not a full A2A-spec card.
- **Every POST creates a new task:** the same order submitted twice is investigated twice.
- **Paused tasks live in `checkpoints.db`** (relative path, repo root). Losing that file loses every `input-required` task.