
import logging
from storage import get_db_connection, init_sqlite

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def activate_all():
    init_sqlite()
    conn = get_db_connection()
    
    # Set all movies to active=1
    cursor = conn.execute("UPDATE movies SET is_active = 1 WHERE is_active = 0 OR is_active = '0'")
    count = cursor.rowcount
    
    conn.commit()
    conn.close()
    
    logger.info(f"Activated {count} movies for enrichment.")

if __name__ == "__main__":
    activate_all()
