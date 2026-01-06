# 🧠 Context: Why & What

## The Problem

Maintaining a large local movie library is difficult:

1. **Messy Filenames**: Files like `The.Matrix.1999.1080p.BluRay.x264-YIFY.mkv` are hard to browse
2. **Missing Metadata**: No posters, no plot summaries, no ratings visible
3. **Manual Organization**: Sorting and categorizing thousands of files is daunting
4. **Ghost Records**: Deleted files leave orphan entries in any indexing database
5. **Discovery Fatigue**: "What should I watch?" becomes overwhelming with large collections

---

## The Solution

This project creates an **AI-powered Private Streaming Service** for your local movies:

### 🔍 Discovery Phase
The system indexes your filesystem recursively, identifying every video file instantly. It parses messy filenames like `Parasite.2019.KOREAN.1080p.BluRay.mkv` and extracts `"Parasite"` and `"2019"` as starting points.

### 🧠 Intelligence Phase
A **2-Step AI Pipeline** runs to identify each movie:

| Step | Model | Function |
|------|-------|----------|
| **Step 1** | Gemini 2.5 Flash + Google Search Grounding | Searches the web for the exact IMDb match |
| **Step 2** | Gemma 3 27B | Extracts structured JSON from the search transcript |

This approach achieves **high accuracy** even for obscure titles because it uses real-time web search rather than static training data.

### ✅ Verification Phase
AI-suggested data is cross-referenced with **OMDb** (The Open Movie Database) to fetch:
- Official movie poster
- Plot summary
- Genre, Director, Actors
- Runtime, Language, Country
- IMDb Rating
- Box Office earnings
- Awards

### 🔧 Manual Override
For particularly tricky titles (abbreviated names, foreign films, etc.), the **Manual Search 🔍** feature in the web UI allows you to:
- Enter an IMDb ID directly
- Search by title and year
- Instantly update the database

### 🔄 Synchronization
The **Cleanup** feature ensures your digital library stays synchronized with your physical drive:
- Detects files that have been deleted
- Removes orphan database entries
- Keeps everything perfectly in sync

### 🌐 Access
A **localized web server** transforms your drive into a premium, private streaming service:
- Beautiful dark-mode interface
- Instant search and filtering
- One-click VLC playback
- Works entirely offline (after initial enrichment)

---

## Design Philosophy

### 1. 🛡️ Safety First
**We never move or rename your files.** The system only creates an index. Your original file structure remains completely untouched.

### 2. ⚡ Efficiency
The `is_active` flag (0, 1, 2, 3, 4) allows precise control:

| Value | State | Meaning |
|-------|-------|---------|
| 0 | Ignored | Skip this movie entirely |
| 1 | Pending AI | Needs AI enrichment |
| 2 | Pending OMDb | AI done, awaiting OMDb |
| 3 | Complete | Fully enriched and ready |
| 4 | Failed | OMDb lookup failed, needs manual fix |

### 3. 📂 Transparency
Everything is stored in:
- `data/movies.csv` - Human-readable, editable, portable
- `data/movies.db` - SQLite for fast queries

**You own your data.** Export it, back it up, move it anywhere.

### 4. 🚀 Performance
The web viewer is designed for **collections of thousands**:
- **Lazy Loading**: Posters only load on demand
- **Auto-Images Toggle**: Disable for ultra-fast browsing
- **View Modes**: Grid, List, or Wall for different needs
- **Client-Side Filtering**: No server round-trips

### 5. ✨ Aesthetics
The viewer uses a **high-end dark theme** with:
- Glassmorphism effects
- Subtle hover animations
- Purple accent color scheme
- Modern Inter font
- Professional layout

**The goal is for users to be WOWed at first launch.**

---

## Use Cases

### The Movie Enthusiast
You have 2,000+ movies on your NAS. This tool lets you:
- Browse with full metadata like Netflix
- Filter by genre, decade, or language
- Remember what you haven't watched yet

### The Archivist
You want a clean database of your collection. This tool:
- Exports to CSV for external tools
- Maintains IMDb IDs for cross-referencing
- Tracks enrichment state for progress

### The Lazy Movie Night
"What should I watch?" becomes:
- Filter to a genre you're in the mood for
- Sort by IMDb rating
- Click play and enjoy

---

## Why These Technologies?

| Technology | Why |
|------------|-----|
| **Python** | Universal, readable, extensive ecosystem |
| **Gemini 2.5 Flash** | Native audio model with real-time web search grounding |
| **Gemma 3 27B** | Fast, accurate structured output generation |
| **OMDb** | Free, reliable movie metadata API |
| **SQLite** | Zero-config, single-file database |
| **Vanilla JS/CSS** | No build step, maximum portability |
| **VLC** | Plays everything, free, cross-platform |

---

## Future Possibilities

- 📱 Mobile-responsive design
- 🎭 User ratings and watch history
- 📊 Collection analytics dashboard
- 🔗 Integration with Plex/Jellyfin
- 🤖 AI-powered recommendations
