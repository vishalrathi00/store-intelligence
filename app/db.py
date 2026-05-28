import sqlite3

DB_PATH = "data/store.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT,
            track_id INTEGER,
            store_code TEXT,
            camera_id TEXT,
            event_timestamp TEXT,
            zone_name TEXT,
            is_staff INTEGER DEFAULT 0,
            UNIQUE(event_type, track_id, camera_id, event_timestamp)
        )
    """)
    conn.commit()
    conn.close()