"""
Test: update_metadata() now syncs user_rating/user_tags to BOTH SQLite and
data/movies.csv (the CSV "source of truth"), mirroring manual_enrich().

No real data or external APIs are touched:
  - storage.CSV_FILE / storage.SQLITE_FILE are monkeypatched to a temp dir.
  - The real MovieRequestHandler.update_metadata code path is exercised
    (instance built via __new__ to skip the socket-bound __init__; send_json
    is stubbed to capture the JSON response).
"""

import csv
import sys
import tempfile
import sqlite3
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

import storage  # noqa: E402


def _read_csv_row(csv_file, uuid_val):
    with open(csv_file, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["uuid"] == uuid_val:
                return row
    return None


def _sqlite_row(sqlite_file, uuid_val):
    conn = sqlite3.connect(sqlite_file)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute("SELECT * FROM movies WHERE uuid = ?", (uuid_val,))
        r = cur.fetchone()
        return dict(r) if r else None
    finally:
        conn.close()


def main():
    tmpdir = Path(tempfile.mkdtemp(prefix="movie_test_"))
    csv_file = tmpdir / "movies.csv"
    sqlite_file = tmpdir / "movies.db"

    # --- Redirect storage to the temp DB/CSV. The storage functions read these
    #     module globals at call time, so patching them reroutes everything,
    #     including the names already imported into the server module.
    storage.CSV_FILE = csv_file
    storage.SQLITE_FILE = sqlite_file

    # Now import server (it does `from storage import ... sync_sqlite_to_csv`).
    import server  # noqa: E402

    # --- Initialize temp storage and seed exactly one movie.
    storage.init_csv()
    storage.init_sqlite()

    uuid_val = "11111111-1111-1111-1111-111111111111"
    storage.insert_to_sqlite([{
        "uuid": uuid_val,
        "file_name": "Inception.2010.mkv",
        "directory": "/movies",
        "full_path": "/movies/Inception.2010.mkv",
        "is_active": 3,
        "title": "Inception",
        "year": "2010",
        "user_rating": "",
        "user_tags": "",
    }])
    # Mirror to CSV so we start with a CSV row that has empty rating/tags.
    storage.sync_sqlite_to_csv()

    # Sanity: seeded CSV row exists with empty rating/tags.
    seed_csv = _read_csv_row(csv_file, uuid_val)
    assert seed_csv is not None, "seed CSV row missing"
    assert seed_csv["user_rating"] == "" and seed_csv["user_tags"] == "", \
        f"expected empty seed rating/tags, got {seed_csv['user_rating']!r}/{seed_csv['user_tags']!r}"
    print("[seed] CSV row present, rating/tags empty -> OK")

    # --- Build a real handler instance without running the socket __init__.
    handler = server.MovieRequestHandler.__new__(server.MovieRequestHandler)
    captured = {}
    handler.send_json = lambda data: captured.update({"response": data})

    # =====================================================================
    # CASE 1: valid update -> must reach BOTH SQLite AND CSV
    # =====================================================================
    handler.update_metadata({
        "uuid": uuid_val,
        "user_rating": 9,
        "user_tags": ["favorite", "rewatch"],
    })

    resp = captured["response"]
    assert resp.get("status") == "success", f"expected success, got {resp}"

    db_row = _sqlite_row(sqlite_file, uuid_val)
    assert db_row["user_rating"] == "9", f"SQLite rating wrong: {db_row['user_rating']!r}"
    assert db_row["user_tags"] == "favorite,rewatch", f"SQLite tags wrong: {db_row['user_tags']!r}"

    csv_row = _read_csv_row(csv_file, uuid_val)
    assert csv_row is not None, "CSV row vanished"
    assert csv_row["user_rating"] == "9", \
        f"CSV NOT synced - rating={csv_row['user_rating']!r} (THIS is the bug being fixed)"
    assert csv_row["user_tags"] == "favorite,rewatch", \
        f"CSV NOT synced - tags={csv_row['user_tags']!r} (THIS is the bug being fixed)"
    print(f"[case1] success response: {resp}")
    print(f"[case1] SQLite  -> rating={db_row['user_rating']!r} tags={db_row['user_tags']!r}")
    print(f"[case1] CSV     -> rating={csv_row['user_rating']!r} tags={csv_row['user_tags']!r}")
    print("[case1] BOTH SQLite and CSV reflect the update -> OK")

    # =====================================================================
    # CASE 2: unknown uuid -> "Movie not found", and NOTHING is written
    # =====================================================================
    csv_before = csv_file.read_text(encoding="utf-8")
    captured.clear()
    handler.update_metadata({
        "uuid": "does-not-exist",
        "user_rating": 1,
        "user_tags": ["nope"],
    })
    resp2 = captured["response"]
    assert resp2.get("status") == "error", f"expected error, got {resp2}"
    assert resp2.get("message") == "Movie not found", f"expected 'Movie not found', got {resp2}"

    assert _sqlite_row(sqlite_file, "does-not-exist") is None, "phantom SQLite row written"
    assert csv_file.read_text(encoding="utf-8") == csv_before, "CSV was modified for unknown uuid"
    # The real row must be untouched (still 9 / favorite,rewatch).
    csv_row_after = _read_csv_row(csv_file, uuid_val)
    assert csv_row_after["user_rating"] == "9" and csv_row_after["user_tags"] == "favorite,rewatch", \
        "existing row was disturbed by the unknown-uuid call"
    print(f"[case2] unknown-uuid response: {resp2}")
    print("[case2] 'Movie not found' returned and NOTHING written -> OK")

    print("\nALL ASSERTIONS PASSED")


if __name__ == "__main__":
    main()
