# 🧠 Context: Why & What

## The Problem
Maintaining a large local movie library is difficult. Filenames are often messy (e.g., `The.Matrix.1999.1080p.BluRay.x264.mkv`), missing metadata like posters or plot summaries, and organizing them manually is a daunting task. Deleted files often leave "ghost" records in databases, making the collection feel outdated.

## The Solution
This project automates the entire lifecycle of a local movie library:

1.  **Discernment**: The system indexes the filesystem recursively, identifying new additions instantly.
2.  **Intelligence**: It uses **Gemini 2.5 Flash** with **Google Search Grounding** to "search the web" for the correct IMDb ID for any filename.
3.  **Accuracy**: Chaining results into **Gemma 3 27B** ensures structured, reliable data extraction.
4.  **Verification & Manual Overrides**: Cross-references AI data with **OMDb** authoritative metadata. If a title is particularly difficult, the **Manual Search 🔍** feature allows for human intervention.
5.  **Synchronization**: The **Cleanup** feature ensures that if you delete a file from your hard drive, it is removed from your digital library, keeping the two perfectly in sync.
6.  **Access**: A localized web server treats your local drive like a private, premium streaming service, launching movies directly in **VLC**.

## Design Philosophy
*   **Safety First**: We never move or rename your files. We only index them.
*   **Efficiency**: The `is_active` flag (0, 1, or 2) allows you to control exactly which movies get processed.
*   **Transparency**: Everything is stored in a simple CSV file alongside the SQLite database. You own your data.
*   **Performance**: The viewer uses lazy loading and poster toggles to handle libraries of thousands of movies without slowing down or hanging.
*   **Aesthetics**: The viewer uses a high-end dark theme with glassmorphism, designed to WOW the user on first launch.
