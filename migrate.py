"""
Run this once to apply schema changes without wiping existing data:
    python migrate.py
"""
from db import get_conn

conn = get_conn()
cur = conn.cursor()

def column_exists(table, column):
    cur.execute(
        "SELECT COUNT(*) FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s",
        (table, column),
    )
    return cur.fetchone()[0] > 0

def table_exists(table):
    cur.execute(
        "SELECT COUNT(*) FROM information_schema.TABLES "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s",
        (table,),
    )
    return cur.fetchone()[0] > 0

# users.campus_location
if not column_exists("users", "campus_location"):
    cur.execute("ALTER TABLE users ADD COLUMN campus_location VARCHAR(255) DEFAULT NULL")
    print("Added users.campus_location")
else:
    print("users.campus_location already exists")

# listings.pickup_location
if not column_exists("listings", "pickup_location"):
    cur.execute("ALTER TABLE listings ADD COLUMN pickup_location VARCHAR(255) DEFAULT NULL")
    print("Added listings.pickup_location")
else:
    print("listings.pickup_location already exists")

# watchlist table
if not table_exists("watchlist"):
    cur.execute("""
        CREATE TABLE watchlist (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            listing_id INT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uq_watchlist (user_id, listing_id),
            CONSTRAINT fk_watchlist_user    FOREIGN KEY (user_id)    REFERENCES users(id)    ON DELETE CASCADE,
            CONSTRAINT fk_watchlist_listing FOREIGN KEY (listing_id) REFERENCES listings(id) ON DELETE CASCADE
        )
    """)
    print("Created watchlist table")
else:
    print("watchlist table already exists")

conn.commit()
cur.close()
conn.close()
print("Migration complete.")
