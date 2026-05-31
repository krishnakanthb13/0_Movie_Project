# 🧠 Design Philosophy

This document outlines the rationale, principles, and target audience for the **Movie Library Manager**.

## Problem Statement

Maintaining a large local movie library is traditionally difficult due to:
1. **Messy Filenames**: Cryptic file names make browsing difficult.
2. **Missing Metadata**: Lack of visuals (posters) and context (plots, ratings).
3. **Manual Organization**: Sorting thousands of files is time-consuming.
4. **Data Fragmentation**: Databases often get out of sync with actual files.

## Project Rationale

This project creates an **AI-powered Private Streaming Service** experience for local media. Unlike traditional media managers, it uses advanced AI models with web search capabilities to identify movies accurately without requiring perfectly named folders.

### Why This Solution?
- **AI-First Identification**: Uses AI to identify movies from even the most obscure filenames (Gemini with Google Search, or Groq's fast open models).
- **Provider-Agnostic**: A pluggable AI layer (`ai_provider.py`) dispatches to either provider behind one shared interface, so swapping or adding backends never touches the pipeline.
- **Privacy & Control**: Works locally, doesn't rename your files, and stores data in open formats (CSV/SQLite).
- **Zero Configuration**: A single-file launcher handles setup and execution.

## Design Principles

1. **🛡️ Safety First (Untouchable Files)**
   - The system NEVER moves, renames, or modifies your original movie files. It only creates a separate metadata index.
   - The local server is defensively hardened: requests are confined to the project's web/movie directories (no path traversal), responses carry CSP and security headers, and concurrent writes are serialized through a lock to protect the CSV/DB.

2. **⚡ Performance & Efficiency**
   - The state-based enrichment pipeline (`is_active` 0–4 state machine) is the pipeline's backbone, allowing interrupted runs to be resumed and failures to be retried.
   - AI calls use request timeouts and 429 backoff so a stalled or rate-limited provider can't hang or derail a run.
   - The web viewer uses lazy loading and client-side filtering for a smooth experience even with 1000+ movies.

3. **📂 Transparency & Portability**
   - All data is stored in `data/movies.csv` and `data/movies.db`.
   - The CSV is the source of truth, making it human-readable and easy to back up or move.

4. **✨ Aesthetic Excellence**
   - The interface is designed to FEEL premium. Glassmorphism, smooth animations, and a carefully chosen dark theme ensure a "wow" factor.

5. **🚀 Simplicity & Speed**
   - One-click VLC playback.
   - Fast recursive scanning.
   - Minimal dependencies.

## Target Users

- **Movie Enthusiasts**: Users with massive local collections who want a Netflix-like browsing experience.
- **Archivists**: People who want a structured, portable record of their media library.
- **Efficiency Seekers**: Anyone tired of manual renaming and scouting for movie details.

## Workflow Integration

The tool fits into a simple 3-step loop:
1. **Scan**: Index new files added to any drive.
2. **Enrich**: Run the AI pipeline to fetch metadata.
3. **View**: Enjoy browsing and playing movies through the web dashboard.

## Future Vision

- Mobile-responsive design for local network browsing.
- User watch history and customizable ratings.
- AI-powered content recommendations based on library themes.
