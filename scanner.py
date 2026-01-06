"""
Movie Library Project - File Scanner Module
============================================

Recursively scans directories to discover video files for indexing.

This module provides functions to:
- Check if a file is a recognized video format
- Recursively scan directories for all video files
- Handle permission errors and system files gracefully
- Yield file information as structured dictionaries

The scanner uses a generator pattern for memory efficiency when
processing large directories with thousands of files.

Usage:
    from scanner import scan_directory, get_all_videos
    
    # Generator approach (memory efficient)
    for video in scan_directory(Path("E:/")):
        print(video["file_name"])
    
    # List approach (loads all into memory)
    all_videos = get_all_videos()

Dependencies:
    - config.py: MOVIE_DIRECTORY, VIDEO_EXTENSIONS
"""

import logging
from pathlib import Path
from typing import Generator, List, Dict
from config import MOVIE_DIRECTORY, VIDEO_EXTENSIONS

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================
# Set up logging for scan operations.
# Logs are written to both console and movie_library.log file.

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# =============================================================================
# FILE TYPE DETECTION
# =============================================================================

def is_video_file(file_path: Path) -> bool:
    """
    Check if a file is a video based on its extension.
    
    Compares the file's extension (case-insensitive) against the set of
    recognized video extensions defined in config.VIDEO_EXTENSIONS.
    
    Args:
        file_path (Path): Path object pointing to the file to check.
                          Can be absolute or relative path.
    
    Returns:
        bool: True if the file extension matches a known video format,
              False otherwise.
    
    Examples:
        >>> is_video_file(Path("movie.mp4"))
        True
        >>> is_video_file(Path("document.pdf"))
        False
        >>> is_video_file(Path("VIDEO.MKV"))  # Case insensitive
        True
    
    Note:
        This function only checks the extension, not the actual file content.
        A file with a video extension but non-video content will return True.
    """
    return file_path.suffix.lower() in VIDEO_EXTENSIONS


# =============================================================================
# DIRECTORY SCANNING
# =============================================================================

def scan_directory(root_dir: Path = MOVIE_DIRECTORY) -> Generator[Dict, None, None]:
    """
    Recursively scan a directory for video files.
    
    Traverses all subdirectories starting from root_dir and yields
    information about each discovered video file. Uses a generator
    pattern to allow processing files as they're found without
    loading the entire list into memory.
    
    Args:
        root_dir (Path): Root directory to start scanning from.
                         Defaults to MOVIE_DIRECTORY from config.
                         Will be converted to Path if passed as string.
    
    Yields:
        Dict: Dictionary containing file information with keys:
            - "file_name" (str): Just the filename with extension
                                 Example: "The.Matrix.1999.mkv"
            - "directory" (str): Full path to the containing directory
                                 Example: "E:/Movies/Action"
            - "full_path" (str): Complete absolute path to the file
                                 Example: "E:/Movies/Action/The.Matrix.1999.mkv"
    
    Raises:
        No exceptions are raised - errors are logged and skipped.
    
    Error Handling:
        - PermissionError: Logged as warning, file/directory skipped
        - Other exceptions: Logged as warning, continues scanning
        - Non-existent root_dir: Logged as error, returns immediately
    
    Filters Applied:
        - Skips directories (only yields files)
        - Skips non-video files (based on extension)
        - Skips hidden files (names starting with '.')
        - Skips system files (names starting with '$')
    
    Examples:
        >>> for video in scan_directory(Path("E:/Movies")):
        ...     print(f"Found: {video['file_name']}")
        Found: The.Matrix.1999.mkv
        Found: Inception.2010.mp4
        
        >>> # With limit
        >>> count = 0
        >>> for video in scan_directory():
        ...     count += 1
        ...     if count >= 10:
        ...         break
    
    Performance Notes:
        - Uses Path.rglob("*") for recursive traversal
        - Memory efficient due to generator pattern
        - I/O bound by disk speed
    """
    # Convert to Path object if string is passed
    root_path = Path(root_dir)
    
    # Validate that directory exists before scanning
    if not root_path.exists():
        logger.error(f"Directory does not exist: {root_path}")
        return
    
    logger.info(f"Scanning directory: {root_path}")
    video_count = 0
    
    try:
        # rglob("*") recursively matches all files and directories
        for file_path in root_path.rglob("*"):
            try:
                # -------------------------------------------------------------
                # FILTER: Skip directories
                # We only want to index files, not folder entries
                # -------------------------------------------------------------
                if file_path.is_dir():
                    continue
                
                # -------------------------------------------------------------
                # FILTER: Skip non-video files
                # Check extension against VIDEO_EXTENSIONS set
                # -------------------------------------------------------------
                if not is_video_file(file_path):
                    continue
                
                # -------------------------------------------------------------
                # FILTER: Skip hidden and system files
                # Windows system files often start with '$' (e.g., $RECYCLE.BIN)
                # Unix hidden files start with '.' (e.g., .DS_Store)
                # -------------------------------------------------------------
                if file_path.name.startswith(".") or file_path.name.startswith("$"):
                    continue
                
                video_count += 1
                
                # -------------------------------------------------------------
                # YIELD: Return structured file information
                # Using absolute() ensures consistent path format
                # -------------------------------------------------------------
                yield {
                    "file_name": file_path.name,
                    "directory": str(file_path.parent),
                    "full_path": str(file_path.absolute())
                }
                
            except PermissionError:
                # Handle access denied errors (common for system folders)
                logger.warning(f"Permission denied: {file_path}")
                continue
            except Exception as e:
                # Catch-all for unexpected errors to prevent scan termination
                logger.warning(f"Error processing {file_path}: {e}")
                continue
                
    except PermissionError:
        # Handle permission error at root directory level
        logger.error(f"Permission denied accessing: {root_path}")
    except Exception as e:
        # Catch-all for directory iteration errors
        logger.error(f"Error scanning directory: {e}")
    
    logger.info(f"Scan complete. Found {video_count} video files.")


# =============================================================================
# CONVENIENCE WRAPPER
# =============================================================================

def get_all_videos(root_dir: Path = MOVIE_DIRECTORY) -> List[Dict]:
    """
    Get all video files as a list.
    
    Convenience wrapper around scan_directory() that collects all
    results into a list. Useful when you need random access to results
    or need to know the total count before processing.
    
    Args:
        root_dir (Path): Root directory to scan.
                         Defaults to MOVIE_DIRECTORY from config.
    
    Returns:
        List[Dict]: List of dictionaries, each containing:
            - "file_name" (str): Filename with extension
            - "directory" (str): Path to containing directory
            - "full_path" (str): Absolute path to file
    
    Warning:
        For very large directories (10,000+ files), this will consume
        significant memory. Consider using scan_directory() generator
        directly for such cases.
    
    Examples:
        >>> videos = get_all_videos()
        >>> print(f"Total videos: {len(videos)}")
        Total videos: 1523
        
        >>> # Access specific video
        >>> first_video = videos[0]
        >>> print(first_video["file_name"])
    """
    return list(scan_directory(root_dir))


# =============================================================================
# STANDALONE TEST
# =============================================================================
# This block runs when the module is executed directly (not imported).
# Useful for testing the scanner independently.

if __name__ == "__main__":
    # Test scanner with default settings
    print(f"Scanning: {MOVIE_DIRECTORY}")
    videos = get_all_videos()
    print(f"\nFound {len(videos)} video files")
    
    # Show first 10 results as sample
    for i, video in enumerate(videos[:10]):
        print(f"  {i+1}. {video['file_name']}")
    
    # Indicate if more results exist
    if len(videos) > 10:
        print(f"  ... and {len(videos) - 10} more")
