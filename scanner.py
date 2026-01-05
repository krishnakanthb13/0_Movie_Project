"""
Movie Library Project - File Scanner
Recursively scans directories for video files.
"""

import logging
from pathlib import Path
from typing import Generator, List, Dict
from config import MOVIE_DIRECTORY, VIDEO_EXTENSIONS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def is_video_file(file_path: Path) -> bool:
    """Check if a file is a video based on extension."""
    return file_path.suffix.lower() in VIDEO_EXTENSIONS


def scan_directory(root_dir: Path = MOVIE_DIRECTORY) -> Generator[Dict, None, None]:
    """
    Recursively scan a directory for video files.
    
    Yields:
        Dict with file_name, directory, and full_path for each video found.
    """
    root_path = Path(root_dir)
    
    if not root_path.exists():
        logger.error(f"Directory does not exist: {root_path}")
        return
    
    logger.info(f"Scanning directory: {root_path}")
    video_count = 0
    
    try:
        for file_path in root_path.rglob("*"):
            try:
                # Skip directories
                if file_path.is_dir():
                    continue
                
                # Skip non-video files
                if not is_video_file(file_path):
                    continue
                
                # Skip hidden files and system files
                if file_path.name.startswith(".") or file_path.name.startswith("$"):
                    continue
                
                video_count += 1
                
                yield {
                    "file_name": file_path.name,
                    "directory": str(file_path.parent),
                    "full_path": str(file_path.absolute())
                }
                
            except PermissionError:
                logger.warning(f"Permission denied: {file_path}")
                continue
            except Exception as e:
                logger.warning(f"Error processing {file_path}: {e}")
                continue
                
    except PermissionError:
        logger.error(f"Permission denied accessing: {root_path}")
    except Exception as e:
        logger.error(f"Error scanning directory: {e}")
    
    logger.info(f"Scan complete. Found {video_count} video files.")


def get_all_videos(root_dir: Path = MOVIE_DIRECTORY) -> List[Dict]:
    """
    Get all video files as a list.
    
    Returns:
        List of dicts with file_name, directory, and full_path.
    """
    return list(scan_directory(root_dir))


if __name__ == "__main__":
    # Test scanner
    print(f"Scanning: {MOVIE_DIRECTORY}")
    videos = get_all_videos()
    print(f"\nFound {len(videos)} video files")
    
    # Show first 10
    for i, video in enumerate(videos[:10]):
        print(f"  {i+1}. {video['file_name']}")
    
    if len(videos) > 10:
        print(f"  ... and {len(videos) - 10} more")
