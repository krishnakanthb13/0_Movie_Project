
import os
from pathlib import Path
from config import CSV_FILE, SQLITE_FILE

def reset_data():
    print("Resetting Movie Library Data...")
    print("=" * 30)

    files_to_remove = [CSV_FILE, SQLITE_FILE]
    
    for file_path in files_to_remove:
        if file_path.exists():
            try:
                os.remove(file_path)
                print(f"Deleted: {file_path}")
            except Exception as e:
                print(f"Error deleting {file_path}: {e}")
        else:
            print(f"Not found (already clean): {file_path}")
            
    print("\nData reset complete.")
    print("Next steps:")
    print("1. Run 'python main.py --scan' to re-index movies.")
    print("2. Run 'python main.py --enrich --bulk' to run AI enrichment.")
    print("3. Run 'python main.py --fetch-omdb' to run OMDb enrichment.")

if __name__ == "__main__":
    confirm = input("Are you sure you want to delete all movie data? (y/n): ")
    if confirm.lower() == 'y':
        reset_data()
    else:
        print("Operation cancelled.")
