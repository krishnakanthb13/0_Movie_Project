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
3. [x] Enriches metadata using **Gemini Live (AI)** - *Updated: Using native-audio-preview-12-2025 with 2-step Gemma pipeline*
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
