Raw Prompt:

Movie Project (Status: Completed ✅)
- [x] Should read all the video file formats in a specific location - hardcoded and editable in the code
- [x] save all of them as index in a csv file, we are going to grow this with more columns
- [x] in csv, you can have a uuid, file name, file location on drive, complete location
- [x] the file name mostly contain the movie name and year - 19XX or 20XX
- [x] try to filter them into additional columns - extracted name and extracted year - keep default NA if not found
- [x] then using gemini live tool
	- [x] build a prompt which gives the exact movie name + year + imdb id
	- [x] make the promt as request, and loop it, with some gap after receiving all the details - include thinking and response
	- [x] upon passing the complete file name and extracted name and extracted year
	- [x] response should be very definitive
- [x] then using imdb id or ai obtained name - use omdb api key to get all the info that are available about that movie
- [x] if not available - default to NA
- [x] the backend can be sqlite db too, it is okay
- [x] till now it is reading and enrichment part
- [x] then there need to be a viewer, http-server, a web html interface, to read the csv or the sqlite db
- [x] where I should be able to see the complete list of movies
- [x] give me options to open in vlc - using the local file name and location


Detailed Instructions (Implemented ✅):

---

## 🔧 MASTER PROMPT — *Movie Library Indexing, Enrichment & Viewer System*

---

### ROLE (Fulfilled ✅)

You are a **Senior Python Systems Engineer + AI Integration Architect**.

### OBJECTIVE (Achieved ✅)

Design and implement a **Movie Library Project** that:

1. [x] Scans a local directory for movie files
2. [x] Indexes them into structured storage (CSV + optional SQLite)
3. [x] Enriches metadata using **AI (Gemini or Groq)** - *Updated: 2-step Gemini pipeline (native-audio search + gemini-2.5-flash formatter) or the Groq provider; see Implemented Enhancements below*
4. [x] Fetches authoritative data using **OMDb API (IMDb)**
5. [x] Exposes a **local web viewer** with playback options (VLC) - *Port: 8010*

---

### SYSTEM CONSTRAINTS (Met ✅)

* Language: **Python 3.10+**
* OS: **Windows**
* Modular and extensible
* Default missing data stored as `"NA"`
* Failures do not stop the pipeline

---

## 1️⃣ FILE DISCOVERY & INDEXING (COMPLETED ✅)

### Requirements

* [x] Scan hardcoded directory (`E:/`)
* [x] Detect video files (.mp4, .mkv, .avi, etc.)
* [x] Ignore non-video files

### Column Implementation:

| Column         | Status |
| -------------- | ------ |
| uuid           | ✅     |
| file_name      | ✅     |
| directory      | ✅     |
| full_path      | ✅     |
| extracted_name | ✅     |
| extracted_year | ✅     |

---

## 2️⃣ STORAGE LAYER (COMPLETED ✅)

### Mandatory

* [x] Write to CSV (`data/movies.csv`)
* [x] Append-safe and future-friendly

### Optional

* [x] SQLite database (`data/movies.db`) mirroring CSV

---

## 3️⃣ AI ENRICHMENT (GEMINI LIVE - COMPLETED ✅)

**Implemented via Advanced 2-Step Pipeline:**
1.  **Step 1: Searcher** - Uses `gemini-2.5-flash-native-audio-preview-12-2025` with Google Search grounding.
2.  **Step 2: Formatter** - Uses `gemma-3-27b-it` to extract structured JSON from the audio transcript.

### Prompt Requirements

* [x] Exact title, year, IMDb ID
* [x] definitive answer
* [x] Loop with delay (`AI_REQUEST_DELAY = 3.0`)

---

## 4️⃣ OMDb API ENRICHMENT (COMPLETED ✅)

* [x] Using IMDb ID or Title/Year fallback
* [x] Fetch all available fields (Genre, Actors, Plot, Poster, etc.)
* [x] Handle missing fields as "NA"

---

## 5️⃣ DATA MERGE (COMPLETED ✅)

* [x] Merged file index, AI results, and OMDb metadata
* [x] Persisted back to CSV and SQLite

---

## 6️⃣ WEB VIEWER (LOCAL HTTP SERVER - COMPLETED ✅)

### Backend

* [x] Lightweight Python server (`server.py` on Port 8010)

### Frontend (HTML)

* [x] Table/Grid view
* [x] Sortable and searchable
* [x] Premium Dark Mode UI

### Playback Integration

* [x] **“Play in VLC”** option per row
* [x] Integrated via local system call

---

## 7️⃣ CODE QUALITY & STRUCTURE (COMPLETED ✅)

### Required Modules Created:

* [x] `scanner.py`
* [x] `parser.py`
* [x] `storage.py`
* [x] `gemini_client.py`
* [x] `omdb_client.py`
* [x] `enricher.py`
* [x] `server.py`
* [x] `config.py`

---

