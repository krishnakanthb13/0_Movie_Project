"""
Movie Library Project - Web Server
Lightweight HTTP server to serve the viewer and handle playback requests.
"""

import http.server
import socketserver
import json
import urllib.parse
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any

from config import SERVER_PORT, SERVER_HOST, WEB_DIR, VLC_PATH
from storage import get_all_movies_sqlite, get_movie_by_uuid, update_sqlite_record, update_csv
from omdb_client import fetch_movie_data

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MovieRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom request handler for movie library API."""
    
    def do_GET(self):
        """Handle GET requests."""
        # Parse URL
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)
        
        # API Endpoints
        if path == "/api/movies":
            self.send_json(get_all_movies_sqlite())
            return
            
        if path == "/play":
            uuid_val = query.get("id", [None])[0]
            if uuid_val:
                self.play_movie(uuid_val)
            else:
                self.send_error(400, "Missing movie ID")
            return

        if path == "/api/open-folder":
            uuid_val = query.get("id", [None])[0]
            if uuid_val:
                self.open_folder(uuid_val)
            else:
                self.send_error(400, "Missing movie ID")
            return
            
        if path == "/":
            self.path = "/index.html"
            
        # Serve static files from web directory
        # Map / to web/index.html
        if self.path == "/" or self.path == "/index.html":
            file_path = WEB_DIR / "index.html"
        else:
            # Remove leading / and check if file exists in WEB_DIR
            clean_path = self.path.lstrip("/")
            file_path = WEB_DIR / clean_path
            
        if file_path.exists() and file_path.is_file():
            self.send_file(file_path)
        else:
            self.send_error(404, "File not found")

    def do_POST(self):
        """Handle POST requests."""
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        
        # Read POST body
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8')
        
        try:
            data = json.loads(post_data) if post_data else {}
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
            return
        
        if path == "/api/manual-enrich":
            self.manual_enrich(data)
            return

        if path == "/api/update-metadata":
            self.update_metadata(data)
            return
        
        self.send_error(404, "Endpoint not found")

    def manual_enrich(self, data: Dict):
        """Manually enrich a movie with OMDb data."""
        try:
            uuid_val = data.get("uuid")
            imdb_id = data.get("imdb_id", "").strip()
            title = data.get("title", "").strip()
            year = data.get("year", "").strip()
            
            if not uuid_val:
                self.send_json({"status": "error", "message": "Missing movie UUID"})
                return
            
            # Get current movie
            movie = get_movie_by_uuid(uuid_val)
            if not movie:
                self.send_json({"status": "error", "message": "Movie not found"})
                return
            
            # Fetch from OMDb
            logger.info(f"Manual enrichment for {movie['file_name']}: imdb={imdb_id}, title={title}, year={year}")
            
            result = fetch_movie_data(
                imdb_id=imdb_id if imdb_id else None,
                title=title if title else None,
                year=year if year else None
            )
            
            if result.get("title") == "NA":
                self.send_json({
                    "status": "error", 
                    "message": "No results found. Try a different search."
                })
                return
            
            # Update database
            updates = {
                "title": result.get("title", "NA"),
                "year": result.get("year", "NA"),
                "genre": result.get("genre", "NA"),
                "director": result.get("director", "NA"),
                "actors": result.get("actors", "NA"),
                "plot": result.get("plot", "NA"),
                "runtime": result.get("runtime", "NA"),
                "language": result.get("language", "NA"),
                "country": result.get("country", "NA"),
                "awards": result.get("awards", "NA"),
                "poster": result.get("poster", "NA"),
                "imdb_rating": result.get("imdb_rating", "NA"),
                "box_office": result.get("box_office", "NA"),
                "is_active": 2  # Mark as enriched
            }
            
            # Also update AI fields if we have IMDb ID
            if result.get("imdb_id", "NA") != "NA":
                updates["imdb_id"] = result["imdb_id"]
                updates["ai_title"] = result.get("title", "NA")
                updates["ai_year"] = result.get("year", "NA")
            
            update_sqlite_record(uuid_val, updates)
            
            # Sync to CSV
            all_movies = get_all_movies_sqlite()
            update_csv(all_movies)
            
            logger.info(f"Manual enrichment successful: {result.get('title')} ({result.get('year')})")
            
            self.send_json({
                "status": "success",
                "message": f"Updated: {result.get('title')} ({result.get('year')})",
                "data": result
            })
            
        except Exception as e:
            logger.error(f"Manual enrichment error: {e}")
            self.send_json({"status": "error", "message": str(e)})

    def update_metadata(self, data: Dict):
        """Update user metadata (rating, tags)."""
        try:
            uuid_val = data.get("uuid")
            if not uuid_val:
                self.send_json({"status": "error", "message": "Missing movie UUID"})
                return

            updates = {}
            if "user_rating" in data:
                updates["user_rating"] = str(data["user_rating"])
            if "user_tags" in data:
                # Store as comma-separated string
                tags = data["user_tags"]
                if isinstance(tags, list):
                    updates["user_tags"] = ",".join(tags)
                else:
                    updates["user_tags"] = str(tags)

            if not updates:
                self.send_json({"status": "error", "message": "No updates provided"})
                return

            update_sqlite_record(uuid_val, updates)
            
            # Sync to CSV if needed (optional for metadata but good for backup)
            # all_movies = get_all_movies_sqlite()
            # update_csv(all_movies)

            self.send_json({"status": "success", "message": "Metadata updated"})
            
        except Exception as e:
            logger.error(f"Metadata update error: {e}")
            self.send_json({"status": "error", "message": str(e)})

    def send_json(self, data: Any):
        """Send JSON response."""
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def send_file(self, file_path: Path):
        """Serve a file from disk."""
        try:
            with open(file_path, "rb") as f:
                content = f.read()
            
            self.send_response(200)
            
            # Set content type
            if file_path.suffix == ".html":
                ctype = "text/html"
            elif file_path.suffix == ".css":
                ctype = "text/css"
            elif file_path.suffix == ".js":
                ctype = "application/javascript"
            else:
                ctype = "application/octet-stream"
                
            self.send_header("Content-type", ctype)
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            logger.error(f"Error serving file {file_path}: {e}")
            self.send_error(500, "Internal Server Error")

    def play_movie(self, uuid_val: str):
        """Open movie in VLC."""
        try:
            movie = get_movie_by_uuid(uuid_val)
            if not movie:
                self.send_error(404, "Movie not found")
                return
            
            full_path = movie["full_path"]
            logger.info(f"Playing: {full_path}")
            
            # Launch VLC
            if Path(VLC_PATH).exists():
                subprocess.Popen([VLC_PATH, full_path])
                self.send_json({"status": "success", "message": f"Playing {movie['file_name']}"})
            else:
                logger.error(f"VLC not found at {VLC_PATH}")
                self.send_error(500, "VLC executable not found")
                
        except Exception as e:
            logger.error(f"Error launching VLC: {e}")
            self.send_error(500, str(e))

    def open_folder(self, uuid_val: str):
        """Open movie folder in explorer."""
        try:
            movie = get_movie_by_uuid(uuid_val)
            if not movie:
                self.send_error(404, "Movie not found")
                return
            
            full_path = movie.get("full_path")
            if not full_path:
                self.send_error(404, "File path not found")
                return

            full_path_obj = Path(full_path).resolve()
            if not full_path_obj.exists():
                self.send_error(404, "File does not exist on disk")
                return
            
            # Windows specific: select file in explorer
            subprocess.Popen(f'explorer /select,"{full_path_obj}"')
            self.send_json({"status": "success", "message": f"Opened folder for {movie['file_name']}"})
                
        except Exception as e:
            logger.error(f"Error opening folder: {e}")
            self.send_error(500, str(e))


def run_server():
    """Start the HTTP server."""
    # Ensure web dir exists
    WEB_DIR.mkdir(exist_ok=True)
    
    with socketserver.TCPServer((SERVER_HOST, SERVER_PORT), MovieRequestHandler) as httpd:
        logger.info(f"Serving movie library at http://{SERVER_HOST}:{SERVER_PORT}")
        logger.info("Press Ctrl+C to stop")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            logger.info("\nServer stopped.")


if __name__ == "__main__":
    run_server()
