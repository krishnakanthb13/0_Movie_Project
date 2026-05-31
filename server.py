"""
Movie Library Project - Web Server Module
==========================================

Lightweight HTTP server to serve the web viewer and handle API requests.

This module implements a simple HTTP server that:
- Serves static files (HTML, CSS, JS, images) from the web directory
- Provides RESTful API endpoints for movie data
- Handles VLC playback requests
- Supports manual enrichment via web interface

Endpoints:
    GET  /                  -> Serves index.html
    GET  /api/movies        -> Returns all movies as JSON
    POST /play              -> Launches movie in VLC (body: {uuid})
    POST /api/open-folder   -> Opens containing folder (body: {uuid})
    POST /api/manual-enrich -> Manually enrich a movie via OMDb
    POST /api/update-metadata -> Update user ratings/tags

Architecture:
    Uses Python's built-in http.server module for simplicity.
    No external web framework dependencies required.

Usage:
    from server import run_server
    run_server()  # Starts server at http://localhost:8010

    # Or via CLI:
    python main.py --server

Dependencies:
    - storage.py: Database operations
    - omdb_client.py: Manual enrichment lookups
    - config.py: SERVER_PORT, SERVER_HOST, WEB_DIR, VLC_PATH
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
from storage import get_all_movies_sqlite, get_movie_by_uuid, update_sqlite_record, sync_sqlite_to_csv
from omdb_client import fetch_movie_data

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# REQUEST HANDLER
# =============================================================================

class MovieRequestHandler(http.server.SimpleHTTPRequestHandler):
    """
    Custom HTTP request handler for movie library API.
    
    Extends SimpleHTTPRequestHandler to add:
    - Custom API endpoints
    - JSON response handling
    - VLC integration
    - File explorer integration
    
    Request Flow:
        1. Parse URL and query parameters
        2. Route to appropriate handler method
        3. Execute handler logic (DB query, external command, etc.)
        4. Return appropriate response (JSON, HTML, file, error)
    """
    
    # -------------------------------------------------------------------------
    # GET REQUEST HANDLER
    # -------------------------------------------------------------------------
    
    def do_GET(self):
        """
        Handle GET requests.
        
        Routes requests to appropriate handler based on path:
        - /api/movies -> Movie list as JSON
        - /play -> Launch VLC
        - /api/open-folder -> Open file explorer
        - / or /index.html -> Main viewer page
        - Other paths -> Serve static files from WEB_DIR
        
        Args:
            None (uses self.path from request)
        
        Returns:
            None (sends response via self.send_* methods)
        """
        # Parse URL into components
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)
        
        # -----------------------------------------------------------------
        # API ENDPOINT: Get all movies as JSON
        # Returns array of movie objects for the frontend
        # -----------------------------------------------------------------
        if path == "/api/movies":
            self.send_json(get_all_movies_sqlite())
            return

        # Note: /play and /api/open-folder have side effects (launching VLC,
        # opening Explorer) and are handled as POST in do_POST, not GET, so
        # they can't be triggered cross-site by a stray <img>/link (CSRF).

        # -----------------------------------------------------------------
        # STATIC FILE SERVING
        # Maps URL paths to files in WEB_DIR.
        #
        # Security: the requested path is URL-decoded, joined to WEB_DIR,
        # and resolved to an absolute path. We then verify the result is
        # still inside WEB_DIR before serving. This prevents path traversal
        # attacks (e.g. "/../.env", "/../config.py") from leaking files
        # outside the web root such as API keys or the database.
        # -----------------------------------------------------------------
        if path == "/" or path == "/index.html":
            file_path = (WEB_DIR / "index.html").resolve()
        else:
            # URL-decode (e.g. %2e%2e -> ..) and strip leading slashes
            clean_path = urllib.parse.unquote(path).lstrip("/")
            file_path = (WEB_DIR / clean_path).resolve()

        # Confine to WEB_DIR: the resolved path must be the web root itself
        # or live underneath it. Reject anything that escapes.
        web_root = WEB_DIR.resolve()
        is_within_root = file_path == web_root or web_root in file_path.parents

        # Serve file if it is safely within WEB_DIR and exists
        if is_within_root and file_path.is_file():
            self.send_file(file_path)
        else:
            self.send_error(404, "File not found")

    # -------------------------------------------------------------------------
    # POST REQUEST HANDLER
    # -------------------------------------------------------------------------
    
    def do_POST(self):
        """
        Handle POST requests.
        
        Routes requests based on path:
        - /api/manual-enrich -> Manual OMDb search and update
        - /api/update-metadata -> Update user ratings/tags
        - /play -> Launch movie in VLC
        - /api/open-folder -> Open containing folder in Explorer

        Request body should be JSON for all POST endpoints.
        
        Args:
            None (uses self.path and request body)
        
        Returns:
            None (sends JSON response)
        """
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        
        # Read and parse request body
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8')
        
        try:
            data = json.loads(post_data) if post_data else {}
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
            return
        
        # -----------------------------------------------------------------
        # API ENDPOINT: Manual enrichment via OMDb
        # Body: {uuid, imdb_id?, title?, year?}
        # -----------------------------------------------------------------
        if path == "/api/manual-enrich":
            self.manual_enrich(data)
            return

        # -----------------------------------------------------------------
        # API ENDPOINT: Update user metadata
        # Body: {uuid, user_rating?, user_tags?}
        # -----------------------------------------------------------------
        if path == "/api/update-metadata":
            self.update_metadata(data)
            return

        # -----------------------------------------------------------------
        # API ENDPOINT: Play movie in VLC
        # Body: {uuid}
        # -----------------------------------------------------------------
        if path == "/play":
            uuid_val = data.get("uuid")
            if uuid_val:
                self.play_movie(uuid_val)
            else:
                self.send_error(400, "Missing movie ID")
            return

        # -----------------------------------------------------------------
        # API ENDPOINT: Open folder containing movie
        # Body: {uuid}
        # -----------------------------------------------------------------
        if path == "/api/open-folder":
            uuid_val = data.get("uuid")
            if uuid_val:
                self.open_folder(uuid_val)
            else:
                self.send_error(400, "Missing movie ID")
            return

        self.send_error(404, "Endpoint not found")

    # -------------------------------------------------------------------------
    # MANUAL ENRICHMENT HANDLER
    # -------------------------------------------------------------------------
    
    def manual_enrich(self, data: Dict):
        """
        Manually enrich a movie with OMDb data.
        
        Allows users to search OMDb directly via the web interface.
        Useful for fixing incorrect AI identifications or adding
        data for movies that failed automatic enrichment.
        
        Args:
            data (Dict): Request body containing:
                - uuid (str): Movie UUID to update (required)
                - imdb_id (str): IMDb ID to search (preferred)
                - title (str): Movie title to search
                - year (str): Release year to refine search
        
        Response:
            JSON with status "success" or "error" and message.
            On success, includes fetched movie data.
        
        Side Effects:
            - Updates SQLite record with OMDb data
            - Syncs changes to CSV
            - Sets is_active to 2 (enriched)
        """
        try:
            # Extract parameters
            uuid_val = data.get("uuid")
            imdb_id = data.get("imdb_id", "").strip()
            title = data.get("title", "").strip()
            year = data.get("year", "").strip()
            
            # Validate required field
            if not uuid_val:
                self.send_json({"status": "error", "message": "Missing movie UUID"})
                return
            
            # Get current movie record
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
            
            # Check if search returned results
            if result.get("title") == "NA":
                self.send_json({
                    "status": "error", 
                    "message": "No results found. Try a different search."
                })
                return
            
            # Prepare database update with all OMDb fields
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
                "is_active": 3  # Mark as fully enriched (Success)
            }
            
            # Also update AI fields if we have IMDb ID
            # This helps with display and filtering
            if result.get("imdb_id", "NA") != "NA":
                updates["imdb_id"] = result["imdb_id"]
                # Preference: use OMDb official title if fetch was successful
                if result.get("title") != "NA":
                    updates["ai_title"] = result["title"]
                if result.get("year") != "NA":
                    updates["ai_year"] = result["year"]
            
            # Update database record
            update_sqlite_record(uuid_val, updates)

            # Sync to CSV atomically (locked read+rewrite) so a concurrent
            # request can't snapshot and clobber this update in the CSV.
            sync_sqlite_to_csv()
            
            logger.info(f"Manual enrichment successful: {result.get('title')} ({result.get('year')})")
            
            # Return success response
            self.send_json({
                "status": "success",
                "message": f"Updated: {result.get('title')} ({result.get('year')})",
                "data": result
            })
            
        except Exception as e:
            logger.error(f"Manual enrichment error: {e}")
            self.send_json({"status": "error", "message": str(e)})

    # -------------------------------------------------------------------------
    # METADATA UPDATE HANDLER
    # -------------------------------------------------------------------------
    
    def update_metadata(self, data: Dict):
        """
        Update user metadata (rating, tags).
        
        Allows users to add personal ratings and tags to movies
        via the web interface.
        
        Args:
            data (Dict): Request body containing:
                - uuid (str): Movie UUID to update (required)
                - user_rating (int/str): Personal rating (1-10)
                - user_tags (list/str): Tags (stored as comma-separated)
        
        Response:
            JSON with status "success" or "error".
        """
        try:
            uuid_val = data.get("uuid")
            if not uuid_val:
                self.send_json({"status": "error", "message": "Missing movie UUID"})
                return

            updates = {}
            
            # Handle user rating
            if "user_rating" in data:
                updates["user_rating"] = str(data["user_rating"])
            
            # Handle user tags
            if "user_tags" in data:
                tags = data["user_tags"]
                # Convert array to comma-separated string if needed
                if isinstance(tags, list):
                    updates["user_tags"] = ",".join(tags)
                else:
                    updates["user_tags"] = str(tags)

            # Validate that we have something to update
            if not updates:
                self.send_json({"status": "error", "message": "No updates provided"})
                return

            # Update database
            update_sqlite_record(uuid_val, updates)
            
            self.send_json({"status": "success", "message": "Metadata updated"})
            
        except Exception as e:
            logger.error(f"Metadata update error: {e}")
            self.send_json({"status": "error", "message": str(e)})

    # -------------------------------------------------------------------------
    # RESPONSE HELPERS
    # -------------------------------------------------------------------------

    # Content-Security-Policy for served pages. The UI uses large inline
    # <style>/<script> blocks and a few inline event handlers, so 'unsafe-inline'
    # is required for script/style. The real value here is the rest of the
    # policy: connect-src 'self' blocks an injected script from exfiltrating to
    # an external origin, object-src 'none' blocks plugins, base-uri/form-action
    # 'self' and frame-ancestors 'none' block base-tag hijacking and clickjacking.
    # img-src allows https posters (OMDb) and data: URIs.
    CSP = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src https://fonts.gstatic.com; "
        "img-src 'self' https: data:; "
        "connect-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'"
    )

    def send_security_headers(self):
        """
        Emit security headers shared by all responses.

        Must be called after send_response() and before end_headers().
        """
        self.send_header("Content-Security-Policy", self.CSP)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")

    def send_json(self, data: Any):
        """
        Send JSON response to client.
        
        Args:
            data (Any): Data to serialize as JSON.
                        Can be dict, list, or any JSON-serializable type.
        
        Response:
            - HTTP 200 status
            - Content-Type: application/json
            - CORS header for cross-origin requests
            - UTF-8 encoded JSON body
        """
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        # No "Access-Control-Allow-Origin: *": this is a local single-origin
        # app, and the wildcard let any website read the movie list and
        # responses cross-origin. Same-origin requests from the bundled UI
        # are unaffected.
        self.send_security_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def send_file(self, file_path: Path):
        """
        Serve a static file from disk.
        
        Args:
            file_path (Path): Absolute path to the file to serve.
        
        Content-Type Mapping:
            .html -> text/html
            .css  -> text/css
            .js   -> application/javascript
            .png  -> image/png
            .ico  -> image/x-icon
            other -> application/octet-stream
        """
        try:
            # Read file content
            with open(file_path, "rb") as f:
                content = f.read()
            
            self.send_response(200)
            
            # Determine content type based on extension
            if file_path.suffix == ".html":
                ctype = "text/html"
            elif file_path.suffix == ".css":
                ctype = "text/css"
            elif file_path.suffix == ".js":
                ctype = "application/javascript"
            elif file_path.suffix == ".png":
                ctype = "image/png"
            elif file_path.suffix == ".ico":
                ctype = "image/x-icon"
            else:
                ctype = "application/octet-stream"
            
            self.send_header("Content-type", ctype)
            self.send_security_headers()
            self.end_headers()
            self.wfile.write(content)
            
        except Exception as e:
            logger.error(f"Error serving file {file_path}: {e}")
            self.send_error(500, "Internal Server Error")

    # -------------------------------------------------------------------------
    # VLC INTEGRATION
    # -------------------------------------------------------------------------
    
    def play_movie(self, uuid_val: str):
        """
        Launch movie in VLC media player.
        
        Looks up the movie by UUID and opens it in VLC.
        
        Args:
            uuid_val (str): UUID of the movie to play.
        
        Response:
            JSON with status and message.
        
        Requirements:
            - VLC must be installed at VLC_PATH
            - Movie file must exist at stored full_path
        """
        try:
            # Get movie record
            movie = get_movie_by_uuid(uuid_val)
            if not movie:
                self.send_error(404, "Movie not found")
                return
            
            full_path = movie["full_path"]
            logger.info(f"Playing: {full_path}")
            
            # Launch VLC with movie path
            if Path(VLC_PATH).exists():
                # Popen runs VLC in background (non-blocking)
                subprocess.Popen([VLC_PATH, full_path])
                self.send_json({"status": "success", "message": f"Playing {movie['file_name']}"})
            else:
                logger.error(f"VLC not found at {VLC_PATH}")
                self.send_error(500, "VLC executable not found")
                
        except Exception as e:
            logger.error(f"Error launching VLC: {e}")
            self.send_error(500, str(e))

    # -------------------------------------------------------------------------
    # FILE EXPLORER INTEGRATION
    # -------------------------------------------------------------------------
    
    def open_folder(self, uuid_val: str):
        """
        Open movie's folder in Windows Explorer.
        
        Opens the containing folder and selects the movie file.
        Windows-specific implementation using explorer.exe.
        
        Args:
            uuid_val (str): UUID of the movie.
        
        Response:
            JSON with status and message.
        """
        try:
            # Get movie record
            movie = get_movie_by_uuid(uuid_val)
            if not movie:
                self.send_error(404, "Movie not found")
                return
            
            full_path = movie.get("full_path")
            if not full_path:
                self.send_error(404, "File path not found")
                return

            # Resolve to absolute path
            full_path_obj = Path(full_path).resolve()
            if not full_path_obj.exists():
                self.send_error(404, "File does not exist on disk")
                return
            
            # Windows-specific: select the file in Explorer. /select is a
            # quirky verb that requires the exact command line
            #   explorer /select,"<path>"
            # with /select, OUTSIDE the quotes and only the path quoted. A
            # subprocess argument list cannot produce that: Python quotes the
            # whole "/select,<path with spaces>" token, which Explorer fails
            # to parse and then falls back to opening the default (Documents)
            # folder. So build the command line as a string. This is safe:
            # shell=False (the string goes straight to CreateProcess, no shell
            # parsing), the path comes from our database (only the uuid is
            # request-supplied) and was just verified to exist, and Windows
            # paths cannot contain the '"' that would break the quoting.
            subprocess.Popen(f'explorer /select,"{full_path_obj}"')
            self.send_json({"status": "success", "message": f"Opened folder for {movie['file_name']}"})
                
        except Exception as e:
            logger.error(f"Error opening folder: {e}")
            self.send_error(500, str(e))


# =============================================================================
# SERVER STARTUP
# =============================================================================

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """
    Multi-threaded HTTP server to handle concurrent requests.
    Prevents long enrichment fetches from blocking the whole UI.
    """
    daemon_threads = True
    allow_reuse_address = True

def run_server():
    """
    Start the multi-threaded HTTP server.
    """
    # Ensure web directory exists
    WEB_DIR.mkdir(exist_ok=True)
    
    # Create and start server with ThreadingMixIn
    with ThreadedTCPServer((SERVER_HOST, SERVER_PORT), MovieRequestHandler) as httpd:
        logger.info(f"Serving movie library at http://{SERVER_HOST}:{SERVER_PORT}")
        logger.info("Press Ctrl+C to stop")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            logger.info("\nServer stopped.")


# =============================================================================
# STANDALONE EXECUTION
# =============================================================================

if __name__ == "__main__":
    run_server()