## 8️⃣ OUTPUT EXPECTATION (DELIVERED ✅)

1. [x] High-level architecture overview (Summary turns)
2. [x] Step-by-step execution flow (`MovieLibrary.bat`)
3. [x] Database schema (`storage.py`)
4. [x] Example prompts (`gemini_client.py`)
5. [x] Key code snippets per module
6. [x] Clear next-step extension ideas

---

**Project Final State: PRODUCTION READY 🚀**

---

## 🆕 Implemented Enhancements (current)

> The sections above are the **original spec/history**. They are preserved as-is.
> The list below documents features that have since been **implemented on top of**
> that original scope, verified against the current code
> (`main.py`, `config.py`, `server.py`, `enricher.py`, `ai_provider.py`,
> `groq_client.py`, `gemini_client.py`, `storage.py`, `MovieLibrary.bat`).

### Multi-Provider AI (Gemini + Groq)

A pluggable AI layer (`ai_provider.py`) dispatches movie identification to the
selected backend behind one shared interface, so the enrichment pipeline never
needs to know which provider is active.

* **Default provider: Gemini** — 2-step pipeline (Live API search-grounding with
  `gemini-2.5-flash-native-audio-preview-12-2025`, then JSON formatting with the
  configured `AI_MODEL`, default `gemini-2.5-flash`).
* **Alternative provider: Groq** (`groq_client.py`) — fast open models via Groq's
  OpenAI-compatible REST API (default `llama-3.3-70b-versatile`). Identifies from
  model knowledge; OMDb remains the authoritative verifier. Groq **"compound"**
  models add built-in web-search grounding (JSON mode is auto-disabled for them
  and JSON is parsed defensively).
* **Selection** (in priority order):
  * `AI_PROVIDER` env var (`gemini` | `groq`, default `gemini`).
  * `--provider {gemini,groq}` CLI flag (per run).
  * `--model` CLI flag — Gemini shortcuts `2.5` / `3.5`, or any full model id
    (e.g. `llama-3.3-70b-versatile`, `groq/compound`).
  * Groq requires `GROQ_API_KEY` in `.env`.

### Resilience

* **Per-request timeout** — `config.AI_TIMEOUT_SECONDS = 120` applied to both
  providers (Gemini converts to ms; Groq passes to `requests`), so a stalled
  request can't hang the run.
* **Automatic 429 retry/backoff** — Groq client retries on HTTP 429 with
  exponential backoff, honoring the `Retry-After` header / body hint.
* **Configurable bulk chunk size** — bulk enrichment chunks by
  `config.BATCH_SIZE` (default 50).

### Enrichment State Machine + Retry-Failed Flow

`is_active` tracks each movie through the pipeline:

| Value | State |
|-------|-------|
| 0 | Ignored (not processed) |
| 1 | Pending AI |
| 2 | Pending OMDb |
| 3 | Success |
| 4 | Failed |

* **Retry-failed flow**: `--retry-failed` (and `MovieLibrary.bat` option `[F]`)
  resets state `4 → 2` and re-runs the OMDb pass.

### OMDb Verification

* Prefers the AI-supplied **IMDb ID** for an exact, unambiguous lookup.
* Falls back to a title/year search, then runs `verify_match` (normalized title
  containment + 1-year tolerance) and **rejects mismatches** (state 4) rather
  than attaching wrong metadata.

### Security / Robustness (web server)

* **Path-traversal-safe** static file serving (resolved path confined to `WEB_DIR`).
* **CSP + security headers** on every response (incl. error pages):
  `Content-Security-Policy`, `X-Content-Type-Options`, `Referrer-Policy`,
  `X-Frame-Options`. No wildcard CORS.
* **POST-only side-effecting endpoints**: `/play` and `/api/open-folder` are
  POST (JSON body `{uuid}`), guarding against CSRF via stray links/images.
* **Multi-threaded server** (`ThreadingMixIn`) with **write serialization** —
  all mutating storage operations are guarded by a re-entrant lock, and
  CSV sync holds the lock across read+rewrite.
* **Request body cap** (1 MiB) + **socket timeout** (30s) to resist memory/slow
  request DoS.

### Environment Keys (`.env`)

| Key | Required? |
|-----|-----------|
| `GEMINI_API_KEY` | Required for the default Gemini provider |
| `OMDB_API_KEY` | Required for all metadata fetching |
| `GROQ_API_KEY` | Optional — only when using the Groq provider |
| `AI_PROVIDER` | Optional — `gemini` (default) or `groq` |

### Updated Module List

In addition to the original modules, the codebase now includes
`ai_provider.py` (provider dispatcher) and `groq_client.py` (Groq backend).

> **Note (original-spec correction):** Section 3 above states Step 2 formatting
> uses `gemma-3-27b-it`. The current code uses the configured `AI_MODEL`
> (default `gemini-2.5-flash`) as the formatter model.
